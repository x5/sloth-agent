# 对话模式

> 归档参考: archive/initial-specs/20260416-07-chat-mode-spec.md
> 最后更新: 2026-05-01

## 概述

Sloth 支持两种对话模式：CLI REPL（核心运行时）和 Web Chat（桌面应用）。

## 已实现

### CLI REPL (`src/sloth_agent/chat/`)

- `repl.py` — 交互式 REPL 循环
- `session.py` — 对话会话管理
- `autonomous.py` — 自主执行模式
- CLI 集成：`cli/chat.py`, `cli/chat_ux.py`, `cli/context.py`

### Web Chat（桌面应用）

- `POST /api/inspirations/{id}/chat` — 发送消息
- `POST /api/inspirations/{id}/chat/stream` — SSE 流式响应
- `GET /api/inspirations/{id}/messages` — 消息历史
- Lead Agent 基于 system_prompt 回复
- Zustand store：`chatStore.ts`

### 消息模型

- `Message` 表：id, inspiration_id, agent_id, role, content, created_at
- 支持 user / assistant / system 三种角色

## 待实现

- 多 Agent 对话路由（当前只有 Lead Agent 回复）
- 工具调用结果在聊天中展示

## 关键接口

- `POST /api/inspirations/{id}/chat` — Web Chat API
- `ChatSession.send(message) → AsyncIterator[Token]`
- `REPL.run()` — 启动交互式 REPL
