# Tools 调用机制规范

> 版本: v1.0.0
> 日期: 2026-04-16
> 状态: 生效中（合并 tools-design-spec 后成为 Module 02 完整工具规范）
> **权威基准**: 工具定义、分组、权限、调用链路均以本文档为准

---

## 1. 问题

现有 `ToolRegistry` 只有注册和直接执行（`registry.get_tool(name).execute(**kwargs)`），缺少以下核心链路：

1. LLM 如何决定调用哪个工具（意图解析）
2. 工具调用前的风险确认（与 Chat Mode / 自主模式联动）
3. 超时/重试/错误恢复机制
4. 工具调用结果的格式化返回（供 LLM 上下文消费）
5. 工具链式调用和并行调用

---

## 2. 架构总览

```
Runner / Phase / Skill / Chat
    │
    ▼
┌──────────────────────────────────────────┐
│           ToolOrchestrator                │
│  （工具调用总调度器）                       │
│                                           │
│  ① IntentResolver → 意图解析              │
│  ② RiskGate       → 风险门控              │
│  ③ Executor       → 执行（超时/重试）      │
│  ④ ResultFormatter → 结果格式化           │
└──────────────┬────────────────────────────┘
               │
               ▼
         ToolRegistry  （已有注册表）
```

### 2.1 与 Runtime Kernel 的集成关系

`ToolOrchestrator` 不是独立流程，而是 `Runner.resolve_next_step()` 的一个分支执行器。

推荐调用关系：

```python
class Runner:
    def resolve_next_step(self, state: RunState, next_step: NextStep) -> None:
        if next_step.type == "tool_call":
            self.tool_orchestrator.execute(state, next_step.request)
```

因此，工具层必须遵循三条约束：

1. 工具结果必须写回 `RunState.tool_history`
2. 高风险工具审批必须返回 `interruption`，而不是直接抛异常结束任务
3. 工具执行失败必须转译成结构化结果，让 runtime 决定是 retry、replan 还是 abort

---

## 3. 工具元数据扩展

在现有 `Tool` 基类上扩展：

```python
from dataclasses import dataclass, field
from enum import Enum

class ToolCategory(str, Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    VCS = "vcs"
    NETWORK = "network"
    LLM = "llm"

class RiskLevel(int, Enum):
    SAFE = 1              # 自动执行，无需确认
    LOW_RISK = 2          # 自动执行，结果可回滚
    MODERATE_RISK = 3     # 自主模式自动；交互模式需确认
    DESTRUCTIVE = 4       # 始终需要人工确认

@dataclass
class ToolParam:
    name: str
    type: str  # "str", "int", "bool", "path", "enum"
    required: bool = True
    default: str | None = None
    description: str = ""

@dataclass
class ToolMetadata:
    name: str
    category: ToolCategory
    risk_level: RiskLevel
    description: str
    parameters: dict[str, ToolParam] = field(default_factory=dict)
    timeout_seconds: int = 300
    retry_count: int = 0
    side_effects: list[str] = field(default_factory=list)
    rollback_strategy: str = "none"  # "auto" | "manual" | "none"
    requires_approval: bool = False
    sandbox_escape_risk: bool = False
```

---

## 4. 调用链路详细设计

### 4.1 步骤 ①：意图解析（IntentResolver）

LLM 通过两种方式触发工具调用：

**方式 A：结构化文本协议（兼容所有模型）**

```
格式: @tool:<tool_name> param1="value1" param2="value2"
示例: @tool:read_file path="src/main.py"
示例: @tool:bash command="pytest tests/" timeout=60
```

**方式 B：LLM 自主决定（需要 IntentResolver 解析）**

当 LLM 输出自然语言描述意图时，IntentResolver 解析并路由到对应工具：

```python
class IntentResolver:
    """解析用户/LLM 意图，路由到对应工具。"""

    KEYWORD_RULES = {
        r"^(读取|打开|查看|read)\s+.*文件?": ("read_file", {"path": 1}),
        r"^(写入|创建|保存|write)\s+.*文件?": ("write_file", {"path": 1}),
        r"^(搜索|查找|search|grep)\s+": ("search", {"pattern": 1}),
        r"^(运行|执行|run|execute)\s+": ("bash", {"command": 1}),
        r"^(提交|commit)\s*": ("git", {"command": "commit -m"}),
    }

    def __init__(self, llm_provider, tool_registry):
        self.llm = llm_provider
        self.registry = tool_registry

    def resolve(self, intent: str) -> ToolCallRequest | None:
        """解析意图，返回工具调用请求。"""
        # 1. 检查结构化协议 @tool:xxx
        direct = self._parse_direct_call(intent)
        if direct:
            return direct

        # 2. 关键词精确匹配
        keyword = self._keyword_match(intent)
        if keyword:
            return keyword

        # 3. LLM 辅助意图分析（fallback）
        return self._llm_analyze(intent)

    def _parse_direct_call(self, intent: str) -> ToolCallRequest | None:
        """解析 @tool:name key="value" 格式。"""
        import re
        match = re.match(r"@tool:(\w+)\s+(.*)", intent)
        if not match:
            return None
        tool_name = match.group(1)
        params_str = match.group(2)
        params = self._parse_params(params_str)
        return ToolCallRequest(tool_name=tool_name, params=params, source="direct")

    def _keyword_match(self, intent: str) -> ToolCallRequest | None:
        """基于关键词快速匹配。"""
        import re
        for pattern, (tool_name, param_map) in self.KEYWORD_RULES.items():
            if re.search(pattern, intent):
                return ToolCallRequest(
                    tool_name=tool_name,
                    params={"intent": intent},
                    source="keyword",
                    confidence=0.7
                )
        return None

    def _llm_analyze(self, intent: str) -> ToolCallRequest | None:
        """使用 LLM 分析意图。"""
        tools = self.registry.list_tools()
        prompt = self._build_routing_prompt(intent, tools)
        response = self.llm.chat([{"role": "user", "content": prompt}])
        return self._parse_llm_response(response)
```

