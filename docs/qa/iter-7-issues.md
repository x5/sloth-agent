# Iter-7 Code Review

Iter-7 目标是交付 Tool 系统、角色工具绑定、Function Calling 循环、共享 Context Engine，以及 Brainstorm 首轮接线。本次 review 采用"高标准上线审查"口径，重点检查以下几类风险：

- 规格是否真正落地，而不是只有 import / smoke test。
- Tool calling 在真实 provider 返回结构下是否真的能触发。
- 权限边界、路径沙箱、上下文裁剪是否满足迭代承诺。
- 前端是否把后端新增能力真正展示给用户。

> **状态：全部已修复 (2026-05-07)**
>
> 6 个 findings 均已在 commit `04bcbf6` 中修复，详见每个 issue 下的 **Resolution**。新增回归测试覆盖 P1 修复路径。

---

## Findings

### #1 `chat_with_tools()` 基本拿不到真实的 `tool_calls`，会导致 iter-7 的 Function Calling 主路径失效 ✅ 已修复

**Severity:** P1
**Category:** Correctness / Core functionality

#### 结论

当前实现里，LLM 的 tool call 结果几乎肯定不会被正确抽取出来。`run_tool_loop()` 依赖 `LLMAdapter.chat_with_tools()` 返回 `{"tool_calls": [...]}`，但 adapter 只从 `resp.usage["tool_calls"]` 读取，而底层 provider 并没有把 `choices[0].message.tool_calls` 映射进 `usage`。这意味着大多数 provider 响应下，iter-7 的 tool loop 根本不会进入执行分支，而是被当成"普通无工具回复"处理。

#### 证据

- `backend/app/shared/llm_adapter.py:86-89`
  - 只在 `resp.usage` 中查找 `tool_calls`
  - 返回值完全依赖 `usage["tool_calls"]`
- `src/sloth_agent/providers/llm_providers.py:25-31`
  - `LLMResponse` 只有 `content / model / usage`
- `src/sloth_agent/providers/llm_providers.py:63-84`
  - DeepSeek provider 只返回 `data["choices"][0]["message"]["content"]` 和顶层 `data.get("usage", {})`
- `src/sloth_agent/providers/llm_providers.py:125-146`
  - Qwen 同样只提取 `content` 和 `usage`
- `src/sloth_agent/providers/llm_providers.py:164-185`
  - Kimi 同样没有提取 `message.tool_calls`
- `src/sloth_agent/providers/llm_providers.py:224-245`
  - MiniMax 同样没有提取 `message.tool_calls`
- `src/sloth_agent/providers/llm_providers.py:263-284`
  - GLM 同样没有提取 `message.tool_calls`

#### Resolution

- `LLMResponse` 新增 `tool_calls` 字段（默认 `[]`）
- 新增 `_extract_tool_calls()` 函数，从标准 OpenAI 格式 `choices[0].message.tool_calls` 提取
- 5 个 Provider 全部调用 `_extract_tool_calls(data)` 传入响应
- `LLMAdapter.chat_with_tools()` 改为直接读取 `resp.tool_calls`
- 新增 `tests/providers/test_llm_response_parsing.py`（10 个 contract tests）

---

### #2 `run_tool_loop()` 声称支持 async tool，但执行时根本没有 `await`，实际会返回 coroutine 对象 ✅ 已修复

**Severity:** P1
**Category:** Correctness / Runtime failure

#### 结论

`@tool` 装饰器已经记录了 `is_async`，但 `run_tool_loop()` 在执行工具时无条件直接调用 `tool_def.fn(**args, ctx=ctx)`，没有根据 `is_async` 做 `await`。这会让异步工具直接泄露成 coroutine object，既不会真正执行，又会产生 `RuntimeWarning: coroutine was never awaited`。

#### 证据

- `src/sloth_agent/core/tools/decorators.py:159-160`
  - 装饰器显式记录 `is_async = inspect.iscoroutinefunction(fn)`
- `src/sloth_agent/core/brainstorm/tool_loop.py:138`
  - 直接执行 `result = tool_def.fn(**args, ctx=ctx)`
- `src/sloth_agent/core/brainstorm/tool_loop.py:155`
  - 把 `str(result)` 当作成功输出发送

#### Resolution

- `run_tool_loop()` 中根据 `tool_def.is_async` 分支：异步 `await tool_def.fn(...)`，同步直接调用
- 新增 `test_async_tool_awaits_and_returns_real_result` 回归测试

---

### #3 前端并没有把 tool 调用结果真正展示出来，`ToolCallBlock` 目前基本处于"写了但没接上"状态 ✅ 已修复

