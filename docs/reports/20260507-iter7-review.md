# Iter-7 再次 Code Review

日期：2026-05-07  
范围：基于 `04bcbf6` 之后的当前 `master` 代码状态进行复审  
标准：按上线前高标准审查口径，覆盖架构、模块边界、接口契约、代码简洁度、逻辑严谨性、安全、性能、测试与用户体验

---

## 结论

上一轮 review 的 6 个问题，大部分已经被真正修掉，不是只修了表面：

- `tool_calls` 提取已经接到 provider 解析层。
- async tool 已经真正 `await` 执行。
- 前端实时气泡已经能展示 `tool_call/tool_result`。
- `/discuss` 路由已经移除。
- ContextEngine diagnostics 的关键字段已经补齐。

本次复审后，我的判断是：

**当前代码已明显优于上一版，但仍未达到“高置信通过”标准。**

原因不是旧问题回归，而是还存在 2 个更底层的结构性缺口：

1. Function calling 的多轮消息协议仍然不完整，真实 provider 下存在继续失效的风险。
2. 只读工具契约仍未完全收敛到 Iter-7 文档，模型调用稳定性与后续维护会继续受影响。

---

## Findings

### 1. P1: Function calling 的多轮协议仍不完整，下一轮 LLM 调用缺少标准 tool message 上下文

**严重级别：P1**  
**类别：架构 / Correctness / Provider compatibility**

#### 结论

虽然这次已经把 `tool_calls` 从 provider 响应里正确提取出来了，但 `run_tool_loop()` 到 `LLMAdapter` 的整条链路，仍然没有保存和回传 function calling 所需的完整消息结构。现在只保留了 `role` 和 `content`，并且在工具执行后只追加了 `role="tool"` 消息，没有把上一轮 assistant 的 `tool_calls` 作为结构化消息回灌给下一轮模型。

这会导致一个现实问题：

**当前实现更像是“本地调度器知道调用过工具”，但下一轮 provider 未必知道。**

对宽松 provider 或 mock 测试，这条链路可能仍然看起来能工作；但对更严格的 OpenAI-compatible 接口，缺少 `assistant.tool_calls` 和 `tool_call_id` 的完整消息语义，下一轮继续推理时存在协议不一致风险。

#### 证据

- `backend/app/services/brainstorm.py:376` 通过 `adapter.chat_with_tools(...)` 继续发起下一轮调用。
- `backend/app/services/brainstorm.py:379` 传入的是 `context_result.model_visible_context`，后续由 tool loop 直接在这份消息列表上追加内容。
- `src/sloth_agent/core/brainstorm/tool_loop.py:113-163` 只向 `messages` 追加 `role="tool"` 消息，包含 `tool_call_id`，但没有把上一轮 assistant 的 `tool_calls` 响应以标准消息形式保存下来。
- `backend/app/shared/llm_adapter.py:34-35` `_to_llm_messages()` 会把任意消息压缩成 `LLMMessage(role, content)`。
- `src/sloth_agent/providers/llm_providers.py:14-22` `LLMMessage` 结构和 `to_dict()` 也只支持 `role` 与 `content`，无法承载 `tool_call_id`、`tool_calls`、`name` 等 function calling 元数据。

#### 为什么这是高优先级问题

- 这不是 UI 或文档问题，而是 **核心协议层仍然未闭环**。
- 目前的 provider unit test 只验证了“能否抽取 `tool_calls`”，没有验证“第二轮请求是否仍然是 provider 可接受的标准 tool conversation”。
- 一旦切到严格校验消息结构的 provider，这类问题会表现为：第一轮能发起 tool call，第二轮却报格式错误、忽略 tool 结果，或行为 silently degrade。

#### 建议修复

1. 把消息模型从 `role/content` 升级为真正的结构化 message object，至少支持 `tool_call_id`、`tool_calls`、`name`、扩展字段透传。
2. 在 `run_tool_loop()` 中，在工具执行前把 assistant 的 `tool_calls` 响应写回消息历史，再追加对应 `tool` 消息。
3. 增加 provider contract test，覆盖“首轮返回 tool_calls -> 执行工具 -> 第二轮请求消息结构合法”这条完整链路，而不是只测抽取。

---

### 2. P2: 只读工具实现仍未完全对齐 Iter-7 契约，工具 schema 与任务文档继续漂移

**严重级别：P2**  
**类别：Spec compliance / Reliability / Maintainability**

#### 结论

上轮指出的只读工具问题，这次修掉了一部分，但没有完全收敛到 Iter-7 任务文档。当前实现和文档仍有多处明确偏差：

- `read_range` 仍使用 `start/end`，不是文档约定的 `start_line/end_line`。
- `read_range` 超过上限时直接报错，文档要求的是最多 400 行并自动截断。
- `read_range` 当前上限是 200 行，不是文档中的 400 行。
- `ls_dir` 默认 `max_depth=1`，而文档要求默认 `2`。
- `ls_dir` 最多返回 100 条，而文档要求最多 300 条。
- `grep_repo` 虽然已有 `include_glob`，但没有看到文档要求的“大文件/常见二进制跳过”策略。