### 4.2 步骤 ②：风险门控（RiskGate）

```python
class RiskGate:
    """工具调用风险门控。

    决策矩阵：
    - Risk 1-2: 始终自动放行
    - Risk 3: 自主模式自动放行；交互模式 AskUserQuestion
    - Risk 4: 始终 AskUserQuestion
    """

    def __init__(self, config: Config):
        self.auto_approve_level = config.chat.auto_approve_risk_level
        self.mode = config.execution.auto_execute_hours  # "09:00-18:00"

    def evaluate(self, request: ToolCallRequest) -> RiskDecision:
        tool = self.registry.get_tool(request.tool_name)
        if not tool:
            return RiskDecision(
                approved=False,
                reason=f"Unknown tool: {request.tool_name}"
            )

        # Level 1: 用户配置的自动审批级别
        if tool.risk_level <= self.auto_approve_level:
            return RiskDecision(approved=True, reason="auto-approved by config")

        # Level 2: 判断当前是否在自主模式时间窗口
        if self._in_autonomous_window():
            if tool.risk_level <= RiskLevel.MODERATE_RISK:
                return RiskDecision(approved=True, reason="autonomous mode window")
            # Risk 4 即使在自主模式也要记录
            return RiskDecision(
                approved=True,
                reason="autonomous-logged (destructive action recorded)"
            )

        # Level 3: 交互模式，需要确认
        return RiskDecision(
            approved=False,
            reason=f"risk level {tool.risk_level} requires user approval",
            requires_user_question=True,
            question=self._build_approval_question(tool, request)
        )

    def _in_autonomous_window(self) -> bool:
        """判断当前是否在自主执行时间窗口内。"""
        from datetime import datetime
        start_str, end_str = self.mode.split("-")
        now = datetime.now().strftime("%H:%M")
        return start_str <= now < end_str
```

### 4.3 步骤 ③：执行器（Executor）

```python
import time
from dataclasses import dataclass

@dataclass
class ToolResult:
    success: bool
    output: str
    error: str | None = None
    duration_ms: int = 0
    retries: int = 0
    tool_name: str = ""
    metadata: dict = field(default_factory=dict)  # 扩展信息

class Executor:
    """工具执行器，带超时控制和重试机制。"""

    def __init__(self, tool_registry, config: Config):
        self.registry = tool_registry
        self.default_timeout = 300  # 5 分钟
        self.call_log: list[dict] = []

    def execute(self, request: ToolCallRequest) -> ToolResult:
        tool = self.registry.get_tool(request.tool_name)
        if not tool:
            return ToolResult(success=False, error=f"Tool not found: {request.tool_name}")

        # 参数校验
        validation = self._validate_params(request.params, tool)
        if not validation.ok:
            return ToolResult(success=False, error=validation.error)

        # 执行（带重试）
        max_retries = tool.retry_count
        timeout = request.params.get("timeout", tool.timeout_seconds)

        for attempt in range(max_retries + 1):
            start = time.monotonic()
            try:
                output = tool.execute(**request.params)
                duration = int((time.monotonic() - start) * 1000)
                result = ToolResult(
                    success=True,
                    output=str(output),
                    duration_ms=duration,
                    retries=attempt,
                    tool_name=request.tool_name,
                )
                self._log_call(request, result)
                return result
            except Exception as e:
                duration = int((time.monotonic() - start) * 1000)
                if attempt < max_retries:
                    wait = min(2 ** attempt, 30)  # 指数退避，上限 30s
                    time.sleep(wait)
                    continue
                result = ToolResult(
                    success=False,
                    error=str(e),
                    duration_ms=duration,
                    retries=attempt,
                    tool_name=request.tool_name,
                )
                self._log_call(request, result)
                return result

    def _validate_params(self, params: dict, tool: Tool) -> ValidationResult:
        """校验工具参数。"""
        pass  # 根据 ToolMetadata.parameters 校验
```

### 4.4 步骤 ④：结果格式化

