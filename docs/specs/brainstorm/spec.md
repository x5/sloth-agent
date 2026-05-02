# Brainstorm 模式

> 归档参考: archive/initial-specs/20260430-brainstorm-mode-spec.md
> 最后更新: 2026-05-02 (brainstorm-fluid-discussion)
> Iter-4 完成: 2026-05-01
> Iter-5 完成: 2026-05-01

## 概述

多 Agent 多轮讨论模式。用户发起话题，Expert Agent 循环发言、互相回应、反驳、追问，直到所有 Agent 均无新内容（全员 PASS）时自然结束。每个 Agent 实时流式响应，可见完整对话历史。所有产出写入隔离沙箱，项目文件零风险。

**Iter-6 目标**：改为持久连接模型——进入 Brainstorm 模式后建立单一 SSE 连接，用户可随时注入消息不中断 agent 发言，任意消息可 reply，讨论持续直到手动结束或全员 PASS。

## 已实现（Iter-4 ~ Iter-5）

### 后端 API (`backend/app/routers/brainstorm.py`)

- `POST /api/inspirations/{id}/brainstorm-sessions` — 创建会话
- `GET /api/inspirations/{id}/brainstorm-sessions` — 会话列表
- `GET /api/brainstorm-sessions/{id}` — 会话详情（含沙箱文件树）
- `POST /api/brainstorm-sessions/{id}/discuss` — 发起讨论（SSE 流式推送）⚠️ deprecated，Iter-7 删除
- `DELETE /api/brainstorm-sessions/{id}/discuss` — 中止讨论 ⚠️ deprecated，Iter-7 删除

### 讨论引擎 (`backend/app/services/brainstorm.py`)

- **多轮循环架构**：`while sub_round < MAX_ROUNDS` 循环，每轮所有 Agent 顺序发言；全员 PASS 时自然结束（`speeches_this_round == 0`），最多 8 轮
- **PASS 机制**：Agent 认为无新内容可补充时发送文本 `PASS`；后端检测后发送 `agent_pass` SSE 事件，消息不持久化
- **互动式 Prompt**：要求 Agent 针对最新发言回应，可点名反驳、追问；明确禁止重复已有观点；无新内容时发 PASS
- 每个 Agent 可见完整对话历史（含本轮前序 Agent 的响应），`_load_history` 通过 JOIN 获取真实 agent name
- `agent_start` / `message_done` SSE 事件携带 `agent_number`（1-based 索引）用于前端颜色标识
- 支持 abort 中止（前端 AbortController + 后端 `_abort` flag，在每次 token 和每次 agent 发言间检查）

#### SSE 事件列表（Iter-5 实现）

| 事件 | 载荷 | 说明 |
|------|------|------|
| `agent_start` | `agent_id, agent_name, agent_number` | Agent 开始发言（显示 typing 气泡）|
| `agent_token` | `agent_id, agent_name, token` | 流式 token |
| `message_done` | `agent_id, agent_name, agent_number, message_id, full_content, round` | Agent 发言完成并入库 |
| `agent_pass` | `agent_id, agent_name, agent_number` | Agent PASS（清除气泡，不入库）|
| `discussion_end` | `message_count, round` | 讨论结束 |
| `max_reached` | `limit` | 达到消息上限 |
| `error` | `error` | 错误 |

### 沙箱隔离 (`backend/app/services/sandbox.py`)

- 每个 Brainstorm 会话有独立沙箱目录 `brainstorm-sessions/{id}/`
- 沙箱内可自由读写，项目文件只读

### 数据模型

- `BrainstormSession` — id, inspiration_id, topic, status, sandbox_path
- `BrainstormFile` — session_id, path, content

### 前端（Iter-5 实现）

**Store (`frontend/src/stores/brainstormStore.ts`)**
- Zustand store: sessions[], activeId, brainstormMode
- 讨论状态: `discussionActive`, `activeAgentId`, `activeAgentName`, `activeAgentNumber`, `discussionMessages`, `streamingContent`
- `activeAgentNumber` 由后端 `agent_start` 事件写入，用于气泡颜色标识；在 `agent_pass` / `discussion_end` / stop 时清空
- `startBrainstorm` — 创建新会话并自动激活
- `stopBrainstorm` — 清除 brainstormMode（不结束会话）
- `activateSession` — 激活指定会话（结束当前活跃会话，保证唯一活跃）
- `endSession` — 结束指定会话
- `setActive` — 仅切换视图（不改变状态）
- `startDiscussion` — SSE 讨论（AbortController 支持随时中止）⚠️ Iter-6 废弃
- `stopDiscussion` — 中止当前讨论（abort + 通知后端）⚠️ Iter-6 废弃

**聊天集成 (`frontend/src/components/ChatArea.tsx`)**
- 闪电按钮切换 brainstorm mode
- brainstorm 消息带 `brainstorm_session_id` 过滤
- 会话切换时插入分割线（start/end/transition）
- 顶部 badge 显示当前会话编号

---

## 待实现（Iter-6）

### 架构改造：持久连接模型

