# Sloth Agent 桌面版 MVP 实现计划

> Spec: `docs/specs/20260425-mvp-desktop-app-spec.md`
> Arch: `docs/design/desktop-app-architecture.md`
> 日期: 2026-04-25
> 状态: IN PROGRESS

---

## 迭代概览

| 迭代 | 天数 | 范围 | 关键产出 |
|------|------|------|---------|
| Iter-1 | Day 1-3 | 项目外壳 + Inspiration CRUD | 4 列布局 + 数据库 + API |
| Iter-2 | Day 4-6 | 聊天 + 默认 Agent | 消息流 + LLM 集成 |
| Iter-3 | Day 7-9 | Agent 管理 + LLM 配置 | Right Panel + 模型切换 |

---

## Iter-1: 项目外壳 + Inspiration CRUD

### Task 1.1: 后端 — SQLite 数据库 + Inspiration API

**文件：**
- `backend/app/database.py` — SQLAlchemy engine + session
- `backend/app/models.py` — Inspiration 模型
- `backend/app/routers/inspirations.py` — CRUD 路由
- `backend/app/main.py` — 注册路由

**具体工作：**
1. 安装依赖：`sqlalchemy`, `aiosqlite`
2. 创建 `database.py`：`create_async_engine` + `async_session` + `init_db()`
3. 创建 `models.py`：`Inspiration(id, name, created_at, updated_at)`
4. 创建 `routers/inspirations.py`：
   - `POST /api/inspirations` — 创建，JSON body `{name}`
   - `GET /api/inspirations` — 列表，支持 `?q=` 搜索
   - `GET /api/inspirations/{id}` — 单个详情
   - `DELETE /api/inspirations/{id}` — 删除
5. 在 `main.py` 中 `app.include_router(inspirations.router, prefix="/api")`
6. `init_db()` 在 `lifespan` 中调用

**验证：** `uv run uvicorn app.main:app` 启动后用 curl 测试 4 个端点

### Task 1.2: 前端 — 4 列布局外壳

**文件：**
- `frontend/src/App.tsx` — 重写为 4 列布局
- `frontend/src/components/SideNavBar.tsx` — Col1
- `frontend/src/components/ProjectList.tsx` — Col2（静态 UI，无数据）
- `frontend/src/components/ChatArea.tsx` — Col3（空骨架）
- `frontend/src/components/RightPanel.tsx` — Col4（空骨架）
- `frontend/src/App.css` — 布局样式

**具体工作：**
1. 创建 `components/` 目录和上述文件
2. `App.tsx` 改为 flex 横向布局：
   ```
   <div className="app-shell">
     <SideNavBar />    {/* 64px */}
     <ProjectList />   {/* 280px */}
     <ChatArea />      {/* flex: 1 */}
     <RightPanel />    {/* 320px */}
   </div>
   ```
3. `SideNavBar.tsx`：垂直排列，4 个图标按钮占位（Logo + Inspiration + Agents + Settings），底部用户头像
4. `ProjectList.tsx`：顶部"Inspiration"标题 + "+"按钮，搜索框，静态项目列表占位
5. `ChatArea.tsx`：顶部空 TopAppBar，中间空聊天区，底部禁用输入框
6. `RightPanel.tsx`：空 div，等 Iter-3 实现
7. 样式用 CSS（plain CSS，color vars 来自设计 token）

**验证：** `cargo tauri dev` 启动，4 列正确显示，窗口大小正确

### Task 1.3: 前端 — Inspiration CRUD 接入

**文件：**
- `frontend/src/api/client.ts` — `invoke` 封装
- `frontend/src/stores/inspirationStore.ts` — Zustand store
- `frontend/src/components/ProjectList.tsx` — 接入真实数据
- `src-tauri/src/lib.rs` — 添加 CRUD commands

**具体工作：**
1. `src-tauri/src/lib.rs` 添加 Rust commands：
   - `create_inspiration(name)` → reqwest POST 后端
   - `list_inspirations(query)` → reqwest GET 后端
   - `get_inspiration(id)` → reqwest GET 后端
   - `delete_inspiration(id)` → reqwest DELETE 后端
2. 前端 `client.ts`：封装 invoke 调用，统一错误处理
3. `inspirationStore.ts`：
   ```
   interface InspirationStore {
     inspirations: Inspiration[]
     activeId: string | null
     loading: boolean
     fetchAll: () => Promise<void>
     create: (name: string) => Promise<void>
     remove: (id: string) => Promise<void>
     setActive: (id: string) => void
   }
   ```