```python
class ResultFormatter:
    """将工具执行结果格式化为不同消费方需要的格式。"""

    @staticmethod
    def for_human(result: ToolResult) -> str:
        """人类可读格式。"""
        if result.success:
            return (
                f"✅ `{result.tool_name}` 执行成功 ({result.duration_ms}ms)\n"
                f"```\n{result.output}\n```"
            )
        return (
            f"❌ `{result.tool_name}` 执行失败\n"
            f"Error: {result.error}\n"
            f"已重试 {result.retries} 次"
        )

    @staticmethod
    def for_llm(result: ToolResult) -> dict:
        """LLM 上下文格式（供下一轮对话消费）。"""
        return {
            "role": "tool",
            "tool_name": result.tool_name,
            "success": result.success,
            "output": result.output if result.success else None,
            "error": result.error,
        }

    @staticmethod
    def for_log(result: ToolResult) -> dict:
        """审计日志格式。"""
        return {
            "tool": result.tool_name,
            "success": result.success,
            "duration_ms": result.duration_ms,
            "retries": result.retries,
            "error": result.error,
            "timestamp": time.time(),
        }
```

---

## 5. ToolOrchestrator（总调度器）

```python
class ToolOrchestrator:
    """工具调用总调度器。

    串联 IntentResolver → RiskGate → Executor → ResultFormatter。
    """

    def __init__(self, config: Config, llm_provider, tool_registry):
        self.config = config
        self.intent_resolver = IntentResolver(llm_provider, tool_registry)
        self.risk_gate = RiskGate(config)
        self.executor = Executor(tool_registry, config)
        self.formatter = ResultFormatter()
        self.call_history: list[dict] = []

    def execute(self, state: RunState, request: ToolCallRequest) -> ToolResult | Interruption:
        """由 Runner 调用的工具执行入口。"""
        decision = self.risk_gate.evaluate(request)
        if not decision.approved:
            interruption = Interruption.from_risk_decision(decision, request)
            state.pending_interruptions.append(interruption)
            return interruption

        result = self.executor.execute(request)
        state.tool_history.append(ToolExecutionRecord.from_result(request, result))
        self.call_history.append(self.formatter.for_log(result))
        return result

    def invoke(self, intent: str) -> ToolResult:
        """兼容入口：供简单脚本或单元测试直接调用。"""
        # 1. 意图解析
        request = self.intent_resolver.resolve(intent)
        if not request:
            return ToolResult(success=False, error="No tool matched intent")

        # 2. 风险门控
        decision = self.risk_gate.evaluate(request)
        if not decision.approved:
            if decision.requires_user_question:
                # 返回决策信息，由上层 AskUserQuestion
                return ToolResult(
                    success=False,
                    error="pending_approval",
                    metadata={"question": decision.question}
                )
            return ToolResult(success=False, error=decision.reason)

        # 3. 执行
        result = self.executor.execute(request)

        # 4. 记录
        self.call_history.append(self.formatter.for_log(result))

        return result

    async def invoke_parallel(self, intents: list[str]) -> list[ToolResult]:
        """并行执行多个工具调用（无依赖关系）。"""
        import asyncio
        tasks = [asyncio.to_thread(self.invoke, intent) for intent in intents]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r if isinstance(r, ToolResult) else ToolResult(success=False, error=str(r)) for r in results]

    def invoke_chain(self, intents: list[str]) -> list[ToolResult]:
        """链式执行：上一个工具的输出作为下一个工具的输入上下文。"""
        results = []
        context = {}
        for intent in intents:
            enriched = self._inject_context(intent, context)
            result = self.invoke(enriched)
            results.append(result)
            if result.success:
                context["last_output"] = result.output
            else:
                break  # 链式失败时停止
        return results

    def _inject_context(self, intent: str, context: dict) -> str:
        """将前一个工具的输出注入到意图中。"""
        if "last_output" in context:
            return f"{intent}\n[Previous output: {context['last_output'][:500]}]"
        return intent
```

### 5.1 Tool Execution Record

工具调用后，最小写回记录应为：

```python
@dataclass
class ToolExecutionRecord:
    tool_name: str
    request_params: dict
    success: bool
    output_summary: str | None
    error: str | None
    duration_ms: int
    approved_by: str | None = None
    interruption_id: str | None = None
```

这份记录进入 `RunState.tool_history`，供后续：

- LLM 下一轮思考
- reflection 分析
- 审计与 observability
- Tool-Use 学习

### 5.2 审批暂停与恢复语义

高风险工具调用不应被建模成“执行失败”，而应被建模成“当前 run 暂停”。

```python
@dataclass
class Interruption:
    id: str
    type: Literal["tool_approval"]
    tool_name: str
    request_params: dict
    reason: str
```

生命周期：

1. `Runner` 收到 `tool_call`
2. `ToolOrchestrator` 调用 `RiskGate`
3. 若需审批，返回 `Interruption`
4. `RunState.pending_interruptions` 写入该中断
5. 外部系统批准/拒绝后，从原 `RunState` 恢复执行

恢复原则：

- 恢复的是同一个 run，不是新任务
- 不能重新生成新的 tool request 覆盖旧请求
- 审批记录必须进入 `ToolExecutionRecord.approved_by`

### 5.3 链式与并行调用的运行时约束

`invoke_parallel()` 与 `invoke_chain()` 只有在 runtime 合同允许时才能使用：

#### 并行调用

- 仅允许无写写冲突、无顺序依赖、无共享可变状态的工具组合
- 若任一工具需要审批，整个并行批次必须拆分成可恢复子批次

#### 链式调用

- 每一步结果都必须写回 `RunState`
- 任一步失败都必须显式交给 runtime 决定：继续、重试、重规划、终止
- 不允许把链式失败静默吞掉后继续构造下一步请求