**核心问题（当前）：**
- `sendOne()` 检测到 `discussionActive` 时强制 abort 当前 SSE 再重建，用户每次发言都截断 agent
- `reply_to_message_id` API 字段存在但 UI 无入口且前端调用不传
- `startDiscussion()` 每次清空 `discussionMessages`，靠 useEffect 追加，脆弱

**目标架构（Iter-6 后）：**

```
进入 brainstorm 模式
  → POST /connect  建立持久 SSE 连接（一次）
  → 连接保持，持续推送所有事件

用户发消息
  → POST /inject   注入队列（立即返回）
  → 不中断 SSE 连接
  → engine 在当前 agent 完成本轮后处理新消息
  → SSE 流持续推送 agents 响应

离开 brainstorm 模式
  → DELETE /connect  优雅关闭
```

### 后端新端点 (`backend/app/routers/brainstorm.py`)

| 端点 | 说明 |
|------|------|
| `POST /api/brainstorm-sessions/{id}/connect` | 建立持久 SSE 连接 |
| `POST /api/brainstorm-sessions/{id}/inject` | 注入用户消息到引擎队列 |
| `DELETE /api/brainstorm-sessions/{id}/connect` | 优雅关闭持久连接 |

**`inject` 请求体：**
```json
{ "content": "...", "reply_to_message_id": "..." }
```

### BrainstormEngine 重构

- `run()` 改为持久 queue-driven 循环（`asyncio.Queue`）
- `inject(content, reply_to)` 异步方法，向 queue 放消息
- 每个 agent 发言结束后检查 queue 是否有新消息，有则优先处理（结束当前轮，启动新轮）
- `heartbeat` SSE 事件（30s 超时），防止连接被代理层 reset
- `round_end` SSE 事件，本轮 agents 全部发言完毕后推送（连接保持）

### 新增 SSE 事件（Iter-6）

| 事件 | 载荷 | 说明 |
|------|------|------|
| `user_message` | `message_id, content` | 用户消息已入库（用于替换前端乐观更新）|
| `round_end` | `round, speeches` | 本轮结束（连接不关闭）|
| `heartbeat` | `{}` | 空闲心跳 |

### 前端 Store 重构 (`brainstormStore.ts`)

**新增状态：**
```ts
discussionConnected: boolean      // 持久连接是否活跃（替代 discussionActive）
replyingToId: string | null       // 当前 reply 目标消息 ID
replyingToContent: string | null  // 被引用消息预览（前 30 字）
```

**新增方法：**
```ts
connectSession(sessionId: string): Promise<void>
disconnectSession(): void
injectMessage(sessionId: string, content: string, replyToMessageId?: string): Promise<void>
```

**废弃方法（Iter-7 删除）：**
- `startDiscussion()` → 改为 `connectSession` + `injectMessage`
- `stopDiscussion()` → 改为 `disconnectSession`

### 前端 UI

**Reply 按钮（`ChatArea.tsx`）：**
- brainstorm 模式下，消息 hover 显示 `↩ Reply` 按钮（右上角 ghost 样式）
- 点击 → `replyingToId` + `replyingToContent` 写入 store
- 输入框上方出现引用条：`↩ 回复 {agent_name} · "{内容前30字}" [✕]`，accent 色左边线
- `[✕]` 清空 `replyingToId`
- `handleSend` 读取 `replyingToId` 传入 `injectMessage` 后清空

**彩色线程竖线（`ChatArea.tsx` + `threadColor.ts`）：**
- `threadColor.ts` 工具：`getRootId(id, messages)` → `threadHue(rootId)` → `hsl(hue, 45%, 58%)`
- 有 `parent_message_id` 的消息显示 3px 左侧竖线
- 无 `parent_message_id`（根消息）不显示竖线
- 仅 brainstorm 模式显示，chat 模式不显示

---

## 迭代计划

| 迭代 | 范围 | 状态 |
|------|------|------|
| Iter-4 | 会话沙箱 CRUD | ✅ |
| Iter-5 | 讨论引擎 + SSE | ✅ |
| Iter-6 | 持久连接 + Reply + 彩色线程 | ⬜ |
| Iter-7 | 读 Tools + 上下文引擎 | ⬜ |
| Iter-8 | 写 Tools + 受限执行器 | ⬜ |
| Iter-9 | 异步自主模式 | ⬜ |

## 关键接口

**Iter-5（当前）：**
- `POST /api/brainstorm-sessions/{id}/discuss` — 发起讨论（SSE 流）⚠️ deprecated
- `DELETE /api/brainstorm-sessions/{id}/discuss` — 中止讨论 ⚠️ deprecated

**Iter-6（新）：**
- `POST /api/brainstorm-sessions/{id}/connect` — 建立持久 SSE 连接
- `POST /api/brainstorm-sessions/{id}/inject` — 注入用户消息
- `DELETE /api/brainstorm-sessions/{id}/connect` — 关闭连接

