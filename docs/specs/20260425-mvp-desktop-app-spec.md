# Sloth Agent 桌面版 MVP 规格

> 关联架构: `docs/design/desktop-app-architecture.md`
> Figma 设计: `fNq2y8ZDKCGeUpCjEcHPSv` node `1:748`
> 日期: 2026-04-25
> 状态: IN PROGRESS

---

## 1. 产品概述

Sloth Agent 桌面版 — 让产品经理输入需求文档，通过 AI Agent 输出可运行功能原型。

**第一个 MVP 范围：** 用户创建 Inspiration（项目），每个 Inspiration 自带默认 Agent，Agent 可配置 LLM 模型，用户在窗口中与 Agent 进行基础对话。

**原则：** 能用，不是好看。每 3 天发布一个版本。

---

## 2. 技术栈

| 层 | 技术 |
|---|------|
| 桌面壳 | Tauri v2 (Rust) |
| 前端 | React 18 + TypeScript + Vite |
| 状态管理 | Zustand |
| UI 样式 | CSS Modules（不用 Tailwind） |
| 后端 | Python FastAPI (Sidecar) |
| 数据库 | SQLite (SQLAlchemy) |
| 通信 | invoke → Rust reqwest → FastAPI |
| LLM | 直连 OpenAI-compatible API |

---

## 3. 功能需求

### 3.1 Inspiration 管理（迭代 1）

| 功能 | 描述 | API |
|------|------|-----|
| 创建 | 输入名称，创建 Inspiration，自动生成默认 Agent | `POST /api/inspirations` |
| 列表 | 返回所有 Inspiration，含最后消息摘要 | `GET /api/inspirations` |
| 获取 | 获取单个 Inspiration 详情 | `GET /api/inspirations/{id}` |
| 删除 | 删除 Inspiration 及关联数据 | `DELETE /api/inspirations/{id}` |
| 搜索 | 按名称模糊搜索 | `GET /api/inspirations?q=` |

### 3.2 基础对话（迭代 2）

| 功能 | 描述 | API |
|------|------|-----|
| 发送消息 | 用户输入文本，发送给默认 Agent | `POST /api/inspirations/{id}/chat` |
| 流式响应 | SSE 流式返回 Agent 回复 | `POST /api/inspirations/{id}/chat/stream` |
| 消息历史 | 返回对话历史 | `GET /api/inspirations/{id}/messages` |

### 3.3 Agent 管理（迭代 3）

| 功能 | 描述 | API |
|------|------|-----|
| Agent 列表 | 返回 Inspiration 下所有 Agent | `GET /api/inspirations/{id}/agents` |
| 添加 Agent | 创建新 Agent 并指定模型 | `POST /api/inspirations/{id}/agents` |
| 配置 LLM | 修改 Agent 的 LLM 模型和参数 | `PATCH /api/agents/{id}` |

---

## 4. UI 结构（4 列布局）

从 Figma 设计拆解的布局结构：

```
┌──────┬──────────┬───────────────────────┬──────────┐
│ Col1 │  Col2    │  Col3 (flex)           │  Col4    │
│ 64px │  280px   │  Chat Area             │  320px   │
├──────┤──────────┤                       │          │
│ Logo │ Header   │  TopAppBar (64px)     │ Header   │
│      │ + 新建   │  ┌─────────────────┐  │ Team     │
│ nav  ├──────────┤  │ Chat Canvas     │  ├──────────┤
│ icons│ Search   │  │ - Date Divider  │  │ Collab-  │
│      ├──────────┤  │ - System Msg    │  │ orators  │
│      │          │  │ - Agent Bubble  │  ├──────────┤
│      │ Project  │  │ - Human Bubble  │  │ Agents   │
│      │ List     │  │ - In-Progress   │  │ List     │
│      │          │  └─────────────────┘  │          │
│      │          │  Input Area           │          │
├──────┤          │                       │          │
│User  │          │                       │          │
│avatar│          │                       │          │
└──────┴──────────┴───────────────────────┴──────────┘
```

**迭代 1 实现：** Col1 (SideNavBar) + Col2 (Project List) + Col3 骨架（空聊天区 + 禁用输入框）  
**迭代 2 实现：** Col3 完整 Chat（消息列表 + 输入 + 流式）  
**迭代 3 实现：** Col4 (Right Panel) Agent 管理

---

## 5. 数据模型

### 5.1 Inspiration

```
id: UUID (PK)
name: String (1-100 chars)
created_at: DateTime
updated_at: DateTime
```

### 5.2 Agent

```
id: UUID (PK)
inspiration_id: UUID (FK → Inspiration)
name: String (e.g. "默认 Agent")
role: String (e.g. "ui_ux", "req_expert", "fullstack_dev")
model: String (e.g. "gpt-4o", "claude-3.5-sonnet")
status: Enum [idle, working, error]
created_at: DateTime
```