因此，更推荐的做法是由 `Runner` 规划链式/并行策略，`ToolOrchestrator` 只负责执行。

### 5.4 HallucinationGuard（幻觉检测层）

Agent 的工具调用可能基于 LLM 幻觉（伪造文件路径、不存在的命令、错误参数）。v1.0 在工具执行器中加入校验层，在 RiskGate 之后、Executor 之前执行：

```python
class HallucinationGuard:
    """工具调用前的幻觉检测"""

    def validate_tool_call(self, call: ToolCall) -> ToolCall | RejectedCall:
        match call.tool_name:
            case "read_file" | "write_file" | "edit_file":
                return self._validate_file_path(call)
            case "run_command":
                return self._validate_command(call)
            case "glob" | "grep":
                return self._validate_pattern(call)
            case _:
                return call  # 未知工具，放行（由 Executor 处理）

    def _validate_file_path(self, call: ToolCall) -> ToolCall | RejectedCall:
        path = call.args.get("path", "")
        # 规则 1: 路径必须在 workspace 内
        if not is_within_workspace(path):
            return RejectedCall(call, "路径越权: 不在 workspace 内")
        # 规则 2: read_file/edit_file 的目标必须存在
        if call.tool_name in ("read_file", "edit_file") and not Path(path).exists():
            return RejectedCall(call, f"文件不存在: {path}",
                                hint="请先用 glob 搜索正确路径")
        # 规则 3: 路径不能包含可疑模式
        if any(p in path for p in ["..", "~", "$(", "`"]):
            return RejectedCall(call, f"路径包含可疑字符: {path}")
        return call

    def _validate_command(self, call: ToolCall) -> ToolCall | RejectedCall:
        cmd = call.args.get("command", "")
        # 规则 1: 黑名单命令
        blacklist = ["rm -rf", "sudo", "chmod 777", "curl | sh", "wget | bash",
                     "mkfs", "dd if=", "> /dev/", "shutdown", "reboot"]
        for b in blacklist:
            if b in cmd:
                return RejectedCall(call, f"黑名单命令: {b}")
        # 规则 2: 不允许链式命令中隐藏危险操作
        if "|" in cmd or ";" in cmd:
            parts = re.split(r'[|;]', cmd)
            for part in parts:
                if any(b in part.strip() for b in blacklist):
                    return RejectedCall(call, f"链式命令中包含危险操作: {part}")
        # 规则 3: 命令长度上限（防止注入超长 payload）
        if len(cmd) > 2000:
            return RejectedCall(call, "命令过长（>2000 字符），可能是注入攻击")
        return call

    def _validate_pattern(self, call: ToolCall) -> ToolCall | RejectedCall:
        pattern = call.args.get("pattern", "")
        # 防止 ReDoS（正则拒绝服务）
        if len(pattern) > 200:
            return RejectedCall(call, "搜索模式过长")
        return call
```

RejectedCall 处理：
- 返回结构化错误信息给 LLM（包含 hint）
- LLM 根据 hint 修正后重试
- 连续 3 次 rejected → 触发 Reflection
- 所有 rejection 记录到 tool_stats.jsonl（供 Tool-Use Learning 分析）

### 5.5 StreamProcessor（流式处理）

`StreamProcessor` 处理 LLM streaming 输出：文本 chunk 直接输出，tool_call chunk 拦截执行后结果回注。

```python
class StreamProcessor:
    """处理 LLM streaming 输出，拦截工具调用并执行"""

    async def process_stream(self, stream: AsyncIterator[Chunk]) -> AsyncIterator[OutputEvent]:
        tool_buffer = []  # 缓冲不完整的 tool_call JSON

        async for chunk in stream:
            match chunk.type:
                case "text":
                    yield TextEvent(chunk.content)  # 直接流式输出

                case "tool_call_start":
                    tool_buffer = [chunk]
                    yield StatusEvent(f"🔧 调用 {chunk.tool_name}...")

                case "tool_call_delta":
                    tool_buffer.append(chunk)  # 缓冲参数片段

                case "tool_call_end":
                    # 完整 tool call 已收到，执行
                    tool_call = self._assemble_tool_call(tool_buffer)
                    yield StatusEvent(f"⚡ 执行 {tool_call.tool_name}")

                    # 执行工具（经过 RiskGate + HallucinationGuard）
                    result = await self.tool_executor.execute(tool_call)
                    yield ToolResultEvent(tool_call, result)

                    # 结果回注 LLM，继续 streaming
                    tool_buffer = []

                case "error":
                    yield ErrorEvent(chunk.error)

                case "done":
                    yield DoneEvent(usage=chunk.usage)
```

v1.0 Provider 对接：
- DeepSeek: SSE (text/event-stream)，兼容 OpenAI 格式
- Qwen: SSE，兼容 OpenAI 格式
- 统一适配：所有 Provider 输出转换为内部 Chunk 格式

关键约束：
- 不使用 WebSocket（v1.0 无 Web UI）
- CLI 模式下 streaming 直接写 stdout
- 飞书模式下 (v1.2) 按段落缓冲后推送（避免过于碎片化）
- tool call 期间挂起 streaming（串行，不并发）

---

## 6. LLM 工具调用协议

### 6.1 Function Calling 兼容

当 LLM Provider 支持 function calling 时，ToolOrchestrator 将工具注册为函数 schema：

```python
def build_function_schemas(tool_registry) -> list[dict]:
    """将工具注册为 OpenAI-compatible function calling schema。"""
    schemas = []
    for tool in tool_registry.list_tools():
        schemas.append({
            "name": tool.name,
            "description": tool.description,
            "parameters": {
                "type": "object",
                "properties": {
                    name: {"type": param.type, "description": param.description}
                    for name, param in tool.parameters.items()
                },
                "required": [name for name, param in tool.parameters.items() if param.required]
            }
        })
    return schemas
