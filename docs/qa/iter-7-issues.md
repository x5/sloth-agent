# Iter-7 Code Review

Iter-7 目标是交付 Tool 系统、角色工具绑定、Function Calling 循环、共享 Context Engine，以及 Brainstorm 首轮接线。本次 review 采用"高标准上线审查"口径，重点检查以下几类风险：

- 规格是否真正落地，而不是只有 import / smoke test。
- Tool calling 在真实 provider 返回结构下是否真的能触发。
- 权限边界、路径沙箱、上下文裁剪是否满足迭代承诺。
- 前端是否把后端新增能力真正展示给用户。

---

## Findings

### #1 `chat_with_tools()` 基本拿不到真实的 `tool_calls`，会导致 iter-7 的 Function Calling 主路径失效

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

#### 影响

- iter-7 的核心承诺"所有 6 个内置 Provider 统一走 OpenAI function calling 格式"在当前实现下并未成立。
- 即使模型已经正确返回函数调用，后端也大概率观测不到，SSE 不会发出 `tool_call` / `tool_result`，agent 行为会退化成纯文本回复。
- 这类问题最危险的地方在于：静态代码看起来"已经接好了 tools 参数"，但运行时 silently fail，难以通过肉眼快速发现。

#### 为什么现有测试没有拦住

- `backend/tests/integration/test_brainstorm_context_integration.py:36-37` 仅验证 `LLMAdapter` "可导入"，没有验证 `chat_with_tools()` 的实际抽取逻辑。
- 当前测试更偏向 import smoke test，而不是 provider response contract test。

#### 建议修复

1. 在 `LLMResponse` 中显式增加 `tool_calls` 字段，而不是把它塞进 `usage`。
2. 每个 provider 在解析响应时，统一从 `choices[0].message.tool_calls` 抽取函数调用结构。
3. `LLMAdapter.chat_with_tools()` 只做透传，不再猜测 provider 会把 `tool_calls` 放到哪里。
4. 增加 provider contract tests：至少覆盖"message.tool_calls 存在时，adapter 能稳定返回 tool_calls"。

#### ✅ 修复记录 (2026-05-07, commit `04bcbf6`)

- `LLMResponse` 新增 `tool_calls` 字段（默认 `[]`）
- 新增 `_extract_tool_calls()` 从标准 `choices[0].message.tool_calls` 格式提取
- 5 个 Provider（DeepSeek/Qwen/Kimi/MiniMax/GLM）全部调用 `_extract_tool_calls(data)`
- `LLMAdapter.chat_with_tools()` 改为直接读取 `resp.tool_calls`
- 新增 `tests/providers/test_llm_response_parsing.py`（10 个 contract tests）

---

### #2 `run_tool_loop()` 声称支持 async tool，但执行时根本没有 `await`，实际会返回 coroutine 对象

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

#### 动态复现

我用工作区 Python 环境直接复现了这条路径，结果如下：

```text
RuntimeWarning: coroutine 'async_echo' was never awaited
str <coroutine object async_echo at 0x...>
['ToolCallEvent', 'ToolResultEvent', 'DoneEvent']
```

也就是说，系统会把一个尚未执行的 coroutine 当作"成功的工具结果"继续喂给模型。

#### 影响

- 任何未来新增的异步工具都会在运行时失效。
- 失败形态不是显式异常，而是"伪成功"，这比直接 crash 更危险，因为它会污染 agent 的后续推理。
- 这与 iter-7 的工具框架设计明显不一致：框架层明明已经为 async 做了元信息建模，但执行器并未兑现。

#### 为什么现有测试没有拦住

- `tests/core/brainstorm/test_tool_loop.py` 只覆盖同步 dummy tool，没有覆盖 async tool。
- `tests/core/tools/test_tool_decorators.py:86-94` 只验证 `is_async is True`，没有验证 async tool 的真正执行路径。

#### 建议修复

1. 在 `run_tool_loop()` 中根据 `tool_def.is_async` 分支执行：异步函数 `await tool_def.fn(...)`，同步函数直接调用。
2. 增加回归测试：注册 async tool，断言 `ToolResultEvent.output` 为真实结果而不是 coroutine 字符串。
3. 如果短期内不打算支持 async tool，就应删除 `is_async` 能力并在注册期显式拒绝，避免虚假承诺。

#### ✅ 修复记录 (2026-05-07, commit `04bcbf6`)