### 5.3 Message

```
id: UUID (PK)
inspiration_id: UUID (FK → Inspiration)
agent_id: UUID (FK → Agent, nullable for human messages)
role: Enum [system, human, agent]
content: Text
created_at: DateTime
```

---

## 6. 迭代规划

### 迭代 1: 项目外壳 + Inspiration CRUD（3 天）

**目标：** 用户能创建和管理 Inspiration  
**交付物：** 可运行的 4 列布局 + SideNavBar + Project List + Inspiration CRUD  
**验收标准：**
- [ ] 应用启动，看到完整 4 列布局（Col3 为空骨架，Col4 为空骨架）
- [ ] SideNavBar 显示 Logo + 3 个导航图标 + 用户头像
- [ ] Project List 有"新建 Inspiration"按钮，点击创建
- [ ] 创建 3 个不同名称的 Inspiration，列表中正确显示
- [ ] 点击 Inspiration 可切换选中态（绿色左边框 + 高亮背景）
- [ ] 搜索框输入关键词，列表过滤匹配的 Inspiration
- [ ] 重启应用，Inspiration 数据持久化不丢失

### 迭代 2: 聊天 + 默认 Agent（3 天）  

**目标：** 用户能在 Inspiration 中和默认 Agent 对话  
**交付物：** 完整 Chat 区域（消息列表 + 气泡 + 输入 + 流式响应）  
**验收标准：**
- [ ] 创建 Inspiration 时自动创建默认 Agent（模型默认 gpt-4o）
- [ ] 选中 Inspiration 后，Chat 区域显示已有消息历史
- [ ] 输入文本点击发送，消息显示为蓝色气泡（右侧，Human 样式）
- [ ] Agent 回复显示为灰色气泡（左侧，带头像 + 名称 + 时间戳）
- [ ] Agent 回复以 SSE 流式展示，逐字/逐句出现
- [ ] 刷新后消息历史保留

### 迭代 3: Agent 管理 + LLM 配置（3 天）

**目标：** 用户能管理 Agent 并配置 LLM 模型  
**交付物：** Right Panel（Agent 列表 + 模型选择器 + 状态指示）  
**验收标准：**
- [ ] Right Panel 显示 Inspiration 下的 Agent 列表
- [ ] 每个 Agent 显示名称、状态灯（绿=working、灰=idle）、模型选择器
- [ ] 模型选择器下拉可切换 LLM（gpt-4o / claude-3.5-sonnet / gemini-1.5）
- [ ] "Add Agent"按钮创建新 Agent
- [ ] Agent 状态随对话实时更新（idle → working → idle）

---

## 7. 错误处理

- Sidecar 崩溃：前端检测连接断开 → 提示"后端服务已断开，正在尝试重启..." → 自动重启
- LLM 调用失败：前端显示错误气泡（红色边框），用户可点击重试
- 端口冲突：启动时自动检测 8080 端口，被占用则选下一个可用端口

---

## 8. 不做什么

- 不实现多 Agent 并行协作（单 Agent 串行对话）
- 不实现代码预览/Monaco Editor
- 不实现 Collaborators（人类协作者）
- 不实现 @mention 功能
- 不实现附件上传
- 不实现 Markdown 渲染（MVP 纯文本消息）
- 不做 LiteLLM 多 Provider 路由（直连一个 API）
- 不做 Agent 角色行为区分（所有 Agent 行为相同，只是模型可配置不同）

---

## 9. 项目结构（目标）

```
frontend/src/
├── App.tsx                    # 主布局（4 列）
├── main.tsx                   # 入口
├── components/
│   ├── SideNavBar.tsx         # Col1: 导航栏
│   ├── ProjectList.tsx        # Col2: Inspiration 列表
│   ├── ChatArea.tsx           # Col3: 聊天区域
│   ├── ChatMessage.tsx        # 消息气泡组件
│   ├── ChatInput.tsx          # 输入区域组件
│   └── RightPanel.tsx         # Col4: Agent 管理
├── stores/
│   ├── inspirationStore.ts    # Zustand: Inspiration 状态
│   ├── chatStore.ts           # Zustand: 聊天状态
│   └── agentStore.ts          # Zustand: Agent 状态
└── api/
    └── client.ts              # invoke 封装

backend/app/
├── main.py                    # FastAPI 入口
├── models.py                  # SQLAlchemy 模型
├── database.py                # 数据库连接
├── routers/
│   ├── inspirations.py        # Inspiration CRUD
│   ├── chat.py                # 聊天接口
│   └── agents.py              # Agent 管理
└── services/
    ├── llm.py                 # LLM 调用封装
    └── agent.py               # Agent 逻辑
```

---

*Spec 版本: 1.0 — 2026-04-25*