```

### 6.2 文本协议（fallback）

当模型不支持 function calling 时，使用文本协议：

```
# 工具调用标记
@tool:<name> <params>

# 工具结果标记
[tool:<name> result]
<output>
[/tool]

# 示例对话
User: 读取 src/main.py 的内容
Assistant: @tool:read_file path="src/main.py"
System: [tool:read_file result]
def main(): ...
[/tool]
Assistant: 文件内容如下...
```

---

## 7. 错误处理与恢复

### 7.1 错误分类

| 错误类型 | 处理方式 | 示例 |
|----------|---------|------|
| 参数错误 | 立即返回，不重试 | 路径不存在、类型不匹配 |
| 执行超时 | 按重试次数退避 | 命令执行超过 timeout |
| 权限错误 | 返回审批请求 | 需要 sudo 的文件操作 |
| 资源错误 | 返回，建议用户介入 | 磁盘满、端口被占用 |
| 网络错误 | 自动重试 | API 连接失败、超时 |

### 7.2 回滚策略

```python
class RollbackManager:
    """管理工具执行失败后的回滚。"""

    def rollback(self, result: ToolResult, tool: Tool) -> RollbackResult:
        if tool.rollback_strategy == "none":
            return RollbackResult(success=False, reason="no rollback strategy")

        if tool.rollback_strategy == "auto":
            return self._auto_rollback(result, tool)

        if tool.rollback_strategy == "manual":
            return RollbackResult(
                success=False,
                reason="manual rollback required",
                requires_user_action=True,
                suggestion=self._build_rollback_suggestion(result, tool)
            )

    def _auto_rollback(self, result: ToolResult, tool: Tool) -> RollbackResult:
        """自动回滚。"""
        # write_file → 删除刚创建的文件
        # bash → 无法自动回滚，记录状态
        pass
```

---

## 8. 审计日志

每次工具调用都记录到审计日志：

```python
@dataclass
class ToolCallLog:
    timestamp: float
    tool_name: str
    intent: str
    params: dict
    risk_level: int
    decision: str  # "auto-approved" | "user-approved" | "rejected"
    success: bool
    duration_ms: int
    retries: int
    error: str | None
    caller: str  # "phase:implementing" | "chat" | "skill:xxx"
