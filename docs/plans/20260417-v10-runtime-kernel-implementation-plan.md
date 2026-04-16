# v1.0 Task 1: Runtime Kernel & RunState — Implementation Plan

> Spec 来源: `docs/specs/00000000-00-architecture-overview.md` §3.1.1, §5.1.1.1, §5.1.1.2
> Plan 文件: `docs/plans/20260417-v10-runtime-kernel-implementation-plan.md`
> 对应 TODO: `Task 1: Runtime Kernel & RunState`
> 依赖: 无（v1.0 起点）

---

## 1. 目标

建立 v1.0 唯一运行时内核：`Runner` + `RunState` + `NextStep`，替代现有的 `AgentEvolve` 昼夜循环。

---

## 2. 步骤（按顺序执行）

### 步骤 1.1: 定义 `NextStep` 协议

**文件**: `src/sloth_agent/core/runner.py`

**内容** (spec §5.1.1.2):

```python
class NextStepType(str, Enum):
    final_output = "final_output"
    tool_call = "tool_call"
    phase_handoff = "phase_handoff"
    retry_same = "retry_same"
    retry_different = "retry_different"
    replan = "replan"
    interruption = "interruption"
    abort = "abort"

class NextStep(BaseModel):
    type: NextStepType
    output: str | None = None
    request: ToolRequest | None = None
    next_agent: str | None = None
    next_phase: str | None = None
    reason: str | None = None
```

其中 `ToolRequest` 定义:

```python
class ToolRequest(BaseModel):
    tool_name: str
    params: dict[str, Any]
```

**验收**: `NextStep` 类型可被 pydantic 序列化/反序列化，8 种 type 值均有效。

---

### 步骤 1.2: 定义 `RunState` 数据模型

**文件**: `src/sloth_agent/core/runner.py`

**内容** (spec §3.1.1):

```python
class RunState(BaseModel):
    """唯一运行时状态，所有真相源"""
    run_id: str
    session_id: str | None = None
    current_agent: str | None = None      # "builder" / "reviewer" / "deployer"
    current_phase: str | None = None      # "plan_parsing" / "coding" / ...
    phase: Literal["initializing", "running", "paused", "completed", "aborted"]
    turn: int = 0
    tool_history: list[dict] = []
    pending_interruptions: list[dict] = []
    handoff_payload: dict | None = None
    model: str = "deepseek-v3.2"
    output: str | None = None
    errors: list[str] = []
    started_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @property
    def is_finished(self) -> bool:
        return self.phase in ("completed", "aborted")
```

**验收**: `RunState` 可序列化/反序列化、可持久化到 JSON、`is_finished` 属性正确。

---

### 步骤 1.3: 定义 `Runner` 内核

**文件**: `src/sloth_agent/core/runner.py`

**内容** (spec §3.1.1):

```python
class Runner:
    """唯一执行循环内核"""

    def __init__(self, config: Config, tool_registry: ToolRegistry, llm_provider: ...):
        self.config = config
        self.tool_registry = tool_registry
        self.llm_provider = llm_provider
        self.hooks: dict[str, list[Callable]] = {}

    def run(self, state: RunState) -> RunState:
        while not state.is_finished:
            state.turn += 1
            next_step = self.think(state)
            state = self.resolve(state, next_step)
            self.persist(state)
            self.observe("turn.end", {"turn": state.turn, "step": next_step.type})
        return state

    def think(self, state: RunState) -> NextStep:
        """调 LLM 得到 next step"""
        ...

    def resolve(self, state: RunState, next_step: NextStep) -> RunState:
        """分发: final/tool/handoff/retry/interrupt/abort"""
        ...

    def persist(self, state: RunState) -> None:
        """写回 RunState 到文件系统"""
        ...

    def observe(self, event: str, data: dict) -> None:
        """触发 hook"""
        ...
```

**验收**: `Runner.run()` 循环可被 mock 测试，`resolve()` 对每种 NextStep type 有明确分支，`persist()` 写 JSON 到 `memory/sessions/{run_id}/state.json`。

---

### 步骤 1.4: 定义 `Product Orchestrator` 边界

**文件**: `src/sloth_agent/core/orchestrator.py`

**内容** (spec §3.1.1 边界规则):

```python
class ProductOrchestrator:
    """产品层入口，不负责执行循环"""

    def __init__(self, config: Config):
        self.config = config
        self.tool_registry = ToolRegistry(config)
        self.llm_provider = ...  # Task 8 对接

    def create_run_state(self, run_id: str, session_id: str | None = None) -> RunState:
        return RunState(run_id=run_id, session_id=session_id, phase="initializing")

    def resume_run_state(self, run_id: str) -> RunState | None:
        path = Path(...) / f"memory/sessions/{run_id}/state.json"
        if path.exists():
            return RunState.model_validate_json(path.read_text())
        return None
```