这说明当前工具系统仍处于“代码与 spec 同时存在，但不是同一个 contract”的状态。

#### 证据

Iter-7 任务文档：

- `docs/changes/iter7-tool-system/tasks.md:104-114` 明确要求 `read_range(path, start_line, end_line)`，且单次最多 400 行、超出自动截断。
- `docs/changes/iter7-tool-system/tasks.md:132-141` 明确要求 `ls_dir(path=".", max_depth=2)`，`max_depth` 范围 0-4，最多 300 个条目。
- `docs/changes/iter7-tool-system/tasks.md:118-126` 要求 `grep_repo(..., include_glob="**/*")` 并按候选文件过滤。

当前实现：

- `src/sloth_agent/core/tools/builtin/readonly_fs.py:23` `MAX_RANGE_LINES = 200`
- `src/sloth_agent/core/tools/builtin/readonly_fs.py:63` `def read_range(path: str, start: int, end: int, ...)`
- `src/sloth_agent/core/tools/builtin/readonly_fs.py:74-75` 超过上限直接返回 error，而不是自动截断。
- `src/sloth_agent/core/tools/builtin/readonly_fs.py:22` `MAX_LS_RESULTS = 100`
- `src/sloth_agent/core/tools/builtin/readonly_fs.py:197` `ls_dir(..., max_depth: int = 1)`
- `src/sloth_agent/core/tools/builtin/readonly_fs.py:130` `grep_repo(..., include_glob="**/*")` 已补上，但函数内仍缺少大文件/常见二进制显式过滤。

#### 为什么这仍然重要

- 工具 schema 就是模型的 API 契约。参数名和行为不稳定，会直接降低模型调用命中率和自纠能力。
- 当前测试更像是在验证“实现现在怎么工作”，不是在验证“实现是否兑现了 Iter-7 规格”。
- 后续如果前端、prompt、文档、测试分别基于不同版本的 contract 演化，这个模块会越来越难维护。

#### 建议修复

1. 直接以 Iter-7 文档为准，把工具签名、默认值、返回上限统一到同一份 contract。
2. `read_range` 改回 `start_line/end_line`，并把超长行为改为自动截断而不是直接报错。
3. `ls_dir` 对齐默认深度、最大条目数和参数边界。
4. `grep_repo` 增加大文件与常见二进制跳过规则。
5. 增加 contract-level tests，测试名和断言直接对应文档，而不是仅对应当前实现。

---

## 已确认修复的部分

以下改动本次复审确认已经有效落地：

- `backend/app/shared/llm_adapter.py` 已不再从 `usage` 猜测 `tool_calls`，而是直接读取 provider 解析结果。
- `src/sloth_agent/core/brainstorm/tool_loop.py` 已对 async tool 做分支 `await`。
- `frontend/src/components/ChatArea.tsx:563` 已把 `toolCalls={agentToolCalls[activeAgentId] || []}` 传给实时流式气泡。
- `frontend/src/stores/brainstormStore.ts:156-186` 已处理 `tool_call` / `tool_result` 事件并回填展示状态。
- `backend/app/routers/brainstorm.py` 已移除旧 `/discuss` 路由，仅保留 persistent connect/inject/connect-delete 模型。

---

## 测试情况

本次复审执行了最相关的目标测试：

```text
.\.venv\Scripts\python.exe -m pytest tests\providers\test_llm_response_parsing.py tests\core\brainstorm\test_tool_loop.py -q
19 passed in 0.17s
```

已确认的新增回归点：

- `tests/providers/test_llm_response_parsing.py:23` 覆盖标准 `tool_calls` 提取。
- `tests/core/brainstorm/test_tool_loop.py:225` 覆盖 async tool await 执行。

但仍缺少两类关键测试：

1. provider contract test：验证第二轮 tool conversation 的消息结构是否合法。
2. readonly tools contract test：直接对照 Iter-7 文档中的参数名、默认值、截断语义做断言。

---

## 总体判断

如果按“是否比上一轮明显进步”来评估，这次修复是成立的。  
如果按“是否已经达到高标准通过”来评估，我的结论仍然是：**还不能给通过。**

更准确地说：

**当前版本已经从“关键问题较多的可集成状态”，提升到了“主修复已完成，但协议层和工具契约仍需再收口的候选验收状态”。**

---

## 优先级建议

建议下一步按下面顺序处理：

1. 先修 function calling 的结构化消息协议，再补 provider 二轮 contract test。
2. 再统一 readonly tools 的 schema / 默认值 / 截断语义，并补 spec-based tests。
3. 做完这两项后，再进行下一轮高标准复审；那时通过概率会高很多。