# Tools 调用机制规范

> 版本: v1.0.0
> 日期: 2026-04-16
> 状态: 新增
> 依赖: 20260415-tools-design-spec.md（工具清单）, 20260415-workflow-tools-hooks-spec.md（钩子）

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
Phase/Skill/Chat
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

    def invoke(self, intent: str) -> ToolResult:
        """同步调用链。"""
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

*规范版本: v1.0.0*
*创建日期: 2026-04-16*
