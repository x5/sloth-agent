# 上下文引擎

> 关联: cli/runtime/spec.md, core/memory/spec.md, core/session/spec.md, core/observability/spec.md, desktop/daemon/spec.md
> 最后更新: 2026-05-04
> 状态: 设计中（Iter-7 首轮接入）
> Scope: Core（Desktop 先接入，CLI 后续复用）

## 概述

Context Engine 是 Desktop Sidecar 的共享运行时模块，负责在预算约束内构建可发送给 LLM 的上下文。

它不归属于 Chat 或 Brainstorm 单一模式；各业务流通过同一引擎接入，只传入不同策略参数。

## 基类复用

`ContextEngine` 继承 `sloth_agent.core.context_window.ContextWindowManager`（CLI 已有实现），**不重建**以下已有能力：

| 已有能力 | 来源 |
|----------|------|
| token 计数（tiktoken + 字符回退） | `sloth_agent.core.token_counter.TokenCounter` |
| `build_messages(system, history, tool_results, user_msg)` — 预算截断 | `ContextWindowManager` |
| `_fit_history(history, budget)` — 历史消息裁剪 | `ContextWindowManager` |
| `_fit_tool_results(tool_results, budget)` — 工具结果压缩 | `ContextWindowManager` |
| `generate_summary(early_messages)` — 早期对话摘要 | `ContextWindowManager` |

Desktop 在继承基础上**扩展**：

| 扩展能力 | 说明 |
|----------|------|
| `protect_reply_chains(messages, max_count)` | 在 `_fit_history` 基础上补充 `parent_message_id` 祖先回溯，确保 reply chain 不被截断 |
| 三段输出结构 | `model_visible_context` / `runtime_only_context` / `diagnostics` |
| `mode` 策略参数 | `chat` / `brainstorm` / `autonomous` 通过 policy 切换，不同模式差异体现在 recent_turns 等参数 |
| `diagnostics` 可观测 | token 利用率、压缩率、截断率、构建耗时、命中策略 |
| 可解释降级错误码 | `ERR_BUDGET_EXCEEDED`、`ERR_TOKEN_COUNT_FALLBACK` 等 |

**path dependency 前提**：`backend/pyproject.toml` 需添加 `"sloth-agent @ file:///../"`。详见 `docs/specs/architecture/spec.md` — 共享核心层。



### 在本模块内

- 上下文构建主流水线（筛选、排序、保护、压缩、输出）
- 回复链保护（基于 `parent_message_id` 的祖先回溯）
- 预算控制（字符数/Token 双预算，含预留输出预算）
- 工具结果注入策略（内联、摘要、引用、截断、落盘引用）
- 关键消息保护策略（system、最近轮次、人工标记关键消息）
- 统一输出结构（ModelVisibleContext / RuntimeOnlyContext / diagnostics）
- 模式策略接口（chat/brainstorm/autonomous 通过 policy 参数切换）
- 可观测元数据产出（压缩率、截断次数、构建耗时、命中策略）

## 模块边界

#### 数据契约（实现级）

1. Message（输入）
    - `id: str`
    - `role: "system" | "user" | "assistant" | "tool"`
    - `content: str`
    - `created_at: str`
    - `parent_message_id: str | null`
    - `importance: "critical" | "normal" | "low"`（可选，默认 normal）

2. ToolResult（输入）
    - `tool_name: str`
    - `content: str`
    - `size_bytes: int`
    - `source_path: str | null`（落盘引用时填充）
    - `created_at: str`

3. Budget（输入）
    - `max_tokens: int`
    - `reserved_output_tokens: int`
    - `max_chars_fallback: int`
    - `max_tool_chars_per_item: int`
    - `max_tool_chars_total: int`

4. Policy（输入）
    - `mode: "chat" | "brainstorm" | "autonomous"`
    - `recent_turns: int`
    - `max_ancestor_hops: int`
    - `enable_summary: bool`
    - `deterministic: bool`

5. BuildResult（输出）
    - `model_visible_context: list[dict]`
    - `runtime_only_context: dict`
    - `diagnostics: dict`

#### 约束与优先级

优先级从高到低：
1. system prompt
2. 关键消息（importance=critical）
3. recent 窗口 + reply 祖先链
4. 工具结果摘要/引用
5. 低优先级历史消息

硬约束：
1. `model_visible_context` 必须按时间顺序稳定输出（同输入同 policy 保证确定性）。
2. 任意压缩与截断不得移除 system prompt。
3. 祖先链补齐在 `max_ancestor_hops` 内必须完整。
4. 工具结果正文注入受 `max_tool_chars_per_item` 与 `max_tool_chars_total` 双重约束。

#### 内部子能力（实现分层）

1. Selector
    - 输入原始消息与工具结果，按模式筛选候选集合。
