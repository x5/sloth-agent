# v1.0 Task 2: Tool Runtime 基础能力 — Implementation Plan

> **权威基准**: 工具定义以 `docs/specs/20260416-02-tools-invocation-spec.md` 为准
> Spec 来源: `docs/specs/20260416-02-tools-invocation-spec.md` + `docs/specs/00000000-00-architecture-overview.md` §7.1, §7.1.3
> Plan 文件: `docs/plans/20260417-v10-tool-runtime-implementation-plan.md`
> 对应 TODO: `Task 2: Tool Runtime 基础能力`
> 依赖: Task 1 (Runtime Kernel & RunState)

> **注意**: ToolCategory 枚举映射到权威 spec 的 group 系统。
> 权威 spec 的 `permission` 字段（auto/plan_approval/explicit_approval）与 RiskGate 共同构成双重门控。

---

## 1. 目标

将现有 `ToolRegistry` 升级为 v1.0 规格的工具运行时：`ToolOrchestrator` + `IntentResolver` + `RiskGate` + `Executor` + `ResultFormatter` + `HallucinationGuard`，并落地 v1.0 核心工具（read/write/edit/run_command/glob/grep）。

---

## 2. 步骤（按顺序执行）

### 步骤 2.1: 定义工具数据模型

**文件**: `src/sloth_agent/core/tools/models.py`（新建）

**内容** (spec §3, §5.1):

```python
class ToolCategory(str, Enum):
    READ = "read"
    WRITE = "write"
    EDIT = "edit"
    EXECUTE = "execute"
    SEARCH = "search"
    VCS = "vcs"

class ToolCallRequest(BaseModel):
    tool_name: str
    params: dict[str, Any]
    source: str = "direct"  # "direct" | "keyword" | "llm"
    confidence: float = 1.0

class ToolResult(BaseModel):
    success: bool
    output: str = ""
    error: str | None = None
    duration_ms: int = 0
    retries: int = 0
    tool_name: str = ""

class ToolExecutionRecord(BaseModel):
    tool_name: str
    request_params: dict[str, Any]
    success: bool
    output_summary: str | None = None
    error: str | None = None
    duration_ms: int = 0
    approved_by: str | None = None
    interruption_id: str | None = None

class RiskDecision(BaseModel):
    approved: bool
    reason: str
    requires_user_question: bool = False
    question: str | None = None

class Interruption(BaseModel):
    id: str
    type: str = "tool_approval"
    tool_name: str
    request_params: dict[str, Any]
    reason: str
```

**验收**: 所有 model 可序列化/反序列化，`ToolExecutionRecord` 与 Task 1 的 `RunState.tool_history` 类型兼容。

---

### 步骤 2.2: 扩展 Tool 基类，增加 metadata

**文件**: `src/sloth_agent/core/tools/tool_registry.py`（修改）

**内容** (spec §3):

在现有 `Tool` 基类上增加：
- `category: ToolCategory`
- `metadata: ToolMetadata`（timeout, retry, rollback_strategy, requires_approval）
- `get_schema() -> dict`（生成 function calling schema）

**验收**: 现有工具（FileReadTool/FileWriteTool/BashTool/GitTool/SearchTool）都带 category 和 metadata。

---

### 步骤 2.3: 实现 `HallucinationGuard`

**文件**: `src/sloth_agent/core/tools/hallucination_guard.py`（新建）

**内容** (spec architecture §7.1.3):

```python
class HallucinationGuard:
    def validate_tool_call(self, call: ToolCallRequest) -> ToolCallRequest | RejectedCall:
        match call.tool_name:
            case "read_file" | "write_file" | "edit_file":
                return self._validate_file_path(call)
            case "run_command":
                return self._validate_command(call)
            case "glob" | "grep":
                return self._validate_pattern(call)
            case _:
                return call  # 未知工具，放行
```