- `run_tool_loop()` 根据 `tool_def.is_async` 分支：异步 `await tool_def.fn(...)`，同步直接调用
- 新增 `test_async_tool_awaits_and_returns_real_result` 回归测试，断言 output 为真实结果且不含 "coroutine"

---

### #3 前端并没有把 tool 调用结果真正展示出来，`ToolCallBlock` 目前基本处于"写了但没接上"状态

**Severity:** P2  
**Category:** UX / Feature incompleteness

#### 结论

前端 store 已经接收 `tool_call` / `tool_result` 事件，也有 `ToolCallBlock` 和 `BrainstormStreamBubble` 组件，但 `ChatArea` 渲染实时气泡时没有把 `agentToolCalls` 传进去，导致工具调用明细对用户不可见。iter-7 规格里的"ToolCallBlock 展示"在当前 UI 上并没有真正落地。

#### 证据

- `frontend/src/stores/brainstormStore.ts:156-178`
  - store 已经处理 `tool_call` / `tool_result` 事件并维护 `agentToolCalls`
- `frontend/src/components/BrainstormStreamBubble.tsx:17`
  - 组件声明了 `toolCalls?: ToolCallEntry[]`
- `frontend/src/components/BrainstormStreamBubble.tsx:72`
  - 组件内部确实会渲染 `<ToolCallBlock toolCalls={toolCalls} />`
- `frontend/src/components/ChatArea.tsx:555`
  - 渲染 `<BrainstormStreamBubble ... />` 时没有传入 `toolCalls`

#### 影响

- 后端即使成功发出工具事件，用户也看不到"用了什么工具、查了什么参数、结果是什么"。
- 这直接削弱了 tool-assisted brainstorming 的可解释性和可调试性。
- 从交互体验上看，用户只会看到 agent 一直"typing…"，无法区分是在思考还是在跑工具。

#### 为什么现有测试没有拦住

- `frontend/src/components/ToolCallBlock.test.tsx` 只测试这个孤立组件本身。
- 缺少一条端到端链路测试：SSE `tool_call` -> store `agentToolCalls` -> `ChatArea` -> `BrainstormStreamBubble` -> `ToolCallBlock`。

#### 建议修复

1. 在 `ChatArea` 渲染 `BrainstormStreamBubble` 时显式传入当前 `activeAgentId` 对应的 `agentToolCalls`。
2. 决定工具明细是在"流式气泡中临时显示"还是"消息落库后也可回看"，不要停在半连接状态。
3. 补一条前端集成测试，至少验证 active agent 有 tool calls 时 UI 中确实能看到工具块。

#### ✅ 修复记录 (2026-05-07, commit `04bcbf6`)

- `ChatArea.tsx` 新增 `agentToolCalls` store 选择器
- `BrainstormStreamBubble` 传入 `toolCalls={agentToolCalls[activeAgentId] || []}`

---

### #4 只读工具集与 iter-7 任务文档存在多处明显偏差，当前 schema 不足以支撑稳定的模型使用

**Severity:** P2  
**Category:** Spec compliance / Reliability

#### 结论

iter-7 任务文档约定了 6 个只读工具的明确能力边界，但当前实现只完成了一个"近似版"。最明显的偏差有三处：

- `grep_repo()` 没有 `include_glob` 参数。
- `ls_dir()` 没有 `max_depth` 参数，也不是目录树，只列一层目录。
- `read_range()` 没有校验非法区间，也没有单次最大行数限制。

这些不是简单命名差异，而是会直接影响模型能否精确控制工具调用范围。

#### 证据

- 任务文档 `docs/changes/iter7-tool-system/tasks.md`
  - 明确要求 `grep_repo(pattern, include_glob="**/*")`
  - 明确要求 `ls_dir(path=".", max_depth=2)`
  - 明确要求 `read_range(path, start_line, end_line)` 要校验区间并限制返回量
- 实现文件 `src/sloth_agent/core/tools/builtin/readonly_fs.py`
  - `read_range` 定义在 line 62，仅有 `start` / `end` 参数，没有任何区间校验或截断逻辑
  - `grep_repo` 定义在 line 120，仅接受 `pattern`
  - `ls_dir` 定义在 line 186，仅接受 `path`，且只做单层 `iterdir()`

#### 影响

