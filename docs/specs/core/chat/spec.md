# 对话模式

> 归档参考: archive/initial-specs/20260416-07-chat-mode-spec.md
> 最后更新: 2026-05-02 (brainstorm-fluid-discussion)
> Scope: Core（CLI REPL 与 Desktop Chat 为 adapter）

## 概述

Sloth 支持两种对话模式：CLI REPL（核心运行时）和 Web Chat（桌面应用）。

## 已实现

### CLI REPL (`src/sloth_agent/chat/`)

- `repl.py` — 交互式 REPL 循环
- `session.py` — 对话会话管理
- `autonomous.py` — 自主执行模式
- CLI 集成：`cli/chat.py`, `cli/chat_ux.py`, `cli/context.py`

### 流式响应

- Chat 模式使用 `POST /api/inspirations/{id}/chat/stream` SSE 端点
- 流式 token 到达时（`streamingContent` 或 `chatStreamText` 变化），若用户距底部 300px 内则自动滚动到底
- 流式期间显示流式气泡（`chatStreamText` 非空时）或思考动画（等待首个 token）

### 消息模型

- `Message` 表：id, inspiration_id, agent_id, role, content, created_at
- 支持 user / assistant / system 三种角色

### 消息队列

- 用户随时可发送消息，系统忙时消息入队
- 队列逐条发送（不合并），每条独立触发一次完整的 LLM 请求
- `processQueue` 和 `handleSend` 尾部均使用 `await` 保证错误向上传播、队列串行执行
- 队列状态通过输入框上方 badge 实时显示

## 待实现

- 多 Agent 对话路由（当前只有 Lead Agent 回复）
- 工具调用结果在聊天中展示

## 关键接口

- `POST /api/inspirations/{id}/chat` — Web Chat API
- `ChatSession.send(message) → AsyncIterator[Token]`
- `REPL.run()` — 启动交互式 REPL
