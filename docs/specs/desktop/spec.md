# 桌面应用 MVP

> 归档参考: archive/initial-specs/20260425-mvp-desktop-app-spec.md
> 最后更新: 2026-05-01

## 概述

基于 Tauri v2 的桌面应用，让产品经理通过 UI 与 Agent 交互，输入需求文档，Agent 产出可运行原型。

## 技术栈

| 层 | 技术 |
|---|------|
| 桌面壳 | Tauri v2 (Rust) |
| 前端 | React 18 + TypeScript + Vite |
| 状态管理 | Zustand |
| 样式 | CSS Modules |
| 后端 | Python FastAPI (Sidecar) |
| 数据库 | SQLite (SQLAlchemy async + aiosqlite) |
| LLM | 直连 OpenAI-compatible API |

## 已实现

### Iter-1：Inspiration CRUD + 4 列布局
- 创建/列表/获取/删除/搜索 Inspiration
- 前端 4 列布局（InspirationList, ChatArea, RightPanel）

### Iter-2：Settings + 聊天 + 默认 Agent
- LLM 管理页（CRUD + 连接测试）
- 消息流 + SSE 流式响应
- Lead Agent 默认对话

### Iter-3：Agent Pool + Team 管理
- 5 个内置 Agent 模板（1 Lead + 4 Expert）
- Agent 加入/离开 Team
- Right Panel 团队面板
- 灵感创建时 auto_join Agent

### 前端组件
- `InspirationList`, `ChatArea`, `RightPanel`
- `AgentPoolList`, `AgentDetail`
- `SettingsPage`, `LLMConfig`

### Zustand Stores
- `inspirationStore`, `chatStore`, `agentPoolStore`, `agentStore`
- `brainstormStore`, `settingsStore`, `llmStore`

## 待实现（Iter-4~9）

见 Brainstorm spec 迭代计划。

## 关键接口

- `POST /api/inspirations` — 创建 Inspiration
- `GET /api/settings/agents` — Agent Pool 列表
- `POST /api/inspirations/{id}/chat/stream` — SSE 流式对话
- `PATCH /api/settings/agents/{id}` — 更新 Agent 模板
