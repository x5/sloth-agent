# 桌面应用 MVP

> 归档参考: archive/initial-specs/20260425-mvp-desktop-app-spec.md
> 最后更新: 2026-05-04
> Scope: Desktop

## 概述

基于 Tauri v2 的桌面应用，让产品经理通过 UI 与 Agent 交互，输入需求文档，Agent 产出可运行原型。

## 架构定位（Iter-7 起）

Desktop Sidecar 引入共享 Context Engine 作为运行时核心能力，不归属于单一业务模式。

- 共享引擎：统一处理上下文裁剪、关键链路保护、预算控制。
- 首轮接入：Iter-7 在 Brainstorm 流程先接入。
- 后续接入：Chat 与多 Agent Autonomous 复用同一 Context Engine，仅策略参数不同。

Context Engine 的模块规格见 `docs/specs/context/spec.md`。

模块关系：
- Context Engine × Memory：摘要与原始消息的双轨可追溯。
- Context Engine × Session：断线重连与恢复时使用同一上下文快照语义。
- Context Engine × Observability：统一输出上下文相关指标与 trace。
- Context Engine × Daemon：后台执行时仍按同一预算与压缩规则构建上下文。

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

### 侧栏列表滚动行为
- Inspiration 列表、Agents 列表、Settings 列表在窗口高度不足时，必须保持 item 高度稳定并显示纵向滚动。
- 列容器与滚动容器必须显式允许高度收缩（`min-height: 0`）。
- 列表 item / provider card 必须禁止沿纵向主轴收缩（`flex: 0 0 auto`），避免内容被压扁重叠。

### 滚动条样式
- 桌面应用主要滚动容器必须统一使用与聊天消息区一致的蓝色细滚动条样式。
- 统一样式包括：`scrollbar-width: thin`、蓝色半透明 thumb、transparent track，以及 hover 时更高可见度的蓝色 thumb。

### Brainstorm interrupt 按钮
- 在 brainstorm mode 下，输入区必须提供一个与 brainstorm 闪电按钮并排的 interrupt icon button，用于中断当前讨论轮次。
- interrupt button 必须使用明确的“停止发言 / 静音”语义 icon，而不是独立红色文字按钮；当前实现为 speaker-with-X icon。
- 只有在当前存在 active agent 正在输出时，按钮才必须呈 brainstorm 紫色可点击态。
- 当 interrupt 已触发或当前无可中断轮次时，按钮必须保持可见，但呈灰色不可点击态。
- 点击 interrupt 只能中断当前正在进行的 agent 回复 / 当前 round，不能结束 brainstorm mode；brainstorm mode 的开始与结束仍由闪电按钮独立控制。

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
