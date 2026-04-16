# v1.0 Task 3: Builder Agent Runtime — Implementation Plan

> Spec 来源: `docs/specs/00000000-00-architecture-overview.md` §5.1, §5.1.2, §5.1.3, §6.0, §6.1.1.1-6.1.3
> Plan 文件: `docs/plans/20260417-v10-builder-agent-implementation-plan.md`
> 对应 TODO: `Task 3: Builder Agent Runtime`
> 依赖: Task 1 (Runner/RunState) + Task 2 (Tool Runtime)

---

## 1. 目标

实现 Builder Agent 的完整运行时：Plan 解析 → 编码 → 调试 → 单元测试 → Reflection → Stuck Detection → 产出 `BuilderOutput` 结构化交接物。

---

## 2. 步骤（按顺序执行）

### 步骤 3.1: 定义 `BuilderOutput` 交接协议

**文件**: `src/sloth_agent/models/handoff.py`（新建）

**内容** (spec §5.1.1):

```python
class TestReport(BaseModel):
    total: int
    passed: int
    failed: int
    errors: list[str] = []
    coverage: float = 0.0

class BuilderOutput(BaseModel):
    branch: str
    changed_files: list[str]
    diff_summary: str
    test_results: TestReport
    coverage: float
    build_log: str | None = None

class ReviewerOutput(BaseModel):
    approved: bool
    branch: str
    blocking_issues: list[str]
    suggestions: list[str]
```

**验收**: 两个模型可序列化/反序列化，与 Task 4 Gate 的输入格式对齐。

---

### 步骤 3.2: 实现 `ContextWindowManager`

**文件**: `src/sloth_agent/core/context_window.py`（新建）

**内容** (spec §5.1.2, §5.1.3):

```python
class ContextWindowManager:
    def __init__(self, max_tokens: int = 128_000, output_reserve: int = 15_000):
        self.max_tokens = max_tokens
        self.output_reserve = output_reserve
        self.available = max_tokens - output_reserve  # 113K

    def build_messages(self, system: str, history: list, tools: list, user_msg: str) -> list:
        # 1. System prompt（固定）
        # 2. 用户消息（固定）
        # 3. 工具结果（最新完整保留，旧压缩）
        # 4. 历史对话（从新到旧填满）
        ...

    def _compress_tool_result(self, result) -> str:
        # match/case 纯规则压缩，不用 LLM
        match result.tool_name:
            case "read_file": return f"[已读取 {result.path} ({result.line_count}行)]"
            case "run_command":
                if result.exit_code == 0: return f"[命令成功: {result.command}]"
                return f"[命令失败(exit={result.exit_code}): {result.stderr[:200]}]"
            case "grep" | "glob": return f"[搜索 {result.pattern}: {result.match_count} 个结果]"
            case _: return f"[{result.tool_name}: {result.summary[:100]}]"
```

Token 分区:
- System Prompt: ~8K（角色 + Plan 全文 + 活跃技能）
- 历史对话: ~40K（最近 3 轮完整，更早压缩）
- 工具结果: ~20K（最新完整，旧压缩）
- 用户消息: ~5K
- 预留输出: ~15K

**验收**: 输入超过 max_tokens 的上下文，build_messages() 正确截断/压缩后输出，总 token 数不超过 available。使用 tiktoken 精确计数。

---

### 步骤 3.3: 实现 `Plan` 模型和解析

**文件**: `src/sloth_agent/models/plan.py`（新建）

**内容** (spec §6.0 v1.0 阶段定义):

```python
class PlanTask(BaseModel):
    id: str
    description: str
    dependencies: list[str] = []
    status: str = "pending"  # pending | running | done | failed

class Plan(BaseModel):
    id: str
    title: str
    tasks: list[PlanTask]
    constraints: list[str] = []
    context: str | None = None

class PlanParser:
    """用 reasoner 模型解析 Plan 文件为结构化任务列表"""
    def parse(self, plan_text: str, llm_provider) -> Plan:
        ...
```

**验收**: `PlanParser.parse()` 能将 markdown plan 文件解析为 `Plan` 对象，任务依赖关系正确。

---

### 步骤 3.4: 实现 `StuckDetector`

**文件**: `src/sloth_agent/core/stuck_detector.py`（新建）

**内容** (spec §5.1.2 Stuck Detection):

```python
class StuckDetector:
    window: list[Reflection]

    def is_stuck(self) -> bool:
        # 规则 1: 连续 3 次相同 error_category + 相似 root_cause
        # 规则 2: 连续 3 次 action=retry_same 但问题未解决
        # 规则 3: confidence 持续下降
        ...

    def get_unstuck_action(self) -> str:
        # 第 1 次 stuck → retry_different
        # 第 2 次 stuck → replan
        # 第 3 次 stuck → abort
        ...

    def record(self, reflection: Reflection):
        self.window.append(reflection)

    def reset(self):
        self.window.clear()
```

**验收**: 3 个 stuck 规则各有独立测试用例，unstuck action 返回值正确。

---

### 步骤 3.5: 实现 `Reflection` 模型和 prompt

**文件**: `src/sloth_agent/core/reflection.py`（新建，不同于现有的 reflector.py）

**内容** (spec §5.1.2 Reflection):

```python
class Reflection(BaseModel):
    error_category: Literal["syntax", "logic", "dependency", "design", "plan", "environment"]
    root_cause: str
    learnings: list[str]
    action: Literal["retry_same", "retry_different", "replan", "abort"]
    retry_hint: str | None
    confidence: float

async def build_reflection_prompt(task, git_diff, gate_errors, file_contents, previous_reflections) -> str:
    """结构化 prompt，喂完整的环境观察"""
    ...
```

