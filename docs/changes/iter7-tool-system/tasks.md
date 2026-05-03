# Tasks: Iter-7 Tool 系统 + 上下文引擎（装饰器模式版）

> 关联变更: docs/changes/iter7-tool-system/
> 日期: 2026-05-05（修订）
> 预计: 3 天
>
> 决策（2026-05-04）：Iter-7 仅实现本地只读工具（`read`、`read_range`、`grep`、`grep_repo`、`glob`、`ls_dir`），`websearch`/`webfetch` 延后到 Iter-8 的受限网络工具包。

---

## Task 7.0: Tool 引擎核心（½ 天）

**文件：** `backend/app/core/tool_engine.py`（新建）

不依赖 CLI `src/sloth_agent` 包，从头实现。

- [ ] 定义 `ToolDef` dataclass：
  ```python
  @dataclass
  class ToolDef:
      name: str
      description: str
      params_schema: dict[str, Any]   # JSON Schema
      invoke: Callable[[ToolContext, str], Awaitable[str]]
  ```
- [ ] 定义 `ToolContext` dataclass：
  ```python
  @dataclass
  class ToolContext:
      project_root: Path
      agent_id: int
  ```
- [ ] 定义 `ToolSecurityError(Exception)`
- [ ] 实现 `TOOL_POOL: dict[str, ToolDef] = {}`（模块级全局）
- [ ] 实现 `_resolve_safe_path(project_root: Path, user_path: str) -> Path`：
  - `candidate = (project_root / user_path).resolve()`
  - 验证 `candidate` 以 `project_root.resolve()` 开头（防路径遍历）
  - 不存在则 raise `FileNotFoundError`
  - 越界则 raise `ToolSecurityError`
- [ ] 实现 `@desktop_tool` 装饰器：
  - 接受 `async def func(ctx: ToolContext, **kwargs) -> str`
  - 用 `inspect.signature` 获取参数列表（跳过 `ctx`）
  - 用 `pydantic.TypeAdapter` 或手动构建每个参数的 JSON Schema
  - 组装 `params_schema`（JSON Schema，`type: "object"`）
  - 从函数 docstring 提取 description（Google style：第一行或第一段）
  - 创建 `ToolDef.invoke`：解析 args_json → kwargs → 调用原函数
  - 注册到 `TOOL_POOL[func.__name__]`
  - 返回 `ToolDef`（允许 `tool = @desktop_tool async def ...` 方式获取引用）
- [ ] 单元测试 `backend/tests/test_tool_engine.py`：
  - `@desktop_tool` 注册后可从 TOOL_POOL 查找
  - `_resolve_safe_path` 正常路径返回 Path
  - `_resolve_safe_path("../../etc/passwd")` raise ToolSecurityError
  - 装饰器生成的 params_schema 结构正确（含 required、properties）

---

## Task 7.1: 内置工具实现（½ 天）

**文件：** `backend/app/services/tool_defs.py`（新建）

所有工具用 `@desktop_tool` 定义，import 时自动注册到 TOOL_POOL。

> 范围约束：本任务不包含网络工具（`websearch`、`webfetch`）。

- [ ] 实现 `read`：
  ```python
  @desktop_tool
  async def read(ctx: ToolContext, path: str) -> str:
      """Read file contents within the project.

      Args:
          path: Relative path to the file within the project root.
      """
      full_path = _resolve_safe_path(ctx.project_root, path)
      return full_path.read_text(encoding="utf-8")
  ```
- [ ] 实现 `grep`：
  ```python
  @desktop_tool
  async def grep(ctx: ToolContext, pattern: str, path: str) -> str:
      """Search for lines matching a pattern in a file.

      Args:
          pattern: Regular expression pattern to search for.
          path: Relative path to the file within the project root.
      """
  ```
  - 用 `re.finditer`，返回匹配行（行号 + 内容），最多 50 行
- [ ] 实现 `glob`：
  ```python
  @desktop_tool
  async def glob(ctx: ToolContext, pattern: str) -> str:
      """List files matching a glob pattern within the project.

      Args:
          pattern: Glob pattern relative to the project root (e.g., "src/**/*.py").
      """
  ```
  - 用 `ctx.project_root.glob(pattern)`，最多返回 100 个路径
  - 返回相对于 project_root 的路径列表（每行一个）