4. `ProjectList.tsx` 接入 store：
   - "+"按钮 → `create()`，弹出简单 input 或 prompt 输入名称
   - 列表渲染 `inspirations`，点击切换 `activeId`
   - active item 样式：绿色左边框 + 绿色背景
   - 搜索框 onChange → 过滤或重新 fetch `?q=`

**验证：**
- 点击"+"→输入名称→列表中新增
- 点击不同项目→选中态切换
- 搜索→列表过滤
- 重启应用→数据保留

---

## Iter-2: 聊天 + 默认 Agent

### Task 2.1: 后端 — Agent 模型 + LLM 服务

**文件：**
- `backend/app/models.py` — 新增 Agent, Message 模型
- `backend/app/services/llm.py` — LLM 调用封装
- `backend/app/services/agent.py` — Agent 逻辑

**具体工作：**
1. 更新 `models.py`：
   - `Agent(id, inspiration_id, name, role, model, status, created_at)`
   - `Message(id, inspiration_id, agent_id, role, content, created_at)`
2. 创建 `services/llm.py`：
   - `LLMService` 类：构造函数读 `config.json` 获取 API key + base_url
   - `chat(messages, model)` — 非流式调用
   - `chat_stream(messages, model)` — 流式调用（async generator）
3. 创建 `services/agent.py`：
   - `AgentService` 类
   - `get_or_create_default(inspiration_id)` — 确保每个 Inspiration 有默认 Agent
   - 创建 Inspiration 时自动调用
4. `database.py`：新增 `init_db()` 自动建表（Agent, Message）

**验证：** 
- 创建 Inspiration → 自动生成默认 Agent（gpt-4o）
- 手动调用 `chat_stream()` → 收到流式 tokens

### Task 2.2: 后端 — 聊天 API + SSE 流式

**文件：**
- `backend/app/routers/chat.py` — 聊天路由
- `backend/app/main.py` — 注册路由

**具体工作：**
1. `routers/chat.py`：
   - `POST /api/inspirations/{id}/chat` — 发送消息，返回完整回复
     - 保存用户消息到 Message 表
     - 加载历史消息作为上下文
     - 调用 Agent LLM
     - 保存 Agent 回复
     - 返回 `{message: ..., agent_id: ...}`
   - `POST /api/inspirations/{id}/chat/stream` — SSE 流式
     - `StreamingResponse` with `text/event-stream`
     - 逐 token 推送 `data: {"token": "..."}\n\n`
     - 最后推送 `data: [DONE]\n\n`
   - `GET /api/inspirations/{id}/messages` — 消息历史
     - 返回 `{messages: [...]}`
     - 支持 `?limit=` 和 `?before=` 分页
2. 在 `main.py` 注册 `chat.router`

**验证：**
- `curl -X POST /api/inspirations/{id}/chat` → 返回完整回复
- `curl -N -X POST /api/inspirations/{id}/chat/stream` → 看到逐行 SSE 数据
- 消息持久化到 SQLite

### Task 2.3: 前端 — Chat UI + 流式展示

**文件：**
- `frontend/src/components/ChatArea.tsx` — 重写完整 Chat
- `frontend/src/components/ChatMessage.tsx` — 消息气泡
- `frontend/src/components/ChatInput.tsx` — 输入区
- `frontend/src/stores/chatStore.ts` — Zustand 聊天状态
- `src-tauri/src/lib.rs` — 添加 chat commands

**具体工作：**
1. Rust commands：
   - `send_message(inspiration_id, content)` → POST 后端（非流式先跑通，再换 SSE）
   - `get_messages(inspiration_id)` → GET 后端
2. 流式方案：
   - 因为 Tauri invoke 不适合 SSE 流（经过 Rust→reqwest→invoke 会缓冲）
   - 方案：Rust `reqwest` 读 SSE stream → 通过 `app.emit()` 推事件到前端
   - 前端用 `listen('chat-token', ...)` 接收
3. `chatStore.ts`：
   ```
   interface ChatStore {
     messages: Message[]
     streaming: boolean
     currentStreamContent: string
     sendMessage: (inspirationId: string, content: string) => Promise<void>
     loadMessages: (inspirationId: string) => Promise<void>
   }
   ```