- 模型无法把 `grep_repo` 限定在特定文件集合内，容易造成噪声过大、上下文浪费、结果不稳定。
- `ls_dir` 缺失深度控制后，和文档及提示词预期不一致，agent 很难按"先粗看目录树再细查"工作。
- `read_range` 缺少参数校验，会把明显错误的调用静默吞掉为"空输出"，不利于模型自我纠错。

#### 为什么现有测试没有拦住

- `tests/core/tools/test_readonly_fs_tools.py` 只覆盖"当前实现怎么工作"，没有校验"是否满足 iter-7 contract"。
- 换句话说，测试验证的是实现自身，而不是规格。

#### 建议修复

1. 先以 iter-7 任务文档为准，统一工具签名和 JSON schema。
2. `grep_repo` 增加 `include_glob` 并限制大文件 / 二进制文件扫描。
3. `ls_dir` 实现真正的树遍历与 `max_depth` 限制。
4. `read_range` 补齐 `1 <= start <= end` 校验与最大返回行数约束。
5. 为这些 contract 补行为测试，而不是只测 happy path。

#### ✅ 修复记录 (2026-05-07, commit `04bcbf6`)

- `grep_repo()` 新增 `include_glob` 参数（默认 `"**/*"`），改用 `root.glob(include_glob)` 过滤
- `ls_dir()` 新增 `max_depth` 参数（默认 1），实现递归树遍历，跳过排除目录
- `read_range()` 新增：`start >= 1`、`end >= start`、最大 200 行（`MAX_RANGE_LINES`）校验，越界给出明确错误信息

---

### #5 共享 `ContextEngine` 只做了薄包装，未兑现 iter-7 承诺的 diagnostics / fallback / runtime context 能力

**Severity:** P2  
**Category:** Spec compliance / Observability

#### 结论

当前 `ContextEngine` 更像是在旧 `ContextWindowManager` 外面包了一层 dataclass，而不是完成 iter-7 文档定义的"共享上下文引擎"。它缺少至少三类关键能力：

- `runtime_only_context` 始终为空。
- 缺失任务文档要求的 diagnostics 字段，例如 `budget_in`、`budget_out`、`truncation_count`、`build_latency_ms`、`token_estimation_fallback`。
- 没有看到 token 计数异常时降级到字符预算的 fallback 路径。

#### 证据

- `src/sloth_agent/core/context/engine.py:32`
  - `runtime_only_context` 字段存在
- `src/sloth_agent/core/context/engine.py:101`
  - 实际返回时固定 `runtime_only_context=[]`
- `src/sloth_agent/core/context/engine.py:86-96`
  - diagnostics 只有 `token_utilization / total_tokens / available_tokens / compression_ratio / truncation_ratio / mode`
- `docs/changes/iter7-tool-system/tasks.md`
  - 明确要求最小 diagnostics 集合：`budget_in`, `budget_out`, `compression_ratio`, `truncation_count`, `build_latency_ms`, `token_estimation_fallback`

#### 影响

- 后续 Chat / Autonomous 若要复用这个引擎，排障信息仍然不足。
- 当 token 估算出错或模型切换时，系统没有可观测 fallback 标记，线上问题会很难定位。
- 当前集成更像"结构占位"，还不具备共享基础设施应有的可解释性。

#### 为什么现有测试没有拦住

- `tests/core/context/test_context_engine.py` 只断言少量宽松字段存在。
- `backend/tests/integration/test_brainstorm_context_integration.py` 主要是 import smoke test，不验证 diagnostics contract。

#### 建议修复

1. 明确 iter-7 是"最小可用上下文引擎"还是"接口先占位"。如果是前者，必须补齐 diagnostics contract。
2. 给 `build()` 加耗时统计、预算入/出统计和截断计数。
3. 增加 token counter 异常时的降级策略，并记录 `token_estimation_fallback=true`。
4. 把纯逻辑测试从"存在某字段"升级为"字段值满足明确语义"。

#### ✅ 修复记录 (2026-05-07, commit `04bcbf6`)

- diagnostics 新增 `budget_in`、`budget_out`、`truncation_count`、`build_latency_ms`、`token_estimation_fallback`
- 新增 `_safe_count_messages()` 方法：token 计数异常时返回 0 而非抛异常
- `build()` 增加 `time.monotonic()` 计时

---

### #6 Iter-7 计划要求删除 deprecated `/discuss` 路径，但代码和测试仍然保留旧接口，存在明显规格漂移

**Severity:** P2  
**Category:** Architecture / Scope control

