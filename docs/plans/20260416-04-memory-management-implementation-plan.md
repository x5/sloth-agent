# 20260416-04-memory-management-implementation-plan.md

> Spec 来源: `docs/specs/20260416-04-memory-management-spec.md`
> Plan 文件: `docs/plans/20260416-04-memory-management-implementation-plan.md`
> 对应 Arch: `docs/specs/00000000-00-architecture-overview.md` §7.2

---

## 1. 目标

实现三层 memory 结构（sessions/scenarios/shared）的文件系统存储、RunState 持久化、三层上下文边界隔离。v1.0 用纯文件系统，不依赖 SQLite/ChromaDB。

---

## 2. 步骤（按顺序执行）

### 步骤 1: 实现 MemoryStore 文件系统存储

**文件**: `src/sloth_agent/memory/store.py`（重写）

**内容** (spec §2.1, §3.1):

```python
class MemoryStore:
    """文件系统存储层，管理 sessions/ 和 scenarios/ 目录结构。"""

    def __init__(self, memory_root: Path):
        self.memory_root = memory_root
        self.sessions_dir = memory_root / "sessions"
        self.scenarios_dir = memory_root / "scenarios"
        self.shared_dir = memory_root / "shared"

    def save_session_message(self, session_id: str, role: str, content: str) -> None:
        """追加消息到 sessions/{session_id}/chat.jsonl"""

    def load_session_messages(self, session_id: str, limit: int | None = None) -> list[dict]:
        """读取 chat.jsonl，可选 limit 取最后 n 条"""

    def save_session_context(self, session_id: str, context: dict) -> None:
        """保存上下文摘要到 context.json"""

    def load_session_context(self, session_id: str) -> dict | None:
        """加载上下文摘要"""

    def save_phase_input(self, scenario_id: str, phase_id: str, data: dict) -> None:
        """保存 phase 输入到 scenarios/{scenario}/{phase}/input.json"""

    def save_phase_output(self, scenario_id: str, phase_id: str, data: dict) -> None:
        """保存 phase 输出到 scenarios/{scenario}/{phase}/output.json"""

    def load_phase_input(self, scenario_id: str, phase_id: str) -> dict | None:
        """加载 phase 输入"""

    def load_phase_output(self, scenario_id: str, phase_id: str) -> dict | None:
        """加载 phase 输出"""

    def save_phase_message(self, scenario_id: str, phase_id: str, role: str, content: str) -> None:
        """追加 phase 对话到 scenarios/{scenario}/{phase}/chat.jsonl"""

    def save_artifact(self, scenario_id: str, phase_id: str, filename: str, content: bytes) -> None:
        """保存 phase 产物到 scenarios/{scenario}/{phase}/artifacts/{filename}"""

    def save_knowledge(self, key: str, content: dict) -> None:
        """保存共享知识到 shared/knowledge/{key}.json"""

    def load_knowledge(self, key: str) -> dict | None:
        """加载共享知识"""
```

**验收**: 在临时目录中创建 MemoryStore，调用各方法后验证文件存在且内容正确。

---

### 步骤 2: 实现 RunState 持久化（spec §9.1）

**文件**: `src/sloth_agent/core/runner.py`（修改）

**内容**:

```python
class Runner:
    def persist(self, run_id: str) -> None:
        """将当前运行状态写入 memory/sessions/{run_id}/"""
        # 写 state.json
        # 追加 tool_history.jsonl（如有新 tool_call）
        # 追加 handoffs.jsonl（如有新 phase_handoff）

    @classmethod
    def resume_run_state(cls, run_id: str) -> "Runner | None":
        """从 memory/sessions/{run_id}/state.json 恢复状态"""
```

持久化路径：`memory/sessions/{run_id}/`
- `state.json` — RunState 快照
- `tool_history.jsonl` — 工具调用记录
- `turns.jsonl` — 每轮对话记录
- `handoffs.jsonl` — phase handoff 记录

**验收**: `persist()` 在 mock 测试中能正确写入文件系统，且 `resume_run_state()` 能正确读取。

---

### 步骤 3: 实现三层上下文边界（spec §9.2）

**文件**: `src/sloth_agent/core/runner.py`（修改）

**内容**:

```python
@dataclass
class ModelVisibleContext:
    history: list            # 对话历史
    retrieved_memory: list   # 从文件系统加载的记忆
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

**验收**: Runner 构建 LLM 请求时，只从 `ModelVisibleContext` 取数据。

---

### 步骤 4: 编写单元测试

| 文件 | 覆盖 | 测试数 |
|------|------|--------|
| `tests/memory/test_store.py` | MemoryStore 文件系统存储、加载一致性 | 5 |
| `tests/core/test_persistence.py` | RunState 持久化、恢复 | 2 |
| `tests/core/test_context_boundary.py` | 三层上下文边界正确性 | 2 |

**具体测试**：

```
test_store.py:
  - test_save_load_session_message: 消息保存/加载一致
  - test_save_load_phase_output: Phase 输出保存/加载一致
  - test_session_metadata: metadata.json 正确写入
  - test_save_artifact: 产物文件正确写入
  - test_save_load_knowledge: 共享知识保存/加载一致

test_persistence.py:
  - test_persist_and_resume: persist() 写 state.json，resume_run_state() 正确恢复
  - test_persist_tool_history: tool_call 后追加 tool_history.jsonl

test_context_boundary.py:
  - test_model_visible_only_in_prompt: LLM 请求中只包含 ModelVisibleContext 的数据
  - test_runtime_context_not_sent: RuntimeOnlyContext 的数据不会出现在 prompt 中
```

---

## 3. 文件清单

| 文件 | 动作 |
|------|------|
| `src/sloth_agent/memory/store.py` | **重写** — 文件系统存储层 |
| `src/sloth_agent/core/runner.py` | **修改** — persist()、resume_run_state()、三层上下文 |
| `tests/memory/test_store.py` | **新建** |
| `tests/core/test_persistence.py` | **新建** |
| `tests/core/test_context_boundary.py` | **新建** |

---

## 4. 与现有代码的关系

| 现有文件 | 动作 | 原因 |
|----------|------|------|
| `memory/store.py` | **重写** | 现有是 SQLite + ChromaDB 脚手架，v1.0 改用纯文件系统 |
| `memory/retrieval.py` | **保留不动** | v1.1+ 使用 |
| `reliability/checkpoint.py` | **保留不动** | 由 session lifecycle spec 对应的 plan 处理 |

---

## 5. 验收标准

- [ ] MemoryStore 支持 save/load session message、phase input/output、artifact、knowledge
- [ ] `Runner.persist()` 每次 turn 后写 state.json，每次 tool_call 后追加 tool_history.jsonl
- [ ] `resume_run_state()` 能从 state.json 正确恢复 Runner 状态
- [ ] Runner 构建 LLM 请求时只传递 ModelVisibleContext 的内容
- [ ] RuntimeOnlyContext 的数据不会出现在 prompt 中
- [ ] 所有测试通过（共 9 tests）

---

*Plan 版本: v1.0.0 | 创建: 2026-04-17*