核心校验规则：
- 路径必须在 workspace 内（`is_within_workspace()`）
- `read_file`/`edit_file` 的目标文件必须存在
- 路径不能包含 `..`, `~`, `$(`, `` ` ``
- 命令黑名单: `rm -rf`, `sudo`, `chmod 777`, `curl | sh`, `wget | bash`, `mkfs`, `dd if=`, `> /dev/`, `shutdown`, `reboot`
- 命令长度 ≤ 2000 字符
- 搜索模式长度 ≤ 200 字符

**验收**: 对每种校验规则写单元测试，验证正确路径放行、越权路径拒绝、黑名单命令拒绝。

---

### 步骤 2.4: 实现 `RiskGate`

**文件**: `src/sloth_agent/core/tools/risk_gate.py`（新建）

**内容** (spec §4.2):

```python
class RiskGate:
    def __init__(self, config: Config, registry: ToolRegistry, guard: HallucinationGuard):
        self.config = config
        self.registry = registry
        self.guard = guard

    def evaluate(self, request: ToolCallRequest) -> RiskDecision:
        # 1. HallucinationGuard 校验
        validated = self.guard.validate_tool_call(request)
        if isinstance(validated, RejectedCall):
            return RiskDecision(approved=False, reason=validated.reason)

        # 2. 风险等级检查
        tool = self.registry.get_tool(request.tool_name)
        if not tool:
            return RiskDecision(approved=False, reason=f"Unknown tool: {request.tool_name}")

        if tool.risk_level <= self.config.chat.auto_approve_risk_level:
            return RiskDecision(approved=True, reason="auto-approved by config")

        if self._in_autonomous_window():
            return RiskDecision(approved=True, reason="autonomous mode window")

        return RiskDecision(
            approved=False,
            reason=f"risk level {tool.risk_level} requires approval",
            requires_user_question=True,
        )
```

**验收**: Risk 1-2 自动放行，Risk 3 在自主窗口放行、交互模式需确认，Risk 4 始终需确认，HallucinationGuard 拒绝的调用不进入执行。

---

### 步骤 2.5: 实现 `Executor`

**文件**: `src/sloth_agent/core/tools/executor.py`（新建）

**内容** (spec §4.3):

- 参数校验
- 超时控制
- 指数退避重试
- 调用日志写 `logs/tool-calls.jsonl`

**验收**: 成功调用返回 `ToolResult(success=True)`，失败调用有重试记录，超时调用正确返回。

---

### 步骤 2.6: 实现 `ResultFormatter`

**文件**: `src/sloth_agent/core/tools/formatter.py`（新建）

**内容** (spec §4.4):

- `for_human()` — 人类可读
- `for_llm()` — LLM 上下文格式
- `for_log()` — 审计日志格式

**验收**: 输入同一 `ToolResult`，三种输出格式正确且稳定。

---

### 步骤 2.7: 实现 `ToolOrchestrator`

**文件**: `src/sloth_agent/core/tools/orchestrator.py`（新建）

**内容** (spec §5):

```python
class ToolOrchestrator:
    def __init__(self, config: Config, llm_provider, registry: ToolRegistry):
        self.config = config
        self.llm_provider = llm_provider
        self.registry = registry
        self.risk_gate = RiskGate(config, registry, HallucinationGuard())
        self.executor = Executor(registry, config)
        self.formatter = ResultFormatter()

    def execute(self, state: RunState, request: ToolCallRequest) -> ToolResult | Interruption:
        # 1. 风险门控
        decision = self.risk_gate.evaluate(request)
        if not decision.approved:
            interruption = Interruption(...)
            state.pending_interruptions.append(interruption)
            return interruption

        # 2. 执行
        result = self.executor.execute(request)

        # 3. 写回 RunState
        record = ToolExecutionRecord(...)
        state.tool_history.append(record)

        return result
```

**验收**: `execute()` 正确串联 RiskGate → Executor → RunState 写回；RiskGate 拒绝时返回 `Interruption`。

---

### 步骤 2.8: 实现 v1.0 核心工具

**文件**: `src/sloth_agent/core/tools/builtin/`（重构现有 + 新增）

v1.0 需要的 6 个核心工具：

| 工具 | 文件 | 动作 | 说明 |
|------|------|------|------|
| `read_file` | `file_ops.py` | **重构** | 现有 FileReadTool 增加 metadata |
| `write_file` | `file_ops.py` | **重构** | 现有 FileWriteTool 增加 metadata |
| `edit_file` | `file_ops.py` | **新建** | 精确字符串替换（对齐 Claude Code edit_file） |
| `run_command` | `shell.py` | **重构** | 现有 BashTool 改名 + 增加 metadata |
| `glob` | `search.py` | **新建** | 文件模式匹配搜索 |
| `grep` | `search.py` | **新建** | 内容正则搜索 |

`edit_file` 必须实现精确字符串替换逻辑：
- 输入 `file_path`, `old_string`, `new_string`
- `old_string` 必须在文件中唯一出现
- 替换后写回文件

**验收**: 每个工具独立单元测试，覆盖成功路径和失败路径（文件不存在、权限不足、模式不匹配等）。

---

### 步骤 2.9: 集成 `Runner.resolve()` 中的 tool_call 分支

**文件**: `src/sloth_agent/core/runner.py`（修改）

将 Task 1 创建的 `Runner.resolve()` 中的 `tool_call` 分支对接到 `ToolOrchestrator.execute()`：

```python
def resolve(self, state: RunState, next_step: NextStep) -> RunState:
    match next_step.type:
        case "tool_call":
            result = self.tool_orchestrator.execute(state, next_step.request)
            if isinstance(result, Interruption):
                state.phase = "paused"
            else:
                # 工具成功，继续下一轮 think
                pass