- [ ] 实现 `read_range`：
  ```python
  @desktop_tool
  async def read_range(ctx: ToolContext, path: str, start_line: int, end_line: int) -> str:
      """Read a line range from a file within the project.

      Args:
          path: Relative path to the file within the project root.
          start_line: 1-based start line.
          end_line: 1-based end line (inclusive).
      """
  ```
  - 仅允许 `1 <= start_line <= end_line`
  - 单次最多返回 400 行（超出自动截断并附加 `...truncated`）
- [ ] 实现 `grep_repo`：
  ```python
  @desktop_tool
  async def grep_repo(ctx: ToolContext, pattern: str, include_glob: str = "**/*") -> str:
      """Search regex matches across files within the project.

      Args:
          pattern: Regular expression pattern.
          include_glob: Glob filter for candidate files.
      """
  ```
  - 先用 `ctx.project_root.glob(include_glob)` 选文件，再逐文件匹配
  - 输出 `path:line:content`，最多 200 条匹配
  - 跳过常见二进制扩展名与超大文件（建议 >1MB）
- [ ] 实现 `ls_dir`：
  ```python
  @desktop_tool
  async def ls_dir(ctx: ToolContext, path: str = ".", max_depth: int = 2) -> str:
      """List directory tree within the project.

      Args:
          path: Relative directory path.
          max_depth: Traversal depth limit.
      """
  ```
  - `max_depth` 取值范围 0-4
  - 最多返回 300 个条目，目录优先、按名称排序
- [ ] 定义 `ROLE_BASE_TOOLS: dict[str, list[str]]`（role 级别基础工具，运行时合并用）：
  ```python
  ROLE_BASE_TOOLS = {
      "lead":    ["read", "grep"],
      "fortune": ["read", "read_range", "glob", "grep", "grep_repo", "ls_dir"],
  }
  ```
- [ ] 单元测试 `backend/tests/test_tool_defs.py`：
  - `read` 读取真实存在文件 → 返回内容
  - `read("../../etc/passwd")` → ToolSecurityError（被 engine 拦截，返回错误字符串）
  - `grep(pattern="def ", path="backend/app/main.py")` → 返回匹配行
  - `glob(pattern="backend/**/*.py")` → 返回 .py 文件列表
  - `read_range(path="README.md", start_line=1, end_line=20)` → 返回行区间
  - `grep_repo(pattern="class ", include_glob="backend/**/*.py")` → 返回跨文件匹配
  - `ls_dir(path="backend", max_depth=2)` → 返回目录树
  - `read_range` 非法区间（如 start > end）→ 返回参数错误

---

## Task 7.2: AgentTemplate.tools 字段 + Seed 更新（½ 天）

**文件：**
- `backend/app/models.py` — 修改 `AgentTemplate`
- `backend/app/services/agent.py` 或 seed 脚本 — 更新 builtin agent tools 字段

- [ ] `AgentTemplate` 新增字段：`tools: str = Field(default="[]")` （JSON 字符串，存储该 agent **个性化追加**工具名列表，默认空）
- [ ] DB migration：`ALTER TABLE agent_templates ADD COLUMN tools TEXT NOT NULL DEFAULT '[]'`（或 drop/recreate SQLite 测试库）
- [ ] builtin agent seed 不需要填充 tools 字段（默认 `[]`，运行时由 `ROLE_BASE_TOOLS` 提供基础工具）
- [ ] `GET /api/settings/agents/{id}` 响应扩展：返回 `tools: list[str]`（JSON 解析后返回，仅含个性化追加部分）
- [ ] 单元测试：验证 seed 后各 builtin agent 的 tools 字段为 `[]`

---

## Task 7.3: BrainstormEngine Function Calling 集成（1 天）

> 所有 6 个内置 Provider（DeepSeek/Qwen/Kimi/GLM/MiniMax/Mimo）均兼容 OpenAI function calling 格式，统一使用原生 `tools` 参数，不使用文本标记。

**文件：** `backend/app/services/brainstorm.py`