```

日志持久化到 `logs/tool-calls.jsonl`，用于：
- 安全审计（谁在什么时候调用了什么工具）
- 性能分析（哪些工具经常超时/失败）
- 技能进化（工具调用失败模式识别）

---

## 9. 文件清单

| 文件 | 说明 |
|------|------|
| `src/sloth_agent/core/tools/orchestrator.py` | ToolOrchestrator 总调度器 |
| `src/sloth_agent/core/tools/intent_resolver.py` | 意图解析器 |
| `src/sloth_agent/core/tools/risk_gate.py` | 风险门控 |
| `src/sloth_agent/core/tools/executor.py` | 执行器 |
| `src/sloth_agent/core/tools/formatter.py` | 结果格式化 |
| `src/sloth_agent/core/tools/rollback.py` | 回滚管理 |
| `src/sloth_agent/core/tools/models.py` | 数据模型（ToolCallRequest, ToolResult 等） |
| `logs/tool-calls.jsonl` | 审计日志（运行时生成） |

---

---

## 10. 工具权限级别（从跨模块规范迁入）

| 级别 | 工具 | 风险 | 需要审批 |
|------|------|------|---------|
| L1 | Read, Glob, Grep | 低 | 否 |
| L2 | Write, Edit, Bash (safe) | 中 | 首次 |
| L3 | Bash (destructive) | 高 | 明确审批 |
| L4 | git push, rm -rf | 极高 | 每次 |

权限级别与 RiskLevel 的映射关系：

| 权限级别 | 对应 RiskLevel | 审批策略 |
|---------|---------------|---------|
| L1 | SAFE (1) | 自动放行 |
| L2 | LOW_RISK (2) / MODERATE_RISK (3) | 首次需确认，后续在自主窗口内自动 |
| L3 | MODERATE_RISK (3) / DESTRUCTIVE (4) | 明确审批，每次确认 |
| L4 | DESTRUCTIVE (4) | 每次明确审批，不可跳过 |

---

---

## 10. 工具定义层（从 20260415-tools-design-spec.md 迁入）

> 本文档合并后成为 Module 02 的完整工具规范：§1-§9 定义"工具怎么调用"，§10 定义"工具是什么"。

### 10.1 设计原则

| 原则 | 说明 |
|------|------|
| **YAGNI** | 不构建不需要的工具，按需扩展 |
| **融合优秀设计** | 继承 Claude Code / Open Claw 的精华 |
| **Rust 优先** | Rust 项目（卡牌游戏、五行运势 APP）优先 |
| **风险分级** | 工具按风险分级 + 权限分级，双重门控 |

### 10.2 代码约定

工具类名使用 PascalCase（如 `ReadFileTool`），工具名（`name` 属性）使用 snake_case（如 `read_file`）。

### 10.3 工具分类体系

#### 10.3.1 工具分组（group）

每个工具属于以下分组之一：

```
group: fs            # 文件系统工具 — Read, Write, Edit, Glob, Grep
group: runtime       # 运行时/执行工具 — Bash/run_command, exec, TaskRun
group: code          # 代码智能工具 — LSP, rust_analyzer, typescript_lsp
group: task          # 任务管理工具 — TaskCreate, TaskList, TaskUpdate, TaskGet
group: web           # Web 工具 — WebFetch, WebSearch
group: sloth         # Sloth 特色工具 — Checkpoint, Heartbeat, Skill*, Test*, Coverage*
group: interaction   # 交互工具 — AskUserQuestion, ApprovalRequest
```

#### 10.3.2 语义分类（category）

用于工具运行时的语义识别：

```
category: read       # 读取操作
category: write      # 写入操作
category: edit       # 编辑操作
category: execute    # 执行操作
category: search     # 搜索操作
category: vcs        # 版本控制
category: network    # 网络操作
category: llm        # LLM 操作
```

#### 10.3.3 权限分级（permission）

| 等级 | 值 | 说明 | 审批要求 |
|------|---|------|---------|
| L1 | `auto` | 只读/低风险 | 自动执行 |
| L2 | `plan_approval` | 写操作/不破坏性 | 计划审批一次后自动 |
| L3 | `explicit_approval` | Shell 执行/可能破坏 | 每次逐次审批 |
| L4 | `high_risk` | 系统级操作 | 明确标注 + 额外审批 |

### 10.4 工具基类定义

#### 10.4.1 Python 实现

```python
class Tool:
    """工具基类。所有工具必须继承此类。"""
    name: str                    # snake_case 工具名，如 "read_file"
    description: str             # 工具描述
    group: str                   # 所属分组：fs/runtime/code/task/web/sloth/interaction
    risk_level: int = 1          # 风险等级 1-4
    permission: str = "auto"     # auto / plan_approval / explicit_approval / high_risk
    inherit_from: str | None = None  # 继承来源：ClaudeCode / OpenClaw / Sloth / None
    params: dict = {}            # 参数定义 {param_name: {type, required, default, description}}

    def execute(self, **kwargs) -> Any:
        """执行工具。子类必须实现。"""
        raise NotImplementedError

    def get_schema(self) -> dict:
        """生成 OpenAI-compatible function calling schema。"""
        raise NotImplementedError
```

#### 10.4.2 工具注册表

```python
class ToolRegistry:
    """工具注册表。管理所有工具的注册、查询、按组列出。"""

    def __init__(self, config: Config):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool, group: str | None = None):
        """注册工具。group 可选，若 tool 已有 group 则忽略。"""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        """按名称获取工具。"""
        return self._tools.get(name)

    def list_all(self) -> list[Tool]:
        """列出所有工具。"""
        return list(self._tools.values())

    def list_by_group(self, group: str) -> list[Tool]:
        """按分组列出工具。"""
        return [t for t in self._tools.values() if t.group == group]

    def execute_tool(self, name: str, **kwargs) -> Any:
        """按名称执行工具。"""
        tool = self.get(name)
        if not tool:
            raise ValueError(f"Unknown tool: {name}")
        return tool.execute(**kwargs)
```

### 10.5 核心工具清单

#### 10.5.1 文件系统工具 (group:fs)

| 工具名 | 功能 | risk_level | permission | 继承来源 | 优先级 |
|--------|------|-----------|-----------|----------|--------|
| `read_file` | 读取文件内容 | 1 | auto | Claude Code | ✅ 必需 |
| `write_file` | 创建/覆盖文件 | 2 | plan_approval | Claude Code | ✅ 必需 |
| `edit_file` | 精准编辑文件 | 2 | plan_approval | Claude Code | ✅ 必需 |
| `glob` | 按模式匹配文件 | 1 | auto | Claude Code | ✅ 必需 |
| `grep` | 搜索文件内容 | 1 | auto | Claude Code | ✅ 必需 |
| `apply_patch` | 多-hunk 批量补丁 | 2 | plan_approval | Open Claw | ⚠️ 建议 |

**read_file**:
```python
def read_file(path: str, encoding: str = "utf-8") -> str:
    """读取文件全部内容。"""

def read_lines(path: str, start: int = 1, end: int | None = None) -> list[str]:
    """按行读取文件。start 从 1 开始计数。end 为 None 时读到末尾。"""
```

**write_file**:
```python
def write_file(path: str, content: str, encoding: str = "utf-8") -> str:
    """创建或覆盖文件。自动创建父目录。返回写入字节数摘要。"""
```

**edit_file**:
```python
def edit_file(file_path: str, old_string: str, new_string: str, encoding: str = "utf-8") -> str:
    """精确替换文件中唯一出现的 old_string。
    若 old_string 不出现或出现多次，抛出 ValueError。
    """
