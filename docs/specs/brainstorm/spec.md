# Brainstorm 模式

> 归档参考: archive/initial-specs/20260430-brainstorm-mode-spec.md
> 最后更新: 2026-05-02 (review-fixes)
> Iter-4 完成: 2026-05-01
> Iter-5 完成: 2026-05-01
> Iter-6 完成: 2026-05-02

## 概述

多 Agent 多轮讨论模式。用户发起话题，Expert Agent 循环发言、互相回应、反驳、追问，直到所有 Agent 均无新内容（全员 PASS）时自然结束。每个 Agent 实时流式响应，可见完整对话历史。所有产出写入隔离沙箱，项目文件零风险。

进入 Brainstorm 模式后建立单一持久 SSE 连接（Iter-6），用户可随时注入消息不中断 agent 发言，任意消息可 reply，讨论持续直到手动结束或全员 PASS。

## 已实现（Iter-4 ~ Iter-6）

### 后端 API (`backend/app/routers/brainstorm.py`)

**会话管理（Iter-4）：**
- `POST /api/inspirations/{id}/brainstorm-sessions` — 创建会话
- `GET /api/inspirations/{id}/brainstorm-sessions` — 会话列表
- `GET /api/brainstorm-sessions/{id}` — 会话详情（含沙箱文件树）
- `PATCH /api/brainstorm-sessions/{id}` — 更新会话（title / status）

**持久连接（Iter-6，当前主路径）：**
- `POST /api/brainstorm-sessions/{id}/connect` — 建立持久 SSE 连接（长驻，一次建立）
- `POST /api/brainstorm-sessions/{id}/inject` — 注入用户消息到引擎队列（立即返回 202）
- `DELETE /api/brainstorm-sessions/{id}/connect` — 优雅关闭持久连接

**遗留端点（Iter-5，DEPRECATED — Iter-7 删除）：**
- `POST /api/brainstorm-sessions/{id}/discuss` — 一次性 SSE 讨论（每条消息单独建立/关闭连接）
- `DELETE /api/brainstorm-sessions/{id}/discuss` — 中止一次性讨论

### 讨论引擎 (`backend/app/services/brainstorm.py`)

**CoolingTimer 状态机：**
```
RUNNING ──(idle >= cooldown_seconds)──────────────────> COOLING_DOWN
COOLING_DOWN ──(new speech / user message)──────────> RUNNING
COOLING_DOWN ──(idle >= cooldown + confirmation)────> CONFIRMING
CONFIRMING ──(new speech / user message)────────────> RUNNING
CONFIRMING ──(idle in state >= confirmation)────────> ENDED
ANY ──(message_count >= max_messages)───────────────> ENDED
```

関鍵行为：
- `heartbeat()` — agent 发言保存入库时调用，重置空闲计时器并递增 message_count
- `keep_alive()` — agent 开始生成时调用，仅重置空闲计时器（不递增 count）。防止 LLM 调用耗时（通常 5-30s）被误判为空闲，错误触发冷却
- `abort()` — 立即切换到 ENDED，供前端 stop 按钮触发

**持久运行模式（`run_persistent()`，Iter-6 主路径）：**
- 进入后常驻，`while not self._abort` 循环等待队列消息
- 空闲 30s 发送 `heartbeat` SSE 防连接超时
- 收到消息 → 保存入库 → 推送 `user_message` SSE → 进入 `_run_rounds()`
- `_run_rounds()` 结束后回到等待状态，连接保持
- 每个 agent 开始发言时调用 `timer.keep_alive()`，防止 LLM 生成期间错误触发冷却

**多轮循环 (`_run_rounds()`)：**
- `while sub_round < MAX_ROUNDS`（MAX_ROUNDS = 8）
- 每轮所有 Agent 顺序发言，全员 PASS → 自然结束（`speeches_this_round == 0`）
- PASS 机制：Agent 回复纯文本 `PASS` → 发送 `agent_pass` SSE，消息不入库
- 检查队列优先级：每轮结束后若 queue 非空则 break，优先处理新消息
- 互动式 Prompt：要求 Agent 针对最新发言回应，可点名反驳、追问；明确禁止重复已有观点
- 每个 Agent 可见完整对话历史（含本轮前序 Agent 的响应），`_load_history` 通过 JOIN 获取真实 agent name
- 支持 abort 中止（后端 `_abort` flag，在每次 token 和每次 agent 发言间检查）