**验收**: `create_run_state()` 返回有效 `RunState`，`resume_run_state()` 能从文件系统恢复。

---

### 步骤 1.5: 实现 `Runner.resolve()` 分支逻辑

**文件**: `src/sloth_agent/core/runner.py`（续）

**内容**:

`resolve()` 必须处理 `NextStep` 的全部 8 种 type:

| type | 动作 | 更新 RunState 字段 |
|------|------|-------------------|
| `final_output` | phase="completed", output=next_step.output | phase, output |
| `tool_call` | 调用 tool_registry，记录结果到 tool_history | tool_history, turn |
| `phase_handoff` | 更新 current_agent/current_phase | current_agent, current_phase, handoff_payload |
| `retry_same` | 继续循环，不重置 | (无特殊变更) |
| `retry_different` | 继续循环，记录 reason | errors |
| `replan` | 触发重规划（v1.1 实现），当前标记 abort | phase="aborted" |
| `interruption` | phase="paused", 记录 pending_interruptions | phase, pending_interruptions |
| `abort` | phase="aborted", 记录 error | phase, errors |

**验收**: 为 `resolve()` 写 8 个单元测试，每种 type 一个 case。

---

### 步骤 1.6: 实现轻量 Hook Manager

**文件**: `src/sloth_agent/core/runner.py`（或独立 `hooks.py`）

**内容** (spec §7.4):

```python
class HookManager:
    hooks: dict[str, list[Callable]]

    def on(self, event: str, handler: Callable): ...
    def emit(self, event: str, data: Any): ...
```

v1.x hook 点: `run.start`, `run.end`, `phase.start`, `phase.end`, `model.start`, `model.end`, `tool.start`, `tool.end`, `handoff`, `gate.pass`, `gate.fail`, `reflection`, `resume`, `budget.warn`, `budget.over`

**验收**: `emit()` 能按注册顺序调用所有 handler。

---

### 步骤 1.7: 编写单元测试

**文件**: `tests/core/test_runner.py`

**覆盖**:

1. `NextStep` 序列化/反序列化 — 8 种 type
2. `RunState.is_finished` — completed/aborted=True, 其余=False
3. `RunState` 持久化 — save → load 后数据一致
4. `Runner.resolve()` — 8 种 type 各一个 case
5. `HookManager.on/emit` — 注册后正确触发
6. `ProductOrchestrator.create_run_state` / `resume_run_state`

---

## 3. 与现有代码的关系

| 现有文件 | 动作 | 原因 |
|----------|------|------|
| `core/state.py` | 保留 | 包含 TaskState/ExecutionStep/PlanContext 等，与 RunState 不冲突 |
| `core/config.py` | 保留 | Runner 依赖 Config |
| `core/tools/tool_registry.py` | 保留 | Runner.resolve() 调用它 |
| `core/agent.py` (AgentEvolve) | **标记废弃** | v1.0 不再使用昼夜循环，入口改为 `sloth run` → Orchestrator → Runner |
| `cli/app.py` (run 命令) | **修改** | 从调用 `AgentEvolve.run()` 改为 `ProductOrchestrator.create_run_state()` → `Runner.run()` |

---

## 4. 文件清单

| 文件 | 动作 |
|------|------|
| `src/sloth_agent/core/runner.py` | **新建** — NextStep, RunState, Runner, HookManager |
| `src/sloth_agent/core/orchestrator.py` | **修改** — 加入 ProductOrchestrator |
| `src/sloth_agent/core/__init__.py` | **修改** — 导出 Runner/RunState/NextStep |
| `src/sloth_agent/cli/app.py` | **修改** — run 命令改为调用 Orchestrator → Runner |
| `tests/core/test_runner.py` | **新建** — 单元测试 |

---

## 5. 验收标准

- [ ] `Runner` 类可实例化，包含 `prepare/think/resolve/persist/observe` 方法
- [ ] `NextStep` 支持全部 8 种 type 值
- [ ] `RunState` 可 JSON 序列化/反序列化，`is_finished` 正确
- [ ] `Runner.resolve()` 对 8 种 type 有正确分支，每种行为符合 spec
- [ ] `HookManager` 支持 on/emit，v1.x hook 点全部注册
- [ ] `ProductOrchestrator` 能创建和恢复 `RunState`
- [ ] `tests/core/test_runner.py` 全部通过
- [ ] `sloth run` CLI 命令不再调用 `AgentEvolve`，改为调用 Runner

---

*Plan 版本: v1.0.0 | 创建: 2026-04-17*