- [ ] 在模块顶部 import tool 相关：
  ```python
  from app.services import tool_defs as _  # noqa: F401 — register tools
  from app.core.tool_engine import TOOL_POOL, ToolContext, ROLE_BASE_TOOLS
  ```
- [ ] 初始化 `ToolContext`：`project_root` 从环境变量 `SLOTH_PROJECT_ROOT` 读取，fallback `Path.cwd()`
- [ ] 实现 `_get_effective_tools(role: str, extra_tools_json: str) -> list[str]`：
  ```python
  effective = set(ROLE_BASE_TOOLS.get(role, [])) | set(json.loads(extra_tools_json))
  return list(effective)
  ```
- [ ] 实现 `_build_tools_schema(tool_names: list[str]) -> list[dict]`，生成 OpenAI function calling 格式：
  ```python
  [{"type": "function", "function": {
      "name": td.name,
      "description": td.description,
      "parameters": td.params_schema
  }} for name in tool_names if (td := TOOL_POOL.get(name))]
  ```
- [ ] 发言时将 `tools=` 参数传入 LLM 调用（`LLMService.chat_stream` 透传 kwargs 到 API）
- [ ] 处理 LLM 响应中的 `tool_calls` 字段（需先拿完整响应再处理）：
  1. 解析 `tool_calls[0].function.name` 和 `.arguments`（JSON）
  2. 验证 `tool_name` 在 effective_tools 白名单中，否则返回权限拒绝内容
  3. 从 TOOL_POOL 取出 ToolDef，调用 `invoke(ctx, args_json)` 执行
  4. 捕获 `ToolSecurityError` → 错误提示字符串
  5. 捕获其他异常 → 错误提示字符串
  6. 发出 SSE 事件：`{"event": "tool_call", "data": {"tool": ..., "args": ..., "result": ..., "success": bool}}`
  7. 将 `{"role": "tool", "tool_call_id": ..., "content": result}` 追加到 messages 继续调用 LLM
- [ ] 最多允许每轮 3 次 tool-call，超过则截断返回已有内容
- [ ] 单元测试：
  - mock LLM 返回含 `tool_calls` → 验证循环触发
  - mock LLM 返回 5 次 `tool_calls` → 验证第 4 次被截断
  - `tool_name` 不在白名单 → `success=false` SSE 事件

---

## Task 7.4: 共享 Context Engine（首轮接入 Brainstorm，½ 天）

**文件:**
- `backend/app/core/context_engine.py`（新建，共享核心）
- `backend/app/services/context.py`（新建，服务层适配）
- `backend/app/services/brainstorm.py`（首轮集成）

- [ ] 在 `backend/app/core/context_engine.py` 实现共享 `ContextEngine`：
  - 暴露与业务模式无关的上下文处理接口
  - 首版提供 `build(...) -> {model_visible_context, runtime_only_context, diagnostics}`
  - 首版实现 `protect_reply_chains(messages, max_count)` 能力
  - 仅依赖消息结构与参数，不依赖 Brainstorm 状态机
- [ ] 在 `ContextEngine.build(...)` 首版实现标准流水线：
  1. 固定保留 system prompt 与最近轮次锚点
  2. 执行 reply 链祖先补齐
  3. 在预算内组装 model_visible_context
  4. 超预算时执行可解释降级（先压缩中段，后截断低优先级内容）
  5. 产出 diagnostics（规则命中、预算使用率、截断统计）
- [ ] 在 `backend/app/services/context.py` 提供轻量适配层：
  - 将业务消息结构映射为 `ContextEngine` 输入
  - 负责 mode 参数（chat/brainstorm/autonomous）透传与默认值
- [ ] 定义首版 diagnostics 字段（最小集合）：
  - `budget_in`, `budget_out`, `compression_ratio`, `truncation_count`, `build_latency_ms`
  - `token_estimation_fallback`（token 计数降级到字符预算时为 `true`）

- [ ] 实现 `ContextEngine.protect_reply_chains(messages: list[Message], max_count: int) -> list[Message]`：
  1. 取尾部 `max_count` 条消息（候选集）
  2. 对每条候选消息，沿 `parent_message_id` 链回溯，标记所有祖先（即使超出 max_count 窗口）
  3. 返回：候选集 ∪ 被标记祖先消息，按时间顺序排列
