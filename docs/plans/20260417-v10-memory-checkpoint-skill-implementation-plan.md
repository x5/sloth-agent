# v1.0 Task 7: FS Memory / Checkpoint / Skill Loading — Implementation Plan

> Spec 来源: `docs/specs/00000000-00-architecture-overview.md` §7.2, §7.3, §8.3; `docs/specs/20260416-04-memory-management-spec.md`; `docs/specs/20260416-06-skill-management-spec.md`; `docs/specs/20260416-13-session-lifecycle-spec.md`
> Plan 文件: `docs/plans/20260417-v10-memory-checkpoint-skill-implementation-plan.md`
> 对应 TODO: `Task 7: FS Memory / Checkpoint / Skill Loading`
> 依赖: Task 6 (Deployer Agent)

---

## 1. 目标

将运行状态、阶段产物、工具记录、gate 结果统一写入文件系统；建立 checkpoint 保存/恢复机制；打通 SKILL.md 加载与按需注入机制。

---

## 2. 步骤（按顺序执行）

### 步骤 7.1: 统一 RunState 持久化

**文件**: `src/sloth_agent/core/runner.py`（修改）

**内容** (spec §7.2 Memory):

```
持久化路径: memory/sessions/{run_id}/
├── state.json            # RunState 快照
├── tool_history.jsonl    # 工具调用记录（每行一条 ToolExecutionRecord）
├── turns.jsonl           # 每轮对话记录
└── handoffs.jsonl        # phase handoff 记录
```

`Runner.persist()` 必须：
1. 每次 turn 后写 `state.json`
2. 每次 tool_call 后追加 `tool_history.jsonl`
3. 每次 phase_handoff 后追加 `handoffs.jsonl`

**验收**: `persist()` 在 mock 测试中能正确写入文件系统，且文件可被 `resume_run_state()` 正确读取。

---

### 步骤 7.2: 统一阶段产物落盘

**文件**: `src/sloth_agent/core/orchestrator.py`（修改）

**内容** (spec §7.2 目录结构):

```
memory/scenarios/{scenario_id}/{phase_id}/
├── input.json            # Phase 输入
├── output.json           # Phase 输出（BuilderOutput / ReviewerOutput）
├── chat.jsonl            # Phase 对话
└── artifacts/            # 产物文件
```

每个 Agent 完成阶段后，必须将结构化输出写入对应目录。

**验收**: Builder 完成后 `output.json` 包含 `BuilderOutput` 数据，Reviewer 完成后包含 `ReviewerOutput` 数据。

---

### 步骤 7.3: 增强 CheckpointManager

**文件**: `src/sloth_agent/reliability/checkpoint.py`（修改）

**内容** (spec §8.3 Checkpoint Strategy):

v1.0 三级 checkpoint：
- **Level 1 (任务级)**: Builder 每完成一个 task → `git commit`（自动）
- **Level 2 (阶段级)**: 每个 Agent 开始前 → `git tag sloth/stage/{stage}/start`
- **Level 3 (Session 级)**: Session 开始时 → `git tag sloth/session/{session_id}/start`

现有 CheckpointManager 只有基础的 save/load JSON 文件功能，需要增加：

```python
class CheckpointManager:
    def create_git_checkpoint(self, level: str, label: str) -> str:
        """创建 git tag checkpoint"""
        tag = f"sloth/{level}/{label}/{timestamp()}"
        run(f"git tag {tag}")
        return tag

    def rollback_to(self, tag: str) -> RollbackResult:
        """回滚到指定 checkpoint"""
        safety_tag = self.create_git_checkpoint("safety", "pre-rollback")
        run(f"git reset --hard {tag}")
        run("git clean -fd")
        return RollbackResult(rolled_back_to=tag, safety_backup=safety_tag)

    def auto_commit(self, task, result):
        """任务完成后自动提交"""
        run("git add -A")
        run(f'git commit -m "sloth: {task.description[:50]} [auto]" --allow-empty')
```

**验收**: git checkpoint 创建/回滚/自动提交可正常工作（在测试仓库中）。

---

### 步骤 7.4: 实现 SKILL.md 加载机制

**文件**: `src/sloth_agent/memory/skills.py`（重写）

**内容** (spec §2.2, §3.1):

v1.0 只需：
1. 从 `skills/` 目录扫描 `SKILL.md` 文件
2. 解析 YAML frontmatter 获取元数据
3. 提供 `get_skill_content(skill_id)` → 返回 SKILL.md 完整内容
4. 提供 `load_all_skills()` → 返回所有技能列表

不需要的 v1.1+ 功能：skill_router, 自动匹配, FTS 搜索, 向量检索