**遗留运行模式（`run()`，DEPRECATED — Iter-7 删除）：**
- 一次性运行，处理单条用户消息，所有轮次结束后 stream 关闭

#### SSE 事件完整列表

| 事件 | 载荷 | 触发时机 |
|------|------|----------|
| `agent_start` | `agent_id, agent_name, agent_number` | Agent 开始生成（显示 typing 气泡）|
| `agent_token` | `agent_id, agent_name, token` | 流式 token |
| `message_done` | `agent_id, agent_name, agent_number, message_id, full_content, parent_message_id, round` | Agent 发言完成并入库 |
| `agent_pass` | `agent_id, agent_name, agent_number` | Agent PASS（清除气泡，不入库）|
| `discussion_end` | `summary, message_count, round` | 本 topic 所有轮次结束（persistent 模式连接保持）|
| `max_reached` | `limit` | 达到消息上限 |
| `error` | `error` | 引擎内部错误 |
| `user_message` | `message_id, content, parent_message_id` | 用户消息已入库（替换前端乐观占位）|
| `round_end` | `round, speeches` | 本轮 agents 发言完毕（连接保持，信息性事件）|
| `heartbeat` | `{}` | 空闲 30s 心跳（防代理层超时断连）|

> 注：`discussion_end` 中 `summary` 字段当前固定为 `null`，Iter-9（异步总结模式）填充。

### 沙箱隔离 (`backend/app/services/sandbox.py`)

- 每个 Brainstorm 会话有独立沙箱目录 `brainstorm-sessions/{id}/`
- 沙箱内可自由读写，项目文件只读

### 数据模型

**`BrainstormSession`（`backend/app/models.py`）：**
- `id` (UUID), `inspiration_id`, `title` (String 200), `status`
- `sandbox_path`, `max_messages`, `cooldown_seconds`, `message_count`
- `summary`, `started_by`, `notification_sent`, `created_at`, `ended_at`

**`Message`（brainstorm 相关字段）：**
- `mode = "brainstorm"`, `brainstorm_session_id`, `parent_message_id`, `round`, `intent`, `truncated`
- `intent` 字段当前未使用（为未来投票策略保留），始终为 `null`

### 消息队列行为

- 用户随时可发送消息，系统忙时前端入队（`queueRef`，UI 显示 badge）
- 消息**逐条发送**（不合并）：每条消息独立触发一次完整的 inject → agent 轮次流程
- 前端乐观更新：发送时立即显示 `temp-{timestamp}` 占位消息；收到 `user_message` 事件后替换为真实 ID

### 前端 Store (`frontend/src/stores/brainstormStore.ts`)

**状态：**
```ts
// 会话
sessions: BrainstormSession[]
activeId: string | null
brainstormMode: boolean
loading: boolean

// 讨论（持久连接模式）
discussionConnected: boolean    // 持久 SSE 连接是否活跃
discussionActive: boolean       // 当前是否有 agent 正在生成内容
activeAgentId / Name / Number   // 当前发言 agent 信息（streaming 期间有值）
discussionMessages: Message[]   // 本次连接累积的消息
streamingContent: string        // 当前 agent 的实时 token 缓冲

// Reply
replyingToId: string | null
replyingToContent: string | null
```

> 注：`discussionConnected` 和 `discussionActive` 共存、语义不同：
> - `discussionConnected`：SSE 连接是否活跃（进入 brainstorm 模式即建立）
> - `discussionActive`：当前是否有 agent 正在生成响应（user_message 事件后 true，discussion_end 后 false）