```

**验收**: `Runner` 接收 `tool_call` NextStep 时，正确调用 `ToolOrchestrator` 并更新 `RunState`。

---

### 步骤 2.10: 编写单元测试

**文件**: `tests/core/tools/`（新建目录）

| 文件 | 覆盖 |
|------|------|
| `test_models.py` | 所有数据模型序列化/反序列化 |
| `test_hallucination_guard.py` | 路径校验、命令黑名单、模式长度 |
| `test_risk_gate.py` | 不同风险等级放行/拒绝逻辑 |
| `test_executor.py` | 成功/失败/超时/重试场景 |
| `test_tool_orchestrator.py` | execute() 全流程，含 mock RiskGate 和 Executor |
| `test_file_ops.py` | read_file/write_file/edit_file 工具 |
| `test_shell.py` | run_command 工具 |
| `test_search.py` | glob/grep 工具 |

---

## 3. 与现有代码的关系

| 现有文件 | 动作 | 原因 |
|----------|------|------|
| `core/tools/tool_registry.py` | **修改** — 增加 metadata 扩展，保留 Tool 基类和 Registry | 现有实现需升级为 spec 格式 |
| `core/tools/builtin/` 目录 | **重构** — 将现有工具搬入，增加 metadata | v1.0 需要 6 个标准工具 |

---

## 4. 文件清单

| 文件 | 动作 |
|------|------|
| `src/sloth_agent/core/tools/models.py` | **新建** |
| `src/sloth_agent/core/tools/hallucination_guard.py` | **新建** |
| `src/sloth_agent/core/tools/risk_gate.py` | **新建** |
| `src/sloth_agent/core/tools/executor.py` | **新建** |
| `src/sloth_agent/core/tools/formatter.py` | **新建** |
| `src/sloth_agent/core/tools/orchestrator.py` | **新建** |
| `src/sloth_agent/core/tools/tool_registry.py` | **修改** — 增加 metadata |
| `src/sloth_agent/core/tools/builtin/file_ops.py` | **重构** — 增加 edit_file |
| `src/sloth_agent/core/tools/builtin/shell.py` | **重构** — BashTool → run_command |
| `src/sloth_agent/core/tools/builtin/search.py` | **重构** — 增加 glob/grep |
| `src/sloth_agent/core/runner.py` | **修改** — tool_call 分支对接 ToolOrchestrator |
| `src/sloth_agent/core/tools/__init__.py` | **修改** — 导出新组件 |
| `tests/core/tools/` | **新建** — 全部单元测试 |

---

## 5. 验收标准

- [ ] `ToolOrchestrator.execute()` 正确串联 IntentResolver → RiskGate → Executor → ResultFormatter
- [ ] `HallucinationGuard` 拦截路径越权、黑名单命令、过长命令/模式
- [ ] `RiskGate` 按风险等级和时间窗口正确放行/拒绝
- [ ] `Executor` 支持超时和指数退避重试
- [ ] 6 个核心工具（read_file/write_file/edit_file/run_command/glob/grep）全部实现
- [ ] `Runner.resolve()` 的 `tool_call` 分支正确调用 `ToolOrchestrator`
- [ ] 所有测试通过，工具结果写回 `RunState.tool_history`
- [ ] `logs/tool-calls.jsonl` 审计日志正确写入

---

*Plan 版本: v1.0.0 | 创建: 2026-04-17*