2. ChainProtector
    - 对候选消息执行祖先链补齐，防止 reply 上下文断裂。
3. BudgetAllocator
    - 在 system、recent、tools、summary 之间分配预算。
4. Compressor
    - 对超预算中段执行摘要或压缩，保留关键锚点。
5. ToolResultReducer
    - 对大工具结果执行引用化与预览化，避免污染上下文窗口。
6. ContextAssembler
    - 组装最终输出：model_visible_context、runtime_only_context、diagnostics。

#### 流水线实现细节（逐步）

Step 0: 预处理与标准化
1. 规范化消息结构，补默认字段（importance=normal）。
2. 按 `(created_at, id)` 做稳定排序。
3. 去重（同 id 保留最后版本）。

Step 1: 锚点固定
1. 固定保留 system prompt。
2. 固定保留 critical 消息。
3. 根据 policy 取 recent 窗口（按轮次，而非按条数）。

Step 2: 祖先链补齐
1. 以 recent 窗口为候选集。
2. 对每条候选沿 `parent_message_id` 回溯，直到：
    - 命中 root，或
    - hop 达到 `max_ancestor_hops`，或
    - 找不到父消息。
3. 将补齐祖先加入保留集合（标记 `source="chain_protector"`）。

Step 3: 工具结果规约
1. 单条工具结果超过 `max_tool_chars_per_item`：
    - 先生成摘要；
    - 仍超限则写引用（`source_path` + preview）。
2. 工具结果聚合超过 `max_tool_chars_total`：
    - 保留最近结果与失败结果；
    - 其余结果转引用化。

Step 4: 预算分配与压缩
1. 计算输入 token；不可用时切换字符预算。
2. 可用预算 = `max_tokens - reserved_output_tokens`。
3. 按优先级保留内容；超限时执行：
    - 先压缩中段 normal 历史；
    - 再截断 low 历史；
    - 最后才压缩工具结果正文（不移除引用元信息）。

Step 5: 组装与诊断
1. 输出 `model_visible_context`（时间序 + 角色合法）。
2. 输出 `runtime_only_context`（映射、引用、内部标记）。
3. 输出 `diagnostics`：
    - `budget_in`, `budget_out`
    - `compression_ratio`, `truncation_count`
    - `build_latency_ms`
    - `applied_rules: list[str]`
    - `token_estimation_fallback: bool`
    - `error_code: str | null`

#### 模式策略默认值（首版）

1. chat
    - `recent_turns=12`, `enable_summary=true`, `max_ancestor_hops=8`
2. brainstorm
    - `recent_turns=20`, `enable_summary=true`, `max_ancestor_hops=20`
3. autonomous
    - `recent_turns=8`, `enable_summary=true`, `max_ancestor_hops=6`

#### 模块内错误与降级策略

- token 计数失败：降级为字符预算模式，并在 diagnostics 标记 `token_estimation_fallback=true`。
- 摘要失败：回退为截断策略，并保留关键锚点。
- 工具结果过大：优先引用化，禁止直接注入超限正文。
- 上下文构建异常：返回最小可用上下文（system + recent tail），并记录错误码。

错误码（首版）：
1. `CTX_TOKEN_ESTIMATE_FAILED`
2. `CTX_SUMMARY_FAILED`
3. `CTX_TOOL_RESULT_OVERSIZE`
4. `CTX_BUILD_FAILED`

### 不在本模块内

- LLM 调用与 provider 路由（由 LLM 模块负责）
- 会话生命周期状态机（由 Session/Brainstorm 负责）
- 具体工具执行（由 Tool Engine 负责）
- 持久化实现细节（由 Memory/Session 存储层负责）

## 核心职责

1. 在预算内构建发送给模型的消息列表
2. 保护关键链路消息，避免 reply 上下文断裂
3. 在上下文过长时触发中段压缩
4. 保持跨模式语义一致（chat/brainstorm/autonomous）
5. 输出可观测元数据，支持调试与审计

## 统一接口（建议）

```python
class ContextEngine:
    def build(
        self,
        *,
        mode: str,
        system_prompt: str,
        messages: list[dict],
        tool_results: list[dict],
        budget: dict,
        policy: dict,
    ) -> dict:
        """Return {
        model_visible_context: list[dict],
        runtime_only_context: dict,
        diagnostics: dict
        }"""

    def protect_reply_chains(
        self,
        messages: list[dict],
        max_count: int,
    ) -> list[dict]:
        """Preserve ancestors of in-window messages by parent_message_id."""
```

## 与其他模块的关系

### Memory

- 存储原始消息、摘要片段、工具结果引用
- 记录摘要版本与原始消息范围映射（可追溯）

### Session

- 提供 `session_id/run_id` 生命周期锚点
- 恢复时优先恢复 context snapshot 与摘要索引

### Observability