**方法（Iter-6 主路径）：**
```ts
connectSession(sessionId: string): Promise<void>    // POST /connect，建立持久 SSE
disconnectSession(): void                            // DELETE /connect，关闭连接
injectMessage(sessionId, content, replyToId?): Promise<void>  // POST /inject
setReplyingTo(id, content): void
```

**状态清理时机：**
- `connectSession`：不清空 `discussionMessages`（同一 session 内消息持续累积）
- `activateSession`（切换 session）：清空 `discussionMessages` 及所有讨论状态，防止跨 session 消息污染
- `stopBrainstorm`：清空所有状态，退出 brainstorm 模式

**遗留方法（DEPRECATED — Iter-7 删除）：**
```ts
startDiscussion()  // POST /discuss，one-shot SSE（每次清空 discussionMessages）
stopDiscussion()   // DELETE /discuss
```

### 前端 UI (`frontend/src/components/ChatArea.tsx`)

**连接生命周期：**
- `brainstormMode && brainstormActiveId` → `connectSession`（useEffect，cleanup 调用 `disconnectSession`）
- 发消息 → `injectMessage`（persistent）

**Reply UI：**
- brainstorm 模式下，消息 hover 显示 `↩ Reply` 按钮
- 点击 → `replyingToId` + `replyingToContent` 写入 store
- 输入框上方显示引用条：`↩ 回复 {agent_name} · "{内容前30字}" [✕]`
- 发送时将 `replyingToId` 传入 `injectMessage`

**彩色线程引用预览：**
- `threadColor.ts`：`getRootId(id, messages)` → FNV-1a hash % 360 → `hsl(hue, 45%, 58%)`
- 有 `parent_message_id` 的消息，在气泡内顶部渲染引用预览块（`.chat-message__quote`）：
  - 引用块左侧显示 3px 线程颜色竖线（`borderLeftColor: threadAccent`）
  - 上方一行：被引用消息的发言人名（accent 色，`.chat-message__quote-author`）
  - 下方：被引用内容前 80 字，超出截断加 `…`（`.chat-message__quote-text`，最多 2 行）
- 不在消息外层 div 添加 `borderLeft`（原竖线方案已移除，因对用户不透明）

**RightPanel (`frontend/src/components/RightPanel.tsx`)：**
- Brainstorm Tab：会话详情卡片（title, status, message_count, cooldown）
- Slide toggle 控制 active/ended
- 沙箱文件树展示

**聊天集成：**
- 闪电按钮切换 brainstorm mode
- brainstorm 消息带 `brainstorm_session_id` 过滤
- 会话切换时插入分割线（start/end/transition）
- 顶部 badge 显示当前会话编号

---

## 迭代计划

| 迭代 | 范围 | 状态 |
|------|------|------|
| Iter-4 | 会话沙箱 CRUD | ✅ |
| Iter-5 | 讨论引擎 + SSE（一次性连接） | ✅ |
| Iter-6 | 持久连接 + Reply + 彩色线程 | ✅ |
| Iter-7 | 删除 deprecated 路径 + 读 Tools + 上下文引擎 | ⬜ |
| Iter-8 | 写 Tools + 受限执行器 | ⬜ |
| Iter-9 | 异步自主模式（含 summary 填充）| ⬜ |

---

## 关键接口（当前，Iter-6）

```
POST   /api/brainstorm-sessions/{id}/connect   建立持久 SSE 连接
POST   /api/brainstorm-sessions/{id}/inject    注入用户消息（202）
DELETE /api/brainstorm-sessions/{id}/connect   关闭连接

POST   /api/inspirations/{id}/brainstorm-sessions  创建会话
GET    /api/inspirations/{id}/brainstorm-sessions  会话列表
GET    /api/brainstorm-sessions/{id}               会话详情
PATCH  /api/brainstorm-sessions/{id}               更新会话

[DEPRECATED] POST   /api/brainstorm-sessions/{id}/discuss   一次性 SSE
[DEPRECATED] DELETE /api/brainstorm-sessions/{id}/discuss   中止一次性讨论
```

