# 变更提案: Brainstorm 流畅讨论体验改进
> 日期: 2026-05-02
> 影响模块: specs/brainstorm/spec.md, specs/chat/spec.md

## 动机

当前 Brainstorm 模式体验不丝滑，核心原因：

1. **单轮架构**：`BrainstormEngine.run()` 只做一轮 `for agent in agents`，每个 Agent 各说一次即结束，无法产生真正的来回辩论。
2. **Prompt 无互动指令**：只要求 Agent "说新东西"，不要求回应他人、反驳、追问，导致每个 Agent 各自发表独立观点而非讨论。
3. **`_load_history` 取不到 agent name**：`getattr(m, "agent_name", None)` 永远返回 None（`Message` 模型无此列），LLM 上下文里所有 Agent 都叫 "Agent"，无法区分谁说了什么，讨论质量严重下降。
4. **`message_done` 未传 `agent_number`**：已提交消息头像全显示 "?"、无颜色，无法区分不同 Agent。
5. **流式内容不自动滚动**：scroll useEffect 只监听 `messages`，token 涌入时视图不跟随。
6. **`processQueue` 未 await**：递归调用无 await，错误被静默吞掉，偶发丢消息。

## 范围

### 改什么

- `BrainstormEngine.run()` 重写为多轮循环（最多 8 轮），全员 PASS 时自然结束
- `SPEECH_PROMPT_TEMPLATE` 更新为明确的互动指令（回应他人、反驳、追问、PASS）
- `_load_history` 改用 JOIN 取真实 agent name
- 后端 `agent_start` / `message_done` 事件携带 `agent_number`
- 前端 store 新增 `activeAgentNumber` 状态；处理 `agent_pass` 事件
- 前端 `ChatArea` 流式内容自动滚动；`processQueue` 加 await

### 不改什么

- SSE 协议格式（事件名称保持兼容，新增 `agent_pass` 事件）
- 数据库模型
- Brainstorm 会话创建/管理 API
- 沙箱隔离
- Chat 模式流式逻辑（已正常工作）