- 指标：`context_tokens_in`, `context_tokens_out`, `compression_ratio`, `truncation_count`, `build_latency_ms`
- 追踪：每轮上下文构建输出 `context_build` trace

### Daemon

- 后台运行时复用同一 Context Engine
- 断线恢复后使用同一策略重建上下文，避免语义漂移

## 分阶段接入

1. Iter-7: Brainstorm 首轮接入（reply 链保护 + 基础窗口）
2. Iter-8: Tool 结果引用与压缩策略接入
3. Iter-9: Autonomous 模式接入，形成多 Agent 上下文隔离
4. 后续: Chat 模式统一迁移到同一引擎

## 验收原则

- 同一输入在同一 policy 下输出稳定（确定性）
- 回复链祖先不丢失
- 超预算时行为可解释（有 diagnostics）
- 各模式共用一套核心实现，仅参数不同

## 与 Iter-7 Task 映射

对应任务文件：`docs/changes/iter7-tool-system/tasks.md`（Task 7.4）

### 规格项 -> 最小可测验收

1. 统一输出结构
    - 规格：`build(...)` 返回 `model_visible_context/runtime_only_context/diagnostics`
    - 验收：输出必须包含上述 3 个顶层字段

2. 回复链保护
    - 规格：`protect_reply_chains(messages, max_count)` 补齐祖先链
    - 验收：窗口外祖先消息在结果中被保留

3. 确定性
    - 规格：同输入同 policy 输出稳定
    - 验收：连续两次构建结果顺序与内容一致

4. 预算与降级
    - 规格：超预算优先压缩中段，再截断低优先级内容
    - 验收：超预算时 `truncation_count > 0` 且 system/recent 锚点仍保留

5. token 计数降级
    - 规格：token 计数失败时退化为字符预算
    - 验收：`token_estimation_fallback=true`

6. 共享模块边界
    - 规格：核心逻辑位于共享层，不依赖 Brainstorm 状态机
    - 验收：`backend/app/core/context_engine.py` 可在不引入 Brainstorm 依赖下单测通过

### 建议测试文件

- `backend/tests/test_context_engine.py`：纯逻辑测试
- `backend/tests/test_brainstorm_context_integration.py`：首轮接入验证（mode="brainstorm"）

## 开发 Checklist（Iter-7 可直接开工）

### 函数映射（建议）

1. `normalize_messages(messages) -> list[Message]`
    - 对应 Step 0（标准化、稳定排序、去重）
2. `select_anchors(system_prompt, messages, policy) -> list[Message]`
    - 对应 Step 1（system + critical + recent）
3. `protect_reply_chains(messages, max_count, max_hops) -> list[Message]`
    - 对应 Step 2（祖先补齐）
4. `reduce_tool_results(tool_results, budget, policy) -> list[dict]`
    - 对应 Step 3（工具结果摘要/引用化）
5. `allocate_and_compress(messages, tool_blocks, budget, policy) -> tuple[list[dict], dict]`
    - 对应 Step 4（预算分配与压缩）
6. `assemble_result(model_visible_context, runtime_meta, diagnostics) -> BuildResult`
    - 对应 Step 5（最终组装）
7. `build(mode, system_prompt, messages, tool_results, budget, policy) -> BuildResult`
    - 主入口，串联 Step 0-5

### 任务拆分（建议顺序）

1. 建立 `backend/app/core/context_engine.py` 文件与 `ContextEngine` 空实现
2. 先实现 `protect_reply_chains`（独立价值最高，且不依赖 token 逻辑）
3. 实现 Step 0 与 Step 1（稳定排序、锚点保留）
4. 实现 Step 3 工具结果规约（先做引用化，再做摘要）
5. 实现 Step 4 预算与压缩（先字符预算，后 token 预算）
6. 实现 Step 5 组装与 diagnostics
7. 在 `backend/app/services/context.py` 增加适配层
8. 在 `backend/app/services/brainstorm.py` 接入 `mode="brainstorm"`

### 单测清单（最小集）

1. `test_protect_reply_chains_keeps_ancestors`
2. `test_build_is_deterministic_with_same_input`
3. `test_budget_overflow_truncates_low_priority_first`
4. `test_token_estimation_fallback_sets_flag`
5. `test_tool_result_oversize_is_referenced_not_inlined`
6. `test_brainstorm_mode_integration_uses_shared_engine`

### 完成定义（DoD）

1. `build(...)` 返回三段结构：`model_visible_context/runtime_only_context/diagnostics`
2. 关键链路（reply 祖先）在窗口外仍可被保留
3. 超预算行为可解释（diagnostics 有明确命中规则与统计）
4. `backend/tests/test_context_engine.py` 与 `backend/tests/test_brainstorm_context_integration.py` 全通过
5. Brainstorm 首轮接入共享引擎，不引入 Brainstorm 状态机耦合到 `core/context_engine.py`
