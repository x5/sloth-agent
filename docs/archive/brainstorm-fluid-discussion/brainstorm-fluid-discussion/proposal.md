# Proposal: Brainstorm 流体讨论引擎

> 关联模块: specs/brainstorm/spec.md
> 日期: 2026-05-02
> 状态: APPROVED

## 背景

Iter-5 实现的 brainstorm 讨论采用「一次性请求-响应」模型：每次用户发消息都新建一个 `BrainstormEngine`，跑完所有 agent 后关闭 SSE 流。

这导致三个核心问题：
1. **用户无法在讨论中途注入消息**：`sendOne()` 遇到 `discussionActive` 时强制 abort 当前流再重建，每次发言都截断 agent 发言中
2. **无法 reply 指定消息**：`reply_to_message_id` 字段在 API 存在但前端无入口，`sendOne` 调用也不传
3. **历史脆弱**：`startDiscussion()` 每次清空 `discussionMessages`，靠 useEffect 追加，有顺序竞争风险

## 目标

将 brainstorm 改为「持久连接 + 队列注入」模型：
- 进入 brainstorm 模式时建立单一长连接 SSE
- 用户发消息通过 `POST /inject` 放入 queue，不中断 SSE 连接
- Engine 在当前 agent 发言结束后处理队列
- 支持 reply：前端消息 hover 显示 reply 按钮，引用条显示被回复内容
- 彩色线程竖线：通过 `parent_message_id` 追踪回复链，用颜色区分不同线程

## 影响范围

- `backend/app/routers/brainstorm.py` — 新增 3 个端点
- `backend/app/services/brainstorm.py` — 引擎重构
- `frontend/src/stores/brainstormStore.ts` — store 重构
- `frontend/src/components/ChatArea.tsx` — reply UI
- `frontend/src/utils/threadColor.ts` — 新文件，线程颜色工具

## 不影响范围

- 旧 `/discuss` 和 `DELETE /discuss` 端点保留（deprecated，Iter-7 删除）
- 沙箱隔离逻辑不变
- 数据模型不变（`parent_message_id`, `round`, `intent`, `truncated` 字段已存在）