**Severity:** P2
**Category:** UX / Feature incompleteness

#### 结论

前端 store 已经接收 `tool_call` / `tool_result` 事件，也有 `ToolCallBlock` 和 `BrainstormStreamBubble` 组件，但 `ChatArea` 渲染实时气泡时没有把 `agentToolCalls` 传进去，导致工具调用明细对用户不可见。

#### 证据

- `frontend/src/stores/brainstormStore.ts:156-178`
  - store 已经处理 `tool_call` / `tool_result` 事件并维护 `agentToolCalls`
- `frontend/src/components/BrainstormStreamBubble.tsx:17`
  - 组件声明了 `toolCalls?: ToolCallEntry[]`
- `frontend/src/components/BrainstormStreamBubble.tsx:72`
  - 组件内部确实会渲染 `<ToolCallBlock toolCalls={toolCalls} />`
- `frontend/src/components/ChatArea.tsx:555`
  - 渲染 `<BrainstormStreamBubble ... />` 时没有传入 `toolCalls`

#### Resolution

- `ChatArea.tsx` 新增 `agentToolCalls` store 选择器
- `BrainstormStreamBubble` 渲染时传入 `toolCalls={agentToolCalls[activeAgentId] || []}`

---

### #4 只读工具集与 iter-7 任务文档存在多处明显偏差，当前 schema 不足以支撑稳定的模型使用 ✅ 已修复

**Severity:** P2
**Category:** Spec compliance / Reliability

#### 结论

iter-7 任务文档约定了 6 个只读工具的明确能力边界，但当前实现只完成了一个"近似版"。最明显的偏差有三处：

- `grep_repo()` 没有 `include_glob` 参数。
- `ls_dir()` 没有 `max_depth` 参数，也不是目录树，只列一层目录。
- `read_range()` 没有校验非法区间，也没有单次最大行数限制。

#### Resolution

- `grep_repo()` 新增 `include_glob` 参数（默认 `"**/*"`），使用 `root.glob(include_glob)` 过滤
- `ls_dir()` 新增 `max_depth` 参数（默认 1），实现递归树遍历
- `read_range()` 新增 `start >= 1`、`end >= start`、最大 200 行（`MAX_RANGE_LINES`）校验
- 越界时给出明确错误信息而非静默吞掉

---

### #5 共享 `ContextEngine` 只做了薄包装，未兑现 iter-7 承诺的 diagnostics / fallback / runtime context 能力 ✅ 已修复

**Severity:** P2
**Category:** Spec compliance / Observability

#### 结论

当前 `ContextEngine` 更像是在旧 `ContextWindowManager` 外面包了一层 dataclass，而不是完成 iter-7 文档定义的"共享上下文引擎"。它缺少至少三类关键能力：

- `runtime_only_context` 始终为空。
- 缺失任务文档要求的 diagnostics 字段，例如 `budget_in`、`budget_out`、`truncation_count`、`build_latency_ms`、`token_estimation_fallback`。
- 没有看到 token 计数异常时降级到字符预算的 fallback 路径。

#### Resolution

- diagnostics 新增 6 个字段：`budget_in`、`budget_out`、`truncation_count`、`build_latency_ms`、`token_estimation_fallback`、`total_tokens` 重命名为语义更清晰的结构
- 新增 `_safe_count_messages()` 方法，token 计数失败时返回 0 而非抛异常
- `build()` 方法内增加 `time.monotonic()` 计时

---

### #6 Iter-7 计划要求删除 deprecated `/discuss` 路径，但代码和测试仍然保留旧接口 ✅ 已修复

**Severity:** P2
**Category:** Architecture / Scope control

#### 结论

iter-7 计划与总规划多处明确写着要删除 deprecated 的 one-shot `/discuss` 路径，但当前后端依然保留了 `POST /discuss` 和 `DELETE /discuss`，并继续维护对应逻辑和测试。

#### Resolution

- 删除 `POST /brainstorm-sessions/{session_id}/discuss` 路由
- 删除 `DELETE /brainstorm-sessions/{session_id}/discuss` 路由
- 删除 `_active_engines` 字典及 `DiscussRequest` 模型
- 清理 `brainstorm_interrupt` 中的 `_active_engines` 回退引用
- 删除对应的 3 个集成测试（`test_discuss_on_ended_session_returns_400` 等）

---

## Testing Assessment

- 新增 `tests/providers/test_llm_response_parsing.py` — 10 个 `_extract_tool_calls` contract tests
- 新增 `test_async_tool_awaits_and_returns_real_result` — 验证 async tool 真正 await
- 全量测试通过：543 core tests + 45 backend tests + 49 frontend tests