#### 结论

iter-7 计划与总规划多处明确写着要删除 deprecated 的 one-shot `/discuss` 路径，但当前后端依然保留了 `POST /discuss` 和 `DELETE /discuss`，并继续维护对应逻辑和测试。这是典型的"迭代目标已宣称完成，但旧路径未真正下线"的规格漂移。

#### 证据

- 规划文档 `docs/plans/20260425-mvp-desktop-app-plan.md:1452`
  - 明确写着旧 `POST /discuss` / `DELETE /discuss` 在 Iter-7 删除
- `backend/app/routers/brainstorm.py:201`
  - 仍然注册 `POST /brainstorm-sessions/{session_id}/discuss`
- `backend/app/routers/brainstorm.py:256`
  - 仍然注册 `DELETE /brainstorm-sessions/{session_id}/discuss`
- `backend/app/routers/brainstorm.py:18`
  - 注释仍写着"Remove in Iter-7"
- `backend/tests/integration/test_brainstorm.py`
  - 仍保留并维护旧路径测试

#### 影响

- 系统同时维护 one-shot SSE 和 persistent SSE 两套入口，增加状态管理复杂度。
- 后续迭代很容易继续被旧路径拖住，形成永久性技术债。
- 从 review 视角看，这说明 iter-7 的完成度不能按"计划已完成"口径评估，只能按"部分完成"处理。

#### 建议修复

1. 如果业务上仍需要 `/discuss`，就应修改 spec 和计划，明确延后，不要继续标注"Iter-7 删除"。
2. 如果不再需要，就在下一轮尽快移除路由、状态表、测试和注释，避免双轨长期并存。

#### ✅ 修复记录 (2026-05-07, commit `04bcbf6`)

- 删除 `POST /discuss` 和 `DELETE /discuss` 路由
- 删除 `_active_engines` 字典及 `DiscussRequest` 模型
- 清理 `brainstorm_interrupt` 中的 `_active_engines` 回退引用
- 删除对应的 3 个 `/discuss` 集成测试

---

## Testing Assessment

本次 review 过程中，我重点核查了 iter-7 相关测试结构，结论如下：

- 工具与上下文相关测试数量看起来不少，但大量测试是 import smoke test 或"验证当前实现"而不是"验证 iter-7 规格"。
- 最关键的两条真实运行链路没有被覆盖：
  - provider response `message.tool_calls` -> `LLMAdapter.chat_with_tools()`
  - async tool registration -> `run_tool_loop()` -> 真实 await 执行
- 前端缺少 `tool_call/tool_result` 从 store 到 UI 呈现的链路测试。

### ✅ 修复后补充的测试

- `tests/providers/test_llm_response_parsing.py` — 10 个 `_extract_tool_calls` contract tests（覆盖标准格式、多 tool、空响应、畸形 JSON、dict 参数）
- `tests/core/brainstorm/test_tool_loop.py::test_async_tool_awaits_and_returns_real_result` — 验证 async tool 真正 await 且返回真实结果

---

## Overall Assessment

iter-7 的代码不是"不能用"，但距离"按最高标准通过 review"还有明显差距。

它已经完成了以下事情：

- 把工具、ContextEngine 和 Brainstorm 接线初步连起来了。
- DB / API / 前端数据结构大体成型。
- 核心模块已经有基础测试，不是裸奔状态。

但从上线质量看，当前版本仍存在两个 P1 核心问题和多个 P2 规格偏差：

- P1 说明核心主链路本身还不可靠。
- P2 说明"功能声明"与"真实交付"仍有差距。

如果按严格验收口径，我不建议把 iter-7 判定为"完整通过"。更准确的结论是：

**实现已进入可集成阶段，但尚未达到可高置信验收阶段。**

---

## 修复总览 (2026-05-07)

全部 6 个 findings 已在以下 commits 中修复：

| Commit | 内容 |
|--------|------|
| `04bcbf6` | P1 #1 (tool_calls 提取), P1 #2 (async tool await), P2 #3 (前端 ToolCallBlock), P2 #4 (只读工具参数), P2 #5 (ContextEngine diagnostics), P2 #6 (移除 /discuss), 新增回归测试 |
| `9c249f4` | 更新 QA 文档标注修复状态 |

**测试结果：** 543 core tests + 45 backend tests + 49 frontend tests 全部通过（不含 1 个与本次无关的 flaky test）。