```

**glob**:
```python
def glob(pattern: str, root: str = ".") -> list[str]:
    """按 glob 模式匹配文件，返回匹配的文件路径列表。"""
```

**grep**:
```python
def grep(pattern: str, root: str = ".", file_pattern: str = "*", max_results: int = 100) -> list[dict]:
    """正则搜索文件内容。返回 [{file, line, content}]。"""
```

**apply_patch**:
```python
def apply_patch(patch: str, root: str = ".") -> str:
    """应用多-hunk 统一 diff 格式的补丁。支持批量修改多个文件。"""
```

#### 10.5.2 运行时工具 (group:runtime)

| 工具名 | 功能 | risk_level | permission | 继承来源 | 优先级 |
|--------|------|-----------|-----------|----------|--------|
| `run_command` | 执行 Shell 命令 | 3 | explicit_approval | Claude Code | ✅ 必需 |
| `exec` | 带进程管理的 Shell | 3 | explicit_approval | Open Claw | ⚠️ 增强 |
| `task_run` | 运行任务 (cargo/npm) | 2 | auto_after_plan | Sloth | ✅ 必需 |

**run_command**:
```python
def run_command(command: str, timeout: int = 300) -> dict:
    """执行 Shell 命令。返回 {returncode, stdout, stderr}。
    别名: bash（与 Claude Code 兼容）。
    """
```

**exec**:
```python
def exec(command: str, background: bool = False, timeout: int | None = None) -> dict:
    """执行命令并管理进程。支持后台运行、终止进程、列出进程。"""
```

**task_run**:
```python
def task_run(task: str, project_type: str = "auto") -> dict:
    """在 workspace 中执行任务（Rust cargo / npm / pytest 等）。
    project_type: "rust" | "node" | "python" | "auto"
    """
```

#### 10.5.3 代码智能工具 (group:code)

| 工具名 | 功能 | risk_level | permission | 继承来源 | 优先级 |
|--------|------|-----------|-----------|----------|--------|
| `lsp` | 语言服务器（跳转定义/类型检查） | 1 | auto | Claude Code | ✅ 必需 |
| `rust_analyzer` | Rust 代码分析 | 1 | auto | Sloth | ✅ 必需 |
| `typescript_lsp` | TS/JS 代码分析 | 1 | auto | Sloth | ⚠️ React 需要 |

#### 10.5.4 任务管理工具 (group:task)

| 工具名 | 功能 | risk_level | permission | 继承来源 | 优先级 |
|--------|------|-----------|-----------|----------|--------|
| `task_create` | 创建任务 | 1 | auto | Claude Code | ✅ 必需 |
| `task_list` | 列出任务 | 1 | auto | Claude Code | ✅ 必需 |
| `task_update` | 更新任务状态 | 1 | auto | Claude Code | ✅ 必需 |
| `task_get` | 获取任务详情 | 1 | auto | Claude Code | ⚠️ 建议 |

#### 10.5.5 Web 工具 (group:web)

| 工具名 | 功能 | risk_level | permission | 继承来源 | 优先级 |
|--------|------|-----------|-----------|----------|--------|
| `web_fetch` | 获取 URL 内容 | 2 | plan_approval | Claude Code | ✅ 必需 |
| `web_search` | 网络搜索 | 2 | plan_approval | Claude Code | ⚠️ 建议 |

#### 10.5.6 交互工具 (group:interaction)

| 工具名 | 功能 | risk_level | permission | 继承来源 | 优先级 |
|--------|------|-----------|-----------|----------|--------|
| `ask_user_question` | 向用户提问 | 1 | auto | Claude Code | ✅ 必需 |
| `approval_request` | 发送审批请求 | 1 | auto | Sloth | ✅ 必需 |

#### 10.5.7 Sloth 特色工具 (group:sloth)

**可靠性工具**:

| 工具名 | 功能 | risk_level | permission | 优先级 |
|--------|------|-----------|-----------|--------|
| `checkpoint_save` | 保存执行状态 | 1 | auto | ✅ 必需 |
| `checkpoint_load` | 恢复执行状态 | 1 | auto | ✅ 必需 |
| `heartbeat` | 发送心跳 | 1 | auto | ✅ 必需 |

**技能进化工具**:

| 工具名 | 功能 | risk_level | permission | 优先级 |
|--------|------|-----------|-----------|--------|
| `skill_generate` | 从错误生成新技能 | 1 | auto | ✅ 必需 |
| `skill_revise` | 修正已有技能 | 1 | auto | ✅ 必需 |
| `skill_search` | 搜索相关技能 | 1 | auto | ✅ 必需 |

**TDD 工具**:

| 工具名 | 功能 | risk_level | permission | 优先级 |
|--------|------|-----------|-----------|--------|
| `test_runner` | 运行测试 | 2 | plan_approval | ✅ 必需 |
| `coverage_check` | 检查覆盖率 | 1 | auto | ✅ 必需 |
| `coverage_gate` | 覆盖率门槛检查 | 1 | auto | ✅ 必需 |

### 10.6 权限与风险门控

#### 10.6.1 双重门控

工具调用需同时通过两层检查：

1. **Permission 层**（本规范定义）：基于 `permission` 字段的静态策略
2. **RiskGate 层**（§4.2 定义）：基于 `risk_level` + 运行时的动态决策

两层检查串联执行，任何一层拒绝则调用被拦截。

#### 10.6.2 Permission 层策略

| permission | 策略 |
|-----------|------|
| `auto` | 始终自动放行 |
| `plan_approval` | 计划审批一次后自动放行；无计划时需确认 |
| `explicit_approval` | 每次都需要用户明确确认 |
| `high_risk` | 每次都需要明确标注 + 额外审批 |

#### 10.6.3 风险等级矩阵

| risk_level | 名称 | Permission 层 | RiskGate 层 |
|-----------|------|-------------|-----------|
| 1 | SAFE | auto | 自动放行 |
| 2 | LOW_RISK | plan_approval | 自动放行，结果可回滚 |
| 3 | MODERATE_RISK | explicit_approval | 自主模式自动；交互需确认 |
| 4 | DESTRUCTIVE | high_risk | 始终需要人工确认 |

### 10.7 配置

#### 10.7.1 configs/tools.yaml

```yaml
tools:
  groups:
    fs:
      - read_file
      - write_file
      - edit_file
      - glob
      - grep
    runtime:
      - run_command
      - exec
      - task_run
    code:
      - lsp
      - rust_analyzer
    task:
      - task_create
      - task_list
      - task_update
    web:
      - web_fetch
    interaction:
      - ask_user_question
      - approval_request
    sloth:
      - checkpoint_save
      - checkpoint_load
      - heartbeat
      - skill_generate
      - skill_revise
      - test_runner
      - coverage_check
