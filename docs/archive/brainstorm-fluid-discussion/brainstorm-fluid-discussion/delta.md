# Delta: Brainstorm 流体讨论引擎

> 关联模块: specs/brainstorm/spec.md
> 日期: 2026-05-02

## ADDED Requirements

### 后端新端点

- REQ-BS-20: `POST /api/brainstorm-sessions/{id}/connect` — 建立持久 SSE 连接，返回 event-stream；同一 session 同时只允许一个连接
- REQ-BS-21: `POST /api/brainstorm-sessions/{id}/inject` — 注入用户消息到引擎 queue（立即返回 202）；请求体 `{ "content": str, "reply_to_message_id": str | null }`
- REQ-BS-22: `DELETE /api/brainstorm-sessions/{id}/connect` — 优雅关闭持久连接，engine 完成当前 agent 发言后退出

### BrainstormEngine 重构

- REQ-BS-23: `run()` 改为持久 `asyncio.Queue`-driven 循环，`await queue.get()` 等待用户消息触发新轮次
- REQ-BS-24: 新增 `inject(content: str, reply_to: str | None)` 异步方法，向 queue 放消息
- REQ-BS-25: 每个 agent 发言结束后检查 queue（non-blocking `queue.get_nowait()`），有消息则结束当前轮，处理注入消息后重启轮次
- REQ-BS-26: 30s 空闲时推送 `heartbeat` SSE 事件，防止代理层重置连接
- REQ-BS-27: 本轮所有 agent 发言完毕后推送 `round_end` SSE 事件，连接保持

### 新增 SSE 事件

- REQ-BS-28: `user_message` 事件 — 载荷 `{ message_id, content }`，用户消息入库后推送（替换前端乐观更新）
- REQ-BS-29: `round_end` 事件 — 载荷 `{ round, speeches }`，本轮结束时推送
- REQ-BS-30: `heartbeat` 事件 — 载荷 `{}`，30s 无新事件时推送

### 前端 Store 新增

- REQ-BS-31: 新状态 `discussionConnected: boolean` — 持久连接是否活跃
- REQ-BS-32: 新状态 `replyingToId: string | null` — 当前 reply 目标消息 ID
- REQ-BS-33: 新状态 `replyingToContent: string | null` — 被引用消息内容前 30 字
- REQ-BS-34: 新方法 `connectSession(sessionId: string): Promise<void>` — 建立持久 SSE，写入 `discussionConnected: true`
- REQ-BS-35: 新方法 `disconnectSession(): void` — 关闭 SSE，写入 `discussionConnected: false`
- REQ-BS-36: 新方法 `injectMessage(sessionId: string, content: string, replyToMessageId?: string): Promise<void>` — `POST /inject`，传递 reply id

### 前端 Reply UI

- REQ-BS-37: brainstorm 模式下，消息 hover 右上角显示 `↩ Reply` ghost 按钮
- REQ-BS-38: 点击 Reply → store 写入 `replyingToId` + `replyingToContent`（取内容前 30 字）
- REQ-BS-39: 输入框上方出现引用条：`↩ 回复 {agent_name} · "{内容前30字}" [✕]`，accent 色左边线
- REQ-BS-40: `[✕]` 清空 `replyingToId` / `replyingToContent`
- REQ-BS-41: `handleSend` 读取 `replyingToId` 传入 `injectMessage`，发送后清空

### 前端彩色线程竖线

- REQ-BS-42: 新建 `frontend/src/utils/threadColor.ts`：`getRootId(id, messages)` 递归追溯根消息，`threadHue(rootId)` 哈希得到 hue，`threadColor(hue)` 返回 `hsl(hue, 45%, 58%)`
- REQ-BS-43: 有 `parent_message_id` 的消息显示 3px 左侧彩色竖线（颜色来自 `threadColor`）
- REQ-BS-44: 根消息（无 `parent_message_id`）不显示竖线
- REQ-BS-45: 线程竖线仅在 brainstorm 模式下渲染

## MODIFIED Requirements

- REQ-BS-10 (原 startDiscussion): 废弃，由 `connectSession` + `injectMessage` 替代；代码保留到 Iter-7 删除
- REQ-BS-11 (原 stopDiscussion): 废弃，由 `disconnectSession` 替代；代码保留到 Iter-7 删除

## REMOVED Requirements

无（旧端点 deprecated 但不删除，Iter-7 处理）