- [ ] 集成到 `BrainstormEngine`：每轮发言前，调用共享引擎（`mode="brainstorm"`）
- [ ] Chat 模式暂不切换，但增加接入预留点（后续切换到同一共享引擎）
- [ ] 单元测试：
  - `backend/tests/test_context_engine.py`：`ContextEngine` 纯逻辑测试（不依赖 Brainstorm）
  - `backend/tests/test_brainstorm_context_integration.py`：`mode="brainstorm"` 首轮接入集成测试
  - 100 条消息，`max_count=20` → 尾部 20 条存在
  - 尾部消息有超窗口的 `parent_message_id` 链 → 祖先被保留
  - 无引用链的消息超出窗口 → 被丢弃
  - 同一输入 + 同一 policy 连续执行两次 → `model_visible_context` 顺序与内容一致（确定性）
  - 模拟 token 计数异常 → 触发字符预算降级，`token_estimation_fallback=true`
  - 超预算场景 → diagnostics 中 `truncation_count > 0` 且保留 system/recent 锚点

---

## Task 7.5: 前端 — AgentDetail tools 展示 + ToolCallBlock（½ 天）

**文件:**
- `frontend/src/components/AgentDetail.tsx` — 修改，展示 tools chips
- `frontend/src/components/ToolCallBlock.tsx` — 新建
- `frontend/src/components/BrainstormStreamBubble.tsx` — 修改，集成 ToolCallBlock

**AgentDetail tools 展示：**
- [ ] 在 Agent 详情面板（system prompt 下方）新增 "工具能力" 区块
- [ ] 每个 tool 显示为 chip：`bg: #f0f4ff, color: #4f46e5, border-radius: 4px, padding: 2px 8px, 12px 字号`
- [ ] tool 名称用 code 风格显示（`font-family: monospace`）
- [ ] 无 tools 时不显示该区块

**ToolCallBlock 组件：**
- [ ] 订阅 `brainstormStore` 中的 `tool_call` SSE 事件，按 message_id 聚合
- [ ] 折叠状态：图标（📄 read / 🔍 grep / 📁 glob）+ 简短描述，如 "读取了 `frontend/src/App.tsx`"
- [ ] 展开状态：结果内容（前 20 行或前 800 字符，超出显示"...已截断"）
- [ ] 成功 → 边框 `#6366f1`；失败 → 边框 `#ef4444`，显示错误原因
- [ ] 样式：`bg: #f8f9fa, border-left: 3px solid, border-radius: 4px, padding: 8px 12px, 12px 字号`
- [ ] `BrainstormStreamBubble` 在消息气泡内，content 渲染前插入对应的 `ToolCallBlock`

---

## 验收标准

- [ ] `TOOL_POOL` 在 backend 启动后包含 6 个本地只读工具（无任何 CLI 依赖）
- [ ] Agent 发言时调用 `read` → SSE 出现 `tool_call` 事件 → 前端 ToolCallBlock 显示
- [ ] `read("../../etc/passwd")` → SSE `success=false`，错误原因显示
- [ ] Agent role=lead 调用 `glob` → SSE `success=false`（不在 lead tools 白名单）
- [ ] Agent role=lead 调用 `grep_repo` → SSE `success=false`（不在 lead tools 白名单）
- [ ] AgentDetail 展示该 Agent 的 tools chips，fortune 有 6 个，lead 有 2 个
- [ ] Context Engine 为共享模块（`backend/app/core/context_engine.py`），而非 Brainstorm 专属实现
- [ ] `backend/tests/test_context_engine.py` 与 `backend/tests/test_brainstorm_context_integration.py` 覆盖 Task 7.4 核心路径
- [ ] 100 条消息讨论，reply-to 链祖先在窗口外 → 仍被保留在上下文中
- [ ] `ContextEngine.build(...)` 返回 `model_visible_context/runtime_only_context/diagnostics` 三段结构
- [ ] 相同输入与 policy 下构建结果稳定（确定性）
- [ ] 超预算与降级行为可解释（diagnostics 含预算与截断信息）
- [ ] `uv run pytest backend/tests/ -v` 全部通过

---