- `POST /api/inspirations/{id}/brainstorm-sessions` — 创建会话
- `GET /api/inspirations/{id}/brainstorm-sessions` — 会话列表
- `GET /api/brainstorm-sessions/{id}` — 会话详情（含沙箱文件树）
- `POST /api/brainstorm-sessions/{id}/discuss` — 发起讨论（SSE 流式推送）
- `DELETE /api/brainstorm-sessions/{id}/discuss` — 中止讨论

### 讨论引擎 (`backend/app/services/brainstorm.py`)

- **多轮循环架构**：`while sub_round < MAX_ROUNDS` 循环，每轮所有 Agent 顺序发言；全员 PASS 时自然结束（`speeches_this_round == 0`），最多 8 轮
- **PASS 机制**：Agent 认为无新内容可补充时发送文本 `PASS`；后端检测后发送 `agent_pass` SSE 事件，消息不持久化
- **互动式 Prompt**：要求 Agent 针对最新发言回应，可点名反驳、追问；明确禁止重复已有观点；无新内容时发 PASS
- 每个 Agent 可见完整对话历史（含本轮前序 Agent 的响应），`_load_history` 通过 JOIN 获取真实 agent name
- `agent_start` / `message_done` SSE 事件携带 `agent_number`（1-based 索引）用于前端颜色标识
- 支持 abort 中止（前端 AbortController + 后端 `_abort` flag，在每次 token 和每次 agent 发言间检查）

#### SSE 事件列表

| 事件 | 载荷 | 说明 |
|------|------|------|
| `agent_start` | `agent_id, agent_name, agent_number` | Agent 开始发言（显示 typing 气泡）|
| `agent_token` | `agent_id, agent_name, token` | 流式 token |
| `message_done` | `agent_id, agent_name, agent_number, message_id, full_content, round` | Agent 发言完成并入库 |
| `agent_pass` | `agent_id, agent_name, agent_number` | Agent PASS（清除气泡，不入库）|
| `discussion_end` | `message_count, round` | 讨论结束 |
| `max_reached` | `limit` | 达到消息上限 |
| `error` | `error` | 错误 |

### 沙箱隔离 (`backend/app/services/sandbox.py`)

- 每个 Brainstorm 会话有独立沙箱目录 `brainstorm-sessions/{id}/`
- 沙箱内可自由读写，项目文件只读

### 数据模型

- `BrainstormSession` — id, inspiration_id, topic, status, sandbox_path
- `BrainstormFile` — session_id, path, content

### 消息队列

- 用户随时可发送消息，系统忙时消息入队
- 系统响应完成后，队列中所有消息合并为一条批量发送
- 队列状态通过输入框上方 badge 实时显示

### 前端

**Store (`frontend/src/stores/brainstormStore.ts`)**
- Zustand store: sessions[], activeId, brainstormMode
- 讨论状态: `discussionActive`, `activeAgentId`, `activeAgentName`, `activeAgentNumber`, `discussionMessages`, `streamingContent`
- `activeAgentNumber` 由后端 `agent_start` 事件写入，用于气泡颜色标识；在 `agent_pass` / `discussion_end` / stop 时清空
- `startBrainstorm` — 创建新会话并自动激活
- `stopBrainstorm` — 清除 brainstormMode（不结束会话）
- `activateSession` — 激活指定会话（结束当前活跃会话，保证唯一活跃）
- `endSession` — 结束指定会话
- `setActive` — 仅切换视图（不改变状态）
- `startDiscussion` — SSE 讨论（AbortController 支持随时中止）
- `stopDiscussion` — 中止当前讨论（abort + 通知后端）
- SSE 事件处理: `agent_start`, `agent_token`, `message_done`, `agent_pass`, `discussion_end`, `error`

**聊天集成 (`frontend/src/components/ChatArea.tsx`)**
- 闪电按钮切换 brainstorm mode
- brainstorm 消息带 `brainstorm_session_id` 过滤
- 会话切换时插入分割线（start/end/transition）
- 顶部 badge 显示当前会话编号

**RightPanel (`frontend/src/components/RightPanel.tsx`)**
- Brainstorm Tab：搜索框 + 会话详情卡片
- Slide toggle 控制会话 active/ended 状态
- 配置信息（max_messages, cooldown, message_count）
- 沙箱文件树展示

## 待实现（规范阶段）

- 彩色线程 UI（BrainstormArea 组件）
- Lead Agent 回合总结

## 迭代计划

| 迭代 | 范围 |
|------|------|
| Iter-4 | 会话沙箱 CRUD | ✅ |
| Iter-5 | 讨论引擎 + SSE | ✅ |
| Iter-6 | 彩色线程 UI | ⬜ |
| Iter-7 | 读 Tools + 上下文引擎 | ⬜ |
| Iter-8 | 写 Tools + 受限执行器 | ⬜ |
| Iter-9 | 异步自主模式 | ⬜ |

## 关键接口

- `POST /api/brainstorm-sessions/{id}/discuss` — 发起讨论（SSE 流式推送）
- `DELETE /api/brainstorm-sessions/{id}/discuss` — 中止讨论
- `SandboxManager.create_session(inspiration_id) → BrainstormSession`
