# 实现任务

## 后端

- [x] `backend/app/services/brainstorm.py` — `_load_history` 改用 `outerjoin(InspirationAgent)` 取真实 agent name
- [x] `backend/app/services/brainstorm.py` — 计算 `agent_indices` map
- [x] `backend/app/services/brainstorm.py` — `agent_start` 事件携带 `agent_number`
- [x] `backend/app/services/brainstorm.py` — `message_done` 事件携带 `agent_number`
- [x] `backend/app/services/brainstorm.py` — `SPEECH_PROMPT_TEMPLATE` 改为互动式指令（回应他人、反驳、追问、PASS）
- [x] `backend/app/services/brainstorm.py` — `run()` 重写为 `while sub_round < MAX_ROUNDS` 多轮循环
- [x] `backend/app/services/brainstorm.py` — PASS 检测：`full_content.strip().upper() == "PASS"` 时发送 `agent_pass` 事件，不入库
- [x] `backend/app/services/brainstorm.py` — 全员 PASS（`speeches_this_round == 0`）时自然结束循环

## 前端 Store

- [x] `frontend/src/stores/brainstormStore.ts` — `BrainstormState` 新增 `activeAgentNumber: number | null`
- [x] `frontend/src/stores/brainstormStore.ts` — `agent_start` 处理：写入 `activeAgentNumber`
- [x] `frontend/src/stores/brainstormStore.ts` — `message_done` 处理：从事件读取 `agent_number`，写入 `Message.agent_number`；清空 `activeAgentNumber`
- [x] `frontend/src/stores/brainstormStore.ts` — 新增 `agent_pass` 事件处理：清除流式气泡
- [x] `frontend/src/stores/brainstormStore.ts` — `discussion_end` / `stopBrainstorm` / `stopDiscussion`：清空 `activeAgentNumber`

## 前端 ChatArea

- [x] `frontend/src/components/ChatArea.tsx` — 订阅 `activeAgentNumber`，替换 `teamMembers.findIndex` 查找逻辑
- [x] `frontend/src/components/ChatArea.tsx` — 新增 useEffect 监听 `streamingContent` 和 `chatStreamText`，近底时自动滚动
- [x] `frontend/src/components/ChatArea.tsx` — `processQueue` 递归调用加 `await`
- [x] `frontend/src/components/ChatArea.tsx` — `handleSend` 末尾 `processQueue()` 加 `await`
