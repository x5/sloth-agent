# Brainstorm 模式

> 归档参考: archive/initial-specs/20260430-brainstorm-mode-spec.md
> 最后更新: 2026-05-02 (brainstorm-fluid-discussion)
> Iter-4 完成: 2026-05-01
> Iter-5 完成: 2026-05-01

## 概述

多 Agent 多轮讨论模式。用户发起话题，Expert Agent 循环发言、互相回应、反驳、追问，直到所有 Agent 均无新内容（全员 PASS）时自然结束。每个 Agent 实时流式响应，可见完整对话历史。所有产出写入隔离沙箱，项目文件零风险。

## 已实现

### 后端 API (`backend/app/routers/brainstorm.py`)

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