```

#### 10.7.2 configs/permissions.yaml

```yaml
permissions:
  default_policy: ask  # 默认需要确认

  auto:
    - read_file
    - glob
    - grep
    - task_create
    - task_list
    - task_update
    - heartbeat
    - checkpoint_save
    - checkpoint_load
    - skill_generate
    - skill_revise
    - ask_user_question
    - lsp
    - rust_analyzer
    - coverage_check
    - coverage_gate

  plan_approval:
    - write_file
    - edit_file
    - apply_patch
    - test_runner
    - web_fetch
    - web_search

  explicit_approval:
    - run_command
    - exec
    - task_run

  high_risk:
    - delete_file
    - git_force_push
```

### 10.8 项目定制配置

#### 10.8.1 通用配置（所有项目）

```yaml
core_tools:
  - read_file
  - write_file
  - edit_file
  - glob
  - grep
  - run_command
  - task_create
  - task_list
  - task_update
  - lsp
  - web_fetch
  - ask_user_question
  - checkpoint_save
  - checkpoint_load
  - heartbeat
  - skill_generate
  - skill_revise
  - test_runner
  - coverage_check
```

#### 10.8.2 Rust 项目配置

```yaml
rust_tools:
  cargo: true
  rust_analyzer: true
  rustfmt: true
  clippy: true
  build_targets:
    - cargo build
    - cargo test
    - cargo clippy
  extra_tools:
    - wasm-pack  # 如果需要 WebAssembly
```

#### 10.8.3 前端 React 配置

```yaml
react_tools:
  npm: true
  typescript_lsp: true
  eslint: true
  build_targets:
    - npm run build
    - npm test
    - npm run lint
```

### 10.9 工具注册机制

工具通过 `ToolRegistry.register(tool)` 注册，通过 `get(name)` 获取，通过 `list_by_group(group)` 按组查询（见 §3.2 ToolRegistry 定义）。

### 10.10 扩展机制

#### 10.10.1 MCP 工具适配（后续）

```yaml
mcp:
  enabled: false
  servers: []
```

#### 10.10.2 自定义工具注册

```yaml
custom_tools:
  - name: my_tool
    command: "python scripts/my_tool.py"
    risk_level: 2
    group: runtime
    permission: explicit_approval
```

### 10.11 实现优先级

**第一阶段（核心必需）**:
```
✅ read_file, write_file, edit_file, glob, grep
✅ run_command, task_create, task_list, task_update
✅ checkpoint_save, checkpoint_load, heartbeat
✅ web_fetch, ask_user_question
✅ skill_generate, skill_revise
```

**第二阶段（建议）**:
```
⚠️ apply_patch (多文件编辑)
⚠️ test_runner, coverage_check
⚠️ lsp (rust_analyzer)
⚠️ web_search
```

**第三阶段（按需）**:
```
⚠️ exec (进程管理)
⚠️ code_execution (沙箱执行)
⚠️ typescript_lsp
⚠️ wasm-pack, xcodebuild, android_sdk
```

### 10.12 参考来源

| 来源 | 工具 | 说明 |
|------|------|------|
| Claude Code | read_file, write_file, edit_file, glob, grep, run_command, task*, lsp | 核心必需 |
| Claude Code | web_fetch, web_search, ask_user_question | Web + 交互 |
| Open Claw | apply_patch | 多-hunk 补丁 |
| Open Claw | exec | 进程管理 |
| Open Claw | code_execution | 沙箱执行 |
| Sloth 设计 | checkpoint, heartbeat | 可靠性 |
| Sloth 设计 | skill_generate/revise | 自进化 |
| Sloth 设计 | coverage_check/gate | TDD |

---

*规范版本: v1.0.0*
*创建日期: 2026-04-16*
