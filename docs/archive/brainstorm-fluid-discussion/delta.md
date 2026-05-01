# Delta: Brainstorm 流畅讨论体验改进
> 关联模块: specs/brainstorm/spec.md, specs/chat/spec.md

## MODIFIED Requirements

### specs/brainstorm/spec.md

- **REQ-BRAINSTORM-ENGINE-LOOP**: 讨论引擎由"单轮顺序发言"改为"多轮循环讨论"（原: 每个 Agent 依次响应一次即结束；改: while 循环最多 8 轮，全员 PASS 时自然结束）

- **REQ-BRAINSTORM-ENGINE-PROMPT**: 系统提示由"说新东西、引用他人"改为包含明确互动指令（原: 要求 Add NEW insights，引用他人；改: 要求针对最新发言作出回应，可点名反驳、追问，无新内容时发送 PASS）

- **REQ-BRAINSTORM-HISTORY-NAMES**: `_load_history` 使用 JOIN 获取真实 agent name（原: `getattr(m, "agent_name", None)` 永远返回 None；改: `outerjoin(InspirationAgent)` 取真实姓名）

- **REQ-BRAINSTORM-AGENT-NUMBER**: `agent_start` 和 `message_done` SSE 事件携带 `agent_number` 字段（原: 无此字段；改: 后端计算 `agent_indices` map 并注入两个事件）

- **REQ-BRAINSTORM-STORE-AGENT-NUM**: 前端 store 新增 `activeAgentNumber: number | null` 状态，在 `agent_start` / `agent_pass` / `discussion_end` / `stopBrainstorm` / `stopDiscussion` 时同步清空（原: 无此字段）

## ADDED Requirements

### specs/brainstorm/spec.md

- **REQ-BRAINSTORM-PASS**: Agent 可通过发送文本 "PASS" 明确跳过本轮发言；后端检测并发送 `agent_pass` SSE 事件，不持久化消息；当一轮内所有 Agent 均 PASS 时讨论自然结束

- **REQ-BRAINSTORM-SSE-AGENT-PASS**: 新增 SSE 事件 `agent_pass`，载荷包含 `agent_id`, `agent_name`, `agent_number`；前端收到后清除流式气泡

### specs/chat/spec.md

- **REQ-CHAT-STREAM-AUTOSCROLL**: 流式 token 到达时（`streamingContent` 或 `chatStreamText` 变化），若用户距底部 300px 内则自动滚动到底

- **REQ-CHAT-QUEUE-AWAIT**: 消息队列 `processQueue` 的递归调用和 `handleSend` 末尾调用均使用 `await`，确保错误向上传播、队列串行执行

## REMOVED Requirements

### specs/chat/spec.md

- **REQ-CHAT-QUEUE-MERGE**: ~~系统响应完成后，队列中所有消息合并为一条批量发送~~（已在上一次 review 中修复为逐条发送，此条款已过时）