注意：这是 task-level reflection（门控失败时即时反思），与现有 `reflector.py` 的 report-level reflection（执行结束后复盘）是两个不同组件。

**验收**: `Reflection` 模型可序列化，prompt 模板包含 task 描述、git diff、gate 错误、文件上下文、历史反思。

---

### 步骤 3.6: 实现 `BuilderAgent` 核心类

**文件**: `src/sloth_agent/agents/builder.py`（新建）

**内容** (spec §6.0 Adaptive Execution):

```python
class BuilderAgent:
    def __init__(self, config: Config, tool_orchestrator: ToolOrchestrator, llm_provider, context_mgr: ContextWindowManager):
        self.config = config
        self.tool_orchestrator = tool_orchestrator
        self.llm = llm_provider          # deepseek-v3.2 (coding)
        self.reasoner = reasoner_llm     # deepseek-r1-0528 (debugging/reflection)
        self.context_mgr = context_mgr
        self.stuck_detector = StuckDetector()

    async def build(self, plan: Plan) -> BuilderOutput:
        tasks = self.parse_plan(plan)
        for task in tasks:
            while not task.done:
                result = await self.execute(task)
                gate = self.check_gate(result)

                if gate.passed:
                    task.done = True
                    self.stuck_detector.reset()
                    continue

                # Reflect
                reflection = await self.reflect(result, gate)
                self.stuck_detector.record(reflection)

                if self.stuck_detector.is_stuck():
                    action = self.stuck_detector.get_unstuck_action()
                    if action == "abort":
                        raise BuildFailure(task, "stuck")
                    elif action == "replan":
                        tasks = await self.replan(plan, task, gate.errors)
                        continue

                task.retries += 1
                if task.retries >= MAX_RETRIES:
                    raise BuildFailure(task, f"exceeded {MAX_RETRIES} retries")

        return self.collect_output()
```

Builder 内部阶段：

| 内部阶段 | 模型 | 输入 | 输出 |
|---------|------|------|------|
| Plan 解析 | deepseek-r1-0528 | Plan 文件 | 任务列表 |
| 编码实现 | deepseek-v3.2 | 任务 | 代码 + 测试 |
| 调试修复 | deepseek-r1-0528 | 失败测试 | 修复代码 |

**验收**: `BuilderAgent.build()` 可跑通单任务场景（mock LLM），gate 失败时触发 reflection，连续失败触发 stuck detection。

---

### 步骤 3.7: 集成 Builder 到 `Runner`

**文件**: `src/sloth_agent/core/runner.py`（修改）

Builder 作为 Runner 的一个 phase owner 运行：
- `Runner.prepare()` 设置 `current_agent="builder"`, `current_phase="plan_parsing"`
- `Runner.think()` 调 LLM 得到 Builder 的下一步动作
- `Runner.resolve()` 处理 builder 的 `tool_call` / `phase_handoff` / `retry_same` 等

**验收**: Runner 能以 builder 身份跑完一个完整 turn cycle（mock LLM + mock tools）。

---

### 步骤 3.8: 编写单元测试

**文件**: `tests/`（新建）

| 文件 | 覆盖 |
|------|------|
| `tests/models/test_handoff.py` | BuilderOutput/ReviewerOutput 序列化 |
| `tests/core/test_context_window.py` | token 预算管理、压缩逻辑 |
| `tests/core/test_stuck_detector.py` | 3 个 stuck 规则 + unstuck action |
| `tests/core/test_reflection.py` | Reflection 模型 + prompt 模板 |
| `tests/agents/test_builder.py` | BuilderAgent 执行循环（mock） |

---

## 3. 与现有代码的关系

| 现有文件 | 动作 | 原因 |
|----------|------|------|
| `core/reflector.py` | **保留** | report-level reflection，与 task-level reflection 共存 |
| `core/planner.py` | **保留或重构** | 现有 Plan 逻辑可能部分复用 |
| `core/executor.py` | **保留或重构** | 现有执行逻辑可能部分复用 |
| `models/handoff.py` | **新建** | BuilderOutput/ReviewerOutput |
| `models/plan.py` | **新建** | Plan 模型 |

---

## 4. 文件清单

| 文件 | 动作 |
|------|------|
| `src/sloth_agent/models/__init__.py` | **新建** |
| `src/sloth_agent/models/handoff.py` | **新建** |
| `src/sloth_agent/models/plan.py` | **新建** |
| `src/sloth_agent/core/context_window.py` | **新建** |
| `src/sloth_agent/core/stuck_detector.py` | **新建** |
| `src/sloth_agent/core/reflection.py` | **新建** |
| `src/sloth_agent/agents/__init__.py` | **新建** |
| `src/sloth_agent/agents/builder.py` | **新建** |
| `src/sloth_agent/core/runner.py` | **修改** — 集成 Builder phase |
| `tests/models/test_handoff.py` | **新建** |
| `tests/core/test_context_window.py` | **新建** |
| `tests/core/test_stuck_detector.py` | **新建** |
| `tests/core/test_reflection.py` | **新建** |
| `tests/agents/test_builder.py` | **新建** |

---

## 5. 验收标准

- [ ] `BuilderOutput` / `ReviewerOutput` 数据结构定义完整
- [ ] `ContextWindowManager` 正确管理 token 预算，压缩规则纯规则实现
- [ ] `StuckDetector` 3 条规则正确检测死循环
- [ ] `Reflection` 模型可结构化输出，prompt 包含完整环境观察
- [ ] `BuilderAgent.build()` 可跑通单任务场景
- [ ] Runner 能以 builder 身份跑完整 turn cycle
- [ ] 所有测试通过

---

*Plan 版本: v1.0.0 | 创建: 2026-04-17*