4. `ChatMessage.tsx`：
   - `role === "agent"` → 灰色气泡，左侧，圆角 `2px 16px 16px 16px`，带头像 + 名称
   - `role === "human"` → 绿色边框气泡，右侧，圆角 `16px 16px 2px 16px`
   - `role === "system"` → 居中灰色小字
   - 流式消息：内容逐字追加，最后追加到 messages 列表
5. `ChatInput.tsx`：
   - 输入框 placeholder "Message Agents or Team..."
   - 绿色发送按钮（圆形）
   - Enter 发送，Shift+Enter 换行
   - 发送中按钮 disabled
6. `ChatArea.tsx` 组合：
   - TopAppBar：Inspiration 名称 + MVP 标签 + "2 ACTIVE" 状态
   - Chat Canvas：可滚动消息列表
   - ChatInput 固定在底部

**验证：**
- 输入消息→发送→消息出现在气泡中
- Agent 回复流式展示
- 历史消息加载正常
- 不同 Inspiration 的消息隔离

---

## Iter-3: Agent 管理 + LLM 配置

### Task 3.1: 后端 — Agent CRUD API

**文件：**
- `backend/app/routers/agents.py` — Agent 路由

**具体工作：**
1. `routers/agents.py`：
   - `GET /api/inspirations/{id}/agents` — Agent 列表
   - `POST /api/inspirations/{id}/agents` — 添加 Agent
     - body: `{name, role, model}`
   - `PATCH /api/agents/{id}` — 修改模型配置
     - body: `{model}`
   - `DELETE /api/agents/{id}` — 删除 Agent
2. 模型列表从配置文件读取（或硬编码 3 个常用模型）
3. 在 `main.py` 注册路由

**验证：**
- 创建 Agent → 返回 Agent 对象
- 修改模型 → PATCH 生效
- 删除 → 列表不再显示

### Task 3.2: 前端 — Right Panel Agent 管理

**文件：**
- `frontend/src/components/RightPanel.tsx` — 完整实现
- `frontend/src/components/AgentListItem.tsx` — 单个 Agent 项
- `frontend/src/stores/agentStore.ts` — Zustand Agent 状态
- `src-tauri/src/lib.rs` — 添加 agent commands

**具体工作：**
1. Rust commands：
   - `list_agents(inspiration_id)` → GET 后端
   - `add_agent(inspiration_id, name, role, model)` → POST 后端
   - `update_agent_model(agent_id, model)` → PATCH 后端
   - `delete_agent(agent_id)` → DELETE 后端
2. `agentStore.ts`：
   ```
   interface AgentStore {
     agents: Agent[]
     loading: boolean
     fetchAll: (inspirationId: string) => Promise<void>
     add: (inspirationId: string, name: string, model: string) => Promise<void>
     updateModel: (agentId: string, model: string) => Promise<void>
     remove: (agentId: string) => Promise<void>
   }
   ```
3. `RightPanel.tsx`：
   - Header："Team" + 全局模型选择器
   - COLLABORATORS 分区（MVP 只显示当前用户头像 + 绿色 dot）
   - AGENTS 分区：
     - "AGENTS" 标题 + "N Active" 计数
     - Agent 列表（AgentListItem 组件）
     - 底部虚线按钮"Add Agent"
4. `AgentListItem.tsx`：
   - 头像（带角色图标）
   - 名称 + 状态灯（绿 working / 灰 idle / 半绿半灰 active）
   - 模型选择下拉框
5. Chat 中 Agent 状态联动：
   - 发送消息 → Agent 状态变为 working
   - 回复完成 → Agent 状态变为 idle

**验证：**
- Right Panel 显示 Agent 列表
- 下拉切换模型 → 新对话使用新模型
- 添加 Agent → 成功
- 聊天时状态灯变化

---

## 跨迭代关注

### 端口与进程管理
- 后端固定使用 `127.0.0.1:8080`
- Tauri 启动前 `taskkill` 清理残留 uvicorn
- Sidecar 崩溃检测：前端定时 health check + 自动重启提示

### 测试策略
- 每个后端 router 至少 1 个集成测试
- 前端不写测试（MVP 阶段）
- 每个迭代结束时手动 smoke test（对照验收标准）

### 提交策略
- 每个 Task 完成即提交（atomic commits）
- 迭代结束时打 tag（`v0.4.0-iter1`, `v0.4.0-iter2`, `v0.4.0-iter3`）

---

*Plan 版本: 1.0 — 2026-04-25*