```python
class SkillManager:
    def __init__(self, config: Config, skills_dir: Path):
        self.skills_dir = skills_dir

    def load_all_skills(self) -> list[Skill]:
        skills = []
        for skill_file in self.skills_dir.rglob("SKILL.md"):
            skills.append(Skill.from_markdown(skill_file.read_text()))
        return skills

    def get_skill_content(self, skill_id: str) -> str | None:
        for skill in self.load_all_skills():
            if skill.name == skill_id:
                return skill.content
        return None
```

**验收**: 能正确加载 `skills/superpowers/` 和 `skills/gstack/` 下的所有 SKILL.md 文件。

---

### 步骤 7.5: 实现 SKILL.md 按需注入

**文件**: `src/sloth_agent/core/context_window.py`（修改）

在 `ContextWindowManager.build_messages()` 中注入活跃技能：

```python
def inject_skill(self, skill_ids: list[str]) -> str:
    skill_content = ""
    for sid in skill_ids:
        content = self.skill_manager.get_skill_content(sid)
        if content:
            skill_content += f"\n## Skill: {sid}\n{content}\n"
    return skill_content
```

Builder phase 的 system prompt 应包含当前任务相关的 SKILL.md 内容。

**验收**: 指定 skill_id 列表后，能正确拼接为可注入 system prompt 的字符串。

---

### 步骤 7.6: 约束模型可见上下文、运行时上下文、持久化状态三层边界

**文件**: `src/sloth_agent/core/runner.py`（修改）

**内容** (spec §5.1.3 Context Boundary):

```python
@dataclass
class ModelVisibleContext:
    history: list  # 对话历史
    retrieved_memory: list  # 从文件系统加载的记忆
    current_task: str | None
    handoff_payload: dict | None

@dataclass
class RuntimeOnlyContext:
    config: Config
    tool_registry: ToolRegistry
    skill_registry: SkillRegistry
    logger: Logger
    workspace_handle: str
```

规则：
- 只有 `ModelVisibleContext` 能进入 prompt
- `RuntimeOnlyContext` 只供代码与工具层使用，不直接发给模型
- `PersistedRunState` 用于恢复、审计、回放，不等价于对话历史

**验收**: Runner 构建 LLM 请求时，只传递 `ModelVisibleContext` 的内容。

---

### 步骤 7.7: 编写单元测试

**文件**: `tests/`（新建/修改）

| 文件 | 覆盖 |
|------|------|
| `tests/core/test_persistence.py` | RunState 持久化、恢复 |
| `tests/reliability/test_checkpoint.py` | git checkpoint 创建/回滚/自动提交 |
| `tests/memory/test_skills.py` | SKILL.md 加载、解析、内容获取 |
| `tests/core/test_context_boundary.py` | 三层上下文边界正确性 |

---

## 3. 与现有代码的关系

| 现有文件 | 动作 | 原因 |
|----------|------|------|
| `memory/store.py` | **保留不动** — SQLite + ChromaDB，v1.1+ 使用 | v1.0 用纯文件系统 |
| `memory/skills.py` | **重写** — 改为 SKILL.md 加载 | 现有格式与 Claude Code SKILL.md 不统一 |
| `reliability/checkpoint.py` | **修改** — 增加 git checkpoint | 现有只有 JSON 文件保存/恢复 |

---

## 4. 文件清单

| 文件 | 动作 |
|------|------|
| `src/sloth_agent/core/runner.py` | **修改** — 持久化、三层上下文边界 |
| `src/sloth_agent/core/orchestrator.py` | **修改** — 阶段产物落盘 |
| `src/sloth_agent/core/context_window.py` | **修改** — skill 注入 |
| `src/sloth_agent/reliability/checkpoint.py` | **修改** — git checkpoint |
| `src/sloth_agent/memory/skills.py` | **重写** — SKILL.md 加载 |
| `tests/core/test_persistence.py` | **新建** |
| `tests/reliability/test_checkpoint.py` | **新建** |
| `tests/memory/test_skills.py` | **新建** |
| `tests/core/test_context_boundary.py` | **新建** |

---

## 5. 验收标准

- [ ] `Runner.persist()` 每次 turn 后写 `state.json`，每次 tool_call 后追加 `tool_history.jsonl`
- [ ] 阶段产物写入 `memory/scenarios/{scenario}/{phase}/output.json`
- [ ] CheckpointManager 支持 git tag checkpoint 创建和回滚
- [ ] `SkillManager.load_all_skills()` 能扫描加载所有 SKILL.md
- [ ] `SkillManager.get_skill_content()` 能获取指定技能的完整内容
- [ ] `ContextWindowManager.inject_skill()` 能拼接为可注入 prompt 的字符串
- [ ] Runner 构建 LLM 请求时只传递 `ModelVisibleContext`
- [ ] 所有测试通过

---

*Plan 版本: v1.0.0 | 创建: 2026-04-17*
