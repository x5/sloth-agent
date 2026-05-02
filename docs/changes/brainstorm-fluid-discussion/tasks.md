# Tasks: Brainstorm 流体讨论引擎（Iter-6）

> 关联 Delta: docs/changes/brainstorm-fluid-discussion/delta.md
> 日期: 2026-05-02

## Task 6.0 — 后端持久连接 + 引擎重构

- [ ] 重构 `BrainstormEngine.run()` 为 queue-driven 持久循环（REQ-BS-23）
- [ ] 实现 `inject(content, reply_to)` 方法（REQ-BS-24）
- [ ] 每轮 agent 发言后检查 queue（REQ-BS-25）
- [ ] 添加 `heartbeat` 机制（30s idle 推送）（REQ-BS-26）
- [ ] 推送 `round_end` SSE 事件（REQ-BS-27）
- [ ] 推送 `user_message` SSE 事件（REQ-BS-28）
- [ ] 添加 `POST /connect` 端点（REQ-BS-20）
- [ ] 添加 `POST /inject` 端点（REQ-BS-21）
- [ ] 添加 `DELETE /connect` 端点（REQ-BS-22）
- [ ] 补充后端集成测试（`test_brainstorm.py`）：connect/inject/disconnect 流程

验证命令：`uv run pytest backend/tests/ -v`

## Task 6.1 — 前端 Store 重构

- [ ] 新增状态 `discussionConnected`, `replyingToId`, `replyingToContent`（REQ-BS-31/32/33）
- [ ] 实现 `connectSession(sessionId)` — 建立持久 SSE，处理 `user_message` / `round_end` / `heartbeat` 事件（REQ-BS-34）
- [ ] 实现 `disconnectSession()` — 关闭 SSE（REQ-BS-35）
- [ ] 实现 `injectMessage(sessionId, content, replyToMessageId?)` — POST /inject（REQ-BS-36）
- [ ] 废弃注释 `startDiscussion` / `stopDiscussion`，不删除（REQ-BS-10/11）
- [ ] 补充 store 单元测试

验证命令：`npm run test -- --run`（frontend/）

## Task 6.2 — Reply UI

- [ ] 消息 hover 显示 `↩ Reply` ghost 按钮（brainstorm 模式）（REQ-BS-37）
- [ ] 点击写入 `replyingToId` / `replyingToContent`（REQ-BS-38）
- [ ] 输入框上方引用条组件（REQ-BS-39）
- [ ] `[✕]` 清空 reply 状态（REQ-BS-40）
- [ ] `handleSend` 读取并传递 `replyingToId`，发送后清空（REQ-BS-41）
- [ ] 补充组件测试

验证命令：`npm run test -- --run`（frontend/）

## Task 6.3 — 彩色线程竖线

- [ ] 新建 `frontend/src/utils/threadColor.ts`：`getRootId` / `threadHue` / `threadColor`（REQ-BS-42）
- [ ] 消息渲染：有 `parent_message_id` → 3px 左侧竖线（REQ-BS-43/44）
- [ ] 仅 brainstorm 模式渲染竖线（REQ-BS-45）
- [ ] 补充 `threadColor.test.ts` 单元测试

验证命令：`npm run test -- --run`（frontend/）

## 完成条件

- [ ] 所有后端测试通过：`uv run pytest tests/ -v`
- [ ] 所有前端测试通过：`npm run test -- --run`
- [ ] Delta 合并到 `docs/specs/brainstorm/spec.md` ✅（已在 spec 中直接写入 Iter-6 章节）
- [ ] 变更目录归档到 `docs/archive/brainstorm-fluid-discussion/`
