# Sloth Agent 桌面版 MVP 实现计划

> Spec: `docs/specs/desktop/app/spec.md`
> Brainstorm Spec: `docs/specs/core/brainstorm/spec.md`
> Arch: `docs/design/desktop-app-architecture.md`
> 日期: 2026-04-25
> 更新: 2026-05-04
> 状态: IN PROGRESS

---

## 共享核心迁移说明

> 详细设计见 `docs/specs/architecture/spec.md` — "共享核心层（Shared Core）"
>
> **判断标准：** 任何 CLI 和 Desktop 都需要、且业务逻辑一致的能力，放入 `src/sloth_agent/core/`。只有 SSE 传输、SQLite 持久化、HTTP 路由、前端 UI 留在 Desktop 适配层。

`src/sloth_agent/` 中以下模块为"共享安全（shared-safe）"，Desktop（backend）直接 import，不重建：

| 模块 | 能力 | Desktop 应用位置 |
|------|------|------------------|
| `sloth_agent.core.token_counter.TokenCounter` | token 计数（tiktoken + 字符回退） | `sloth_agent.core.context.engine.ContextEngine` 内部 |
| `sloth_agent.core.context_window.ContextWindowManager` | 预算截断 + 摘要压缩 + 消息链保护 | `sloth_agent.core.context.engine.ContextEngine`（扩展） |
| `sloth_agent.providers.llm_providers.BaseLLMProvider` + 具体实现 | LLM 调用抽象 | `backend/app/shared/llm_adapter.py`（包装） |
| `sloth_agent.providers.llm_router.LLMRouter` | 按 agent 路由 + 熔断 | `backend/app/shared/llm_adapter.py`（按需接入） |
| `sloth_agent.core.tools.ToolPool` + `@tool` + `ToolDef` + `ToolContext` | 工具装饰器 + 注册表 + 路径沙箱 | `backend/app/services/brainstorm.py`（直接 import） |
| `sloth_agent.core.tools.builtin.readonly_fs` | 6 只读文件系统工具 | import 即注册，brainstorm 引擎自动可用 |
| `sloth_agent.core.agents.role_tools.ROLE_BASE_TOOLS` | role → 工具名列表 | `backend/app/services/agent.py`（effective_tools 计算） |
| `sloth_agent.core.agents.template.AgentTemplate` | Agent 模板纯数据类（无 DB） | Desktop ORM 映射/继承 |
| `sloth_agent.core.brainstorm.tool_loop.run_tool_loop` | function calling 调用循环 | `backend/app/services/brainstorm.py`（委托） |
| `sloth_agent.core.context.engine.ContextEngine` | 三段上下文构建 + diagnostics | `backend/app/services/context.py`（适配器） |

**迁移优先级（按 Iter）：**
- Iter-7（当前）：新建 `llm_adapter.py` 包装 `BaseLLMProvider`；将 Tool 系统、角色工具绑定、Function Calling 循环、ContextEngine 全部实现在 core 层；Desktop 退化为薄适配层。
- Iter-8 及后：写 Tools（write/patch/exec）按需评估放入 core 还是 Desktop 沙箱层；其他共享能力按需接入，原有重复实现逐步删除。

**path dependency 规则：**
`backend/pyproject.toml` 添加 `"sloth-agent @ file:///../"`，backend 只 import 上表模块，禁止 import `sloth_agent.cli.*` 或 CLI 专属运行时。

---

## 迭代概览

| 迭代 | 天数 | 范围 | 关键产出 |
|------|------|------|---------|
| Iter-1 | Day 1-3 | 项目外壳 + Inspiration CRUD | 4 列布局 + 数据库 + API | ✅ |
| Iter-2 | Day 4-7 | Settings + 聊天 + 默认 Agent | LLM 管理页 + 消息流 + SSE 流式 | ✅ |
| Iter-3 | Day 8-14 | Agent Pool 初始化 + Agent 管理 + Right Panel | 5 内置 Agent + Team API + Right Panel 团队面板 | ✅ |
| Iter-4 | Day 15-17 | Brainstorm 会话沙箱 | SandboxManager + BrainstormSession CRUD + 前端列表 | ✅ |
| Iter-5 | Day 18-20 | 讨论引擎 — 两轮投票 + SSE | BrainstormEngine + DecisionStrategy + CoolingTimer | ✅ |
| Iter-6 | Day 21-24 | 持久连接 + Reply + 彩色线程 | queue-driven Engine + connect/inject 端点 + Reply UI + 线程竖线 | ✅ |
| Iter-7 | Day 24-26 | Tool 系统 + 上下文引擎 | `core` 层：@tool 装饰器 + 6 只读工具 + ROLE_BASE_TOOLS + run_tool_loop + ContextEngine；Desktop 薄适配层接线 | ✅ |
| Iter-8 | Day 27-32 | 写 Tools + Toolset 抽象 + Agent 对象模型 + eval | 写 Tools + tool-whitelist.yaml + SandboxFileViewer + 受限网络工具 + **Phase A: Pydantic schema + BaseToolset + AgentConfig + model 继承链 + eval: 读/写工具能力评估** | ⬜ |
| Iter-9 | Day 33-37 | 异步自主模式 + Hooks 系统 + eval | start-async + 断线恢复 + 浏览器通知 + **Phase B: HookManager(8 种 HookPoint) + tool/agent hook 接入 + eval: 自主讨论质量评估** | ⬜ |
| Iter-10 | Day 38-43 | events 全量 + Agent 树 + transfer + eval | **EventBus(CloudEvents/通配符订阅/持久化/DLQ) + EventHandler + WorkflowRule + AgentTreeManager + TransferToAgentTool + eval: Agent 协作评估** | ⬜ |
| Iter-11 | Day 44-49 | coordination 全量 + delta state + Agent-as-Tool + YAML + rewind + eval | **Coordinator(TaskDAG) + LaneManager + MessageBus + WorktreeManager + 失败恢复 + Session delta state + Runner 重构 + Agent-as-Tool + YAML from_config + Session rewind + eval: 编排效率评估** | ⬜ |
| Iter-12 | Day 50-54 | Memory Foundation | **Ingest pipeline + Consolidation tiers (Working→Episodic→Semantic) + Confidence scoring (Ebbinghaus) + Hybrid search (BM25+vector) + Context injection** | ⬜ |
| Iter-13 | Day 55-59 | Memory Advanced | **Knowledge graph (entity+relations+graph traversal) + Supersession + Crystallization (Brainstorm→digest→wiki) + Procedural memory + Self-healing/lint + Event-driven automation** | ⬜ |
| Iter-14+ | 待定 | eval 体系化 + errors + cost + observability + sandbox + plugin + pipeline + A2A | 剩余候选池模块 | ⬜ |

> **变更来源（2026-05-07）:**
> - `docs/changes/adk-optimization/` — ADK 对标分析，Iter-8~14+ 路线图
> - `docs/changes/memory-architecture/` — Memory 架构重设计（参考 ADK + Karpathy LLM Wiki + agentmemory），Iter-12+13 两队

> **变更来源:** `docs/changes/adk-optimization/` — Google ADK 对标分析。
> Iter-8~9 在原计划基础上叠加 Phase A/B，Iter-10~11 为全新规划，Iter-12+ 为候选池。
> 详细任务见 `docs/changes/adk-optimization/tasks.md`

---

---

## 核心关系模型

```
Sloth (Global Application)
│
├─ LLM Providers Pool     (Settings → LLM tab)
│   ├─ DeepSeek V4 Pro  ← 默认
│   ├─ Qwen Max
│   └─ OpenAI GPT-4o
│
├─ Agents Pool            (Settings → Agents tab, 或 SideNav "Agents")
│   └─ Lead Agent        ← Sloth 自带, 唯一默认 Agent 模板
│        name: "Lead Agent"
│        role: "lead"
│        model: DeepSeek V4 Pro  ← 继承 Sloth 默认 LLM
│        │
│        │  创建 Inspiration 时, 从 Pool 自动加入其 Team
│        ▼
└─ Inspiration "My Project"
    └─ Team (RightPanel)
         └─ Lead Agent  ← 由 Sloth Agents Pool 拉入
              └─ 可在 Team 面板切换到 Qwen Max / GPT-4o
```

**规则：**
1. Sloth 全局管理两个池子：LLM Providers 池 和 Agents 池
2. Agents Pool 目前只有一个 Lead Agent，未来可扩展多个 Agent 模板
3. 创建 Inspiration 时 → 从 Agents Pool 拉取 Lead Agent 自动加入该 Inspiration 的 Team（不新建 Agent 记录，而是创建关联）
4. Lead Agent 默认使用 Sloth 的默认 LLM
5. Agent 的模型可在 Team 面板中从 Sloth LLM 池任选
6. 删除 LLM Provider 时，使用该 LLM 的 Agent 回退到默认 LLM

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

## Iter-1 Polish: UI 优化 (来自 QA 验证反馈)

> 来源: `docs/qa/iter-1-verification-report.txt` (2026-04-26)
> 优先级: 与 Iter-2 并行进行

### Task 1.4: 创建 Inspiration 交互优化

**文件：** `frontend/src/components/ProjectList.tsx`

**当前问题：** `prompt()` 弹窗体验差，无法用 Escape 取消

**前端展现：**

```
┌──────────────────────────────┐
│ Inspiration              [+] │  ← header
├──────────────────────────────┤
│ ┌──────────────────────────┐ │  ← 点击 + 后插入的输入行 (slideDown 150ms)
│ │ New inspiration name...  │ │  ← input, auto-focus, 13px, 圆角 8px
│ └──────────────────────────┘ │    bg: #f3f3f3, border: 1px solid transparent
│  Cancel        Create        │  ← 按钮行: Cancel(灰色) + Create(accent色)
├──────────────────────────────┤    右对齐, gap 8px, 12px 字号
│ [AV] Amazing Project  2h ago│  ← 列表项不受影响
└──────────────────────────────┘
```

**交互规格：**
1. 点击 "+" → 列表顶部插入输入行（`max-height` transition, 150ms ease）
2. `<input>` 自动聚焦，placeholder `"New inspiration name..."`
3. Enter → `create(name.trim())`，成功后输入行收起，新项顶部高亮
4. Escape → 取消，输入行收起，清空输入
5. 空名称提交 → input border 变红 `#ff3b30` + shake 动画 300ms，不关闭
6. 提交中 → Create 按钮显示 spinner，input disabled
7. 点击 "+" 再次 → 如果已有展开的输入行，聚焦到它（不创建第二个）

---

### Task 1.5: 列表项 UI 优化

**文件：** `frontend/src/components/ProjectList.tsx` + `App.css`

**4 项改动：**

#### a) 副标题替换
```
当前: "Click to open"
改为: 显示相对创建时间，如 "Created 2h ago"
      formatTime(p.created_at)，不再显示 updated_at
```

#### b) 头像 hash 颜色
```
当前: 灰色背景 #eee，active 时变蓝
改为: 从 name 生成一致的颜色

算法:
  const H = name.split('').reduce((s, c) => s + c.charCodeAt(0), 0) % 360;
  非 active: bg hsl(H, 30%, 88%)  text hsl(H, 30%, 35%)
  active:    bg hsl(H, 50%, 90%)  text hsl(H, 40%, 30%)

  CSS: style={{ background: `hsl(${H}, 30%, 88%)`, color: `hsl(${H}, 30%, 35%)` }}
```

#### c) 头像尺寸/间距
```
当前: 36×36, 文字 16px
改为: 32×32, 文字 12px, font-weight 600
      padding: item 间距从 12px → 10px 12px
```

#### d) 列表项间距
```
当前: gap: 8px (ProjectList list)
改为: gap: 10px
```

---

### Task 1.6: 搜索自动补全

**文件：** `frontend/src/components/ProjectList.tsx`

**前端展现：**

```
┌──────────────────────────────┐
│ 🔍 [Amaz__________________] │  ← search input (现有)
├──────────────────────────────┤
│ ┌──────────────────────────┐ │  ← dropdown overlay
│ │ ◆ Amazing Project  2h ago│ │    绝对定位, z-index: 10
│ │ ◆ Amazon Clone     5h ago│ │    bg: #fff, border-radius: 8px
│ │                          │ │    box-shadow: 0 4px 16px rgba(0,0,0,0.1)
│ └──────────────────────────┘ │    max-height: 240px, overflow-y: auto
│                              │
│ [AV] Amazing Project  2h ago│  ← 列表项在下方
└──────────────────────────────┘

  无匹配时:
│ ┌──────────────────────────┐ │
│ │ No results               │ │  ← 灰色文字, 居中
│ └──────────────────────────┘ │
```

**交互规格：**
1. 输入 ≥1 字符 → 下拉出现（本地过滤 `inspirations`，不调 API）
2. 每行：20×20 头像 + name + 右侧时间（10px #9ea7b0）
3. 匹配文字高亮 `<mark>` 黄色背景 `rgba(255,204,0,0.3)`
4. 点击行 → `setActive(id)` + 清空搜索 + 关闭下拉
5. **键盘导航：**
   - ↑↓ 切换高亮行（`.autocomplete-item--highlighted`，bg: `--color-accent-bg`）
   - Enter 选中高亮行
   - Escape 关闭下拉，保留搜索文字
6. 点击外部区域 → 关闭下拉（document click listener）
7. 搜索为空时下拉隐藏
8. 不显示当前已 active 的项（或标记为 active）

---

### Task 1.7: 窗口最小宽度

- `tauri.conf.json` 已设置 `minWidth: 640, minHeight: 480`（需要重新编译 exe 生效）
- CSS 已加固 ChatArea header 防挤压

---

## Iter-2: Col1 导航 + LLM 设置 + Agent 详情 + 聊天

> 核心链路: Settings → LLM Provider CRUD → Lead Agent 绑定默认 LLM → 创建 Inspiration → Lead Agent 自动加入 Team → 聊天

---

### Col1 驱动的 Master-Detail 导航模型

Col1 (SideNavBar) 的按钮决定 Col2 和 Col3 的内容：

```
Col1 (64px)      Col2 (280px)           Col3 (flex: 1)
─────────        ────────────           ────────────
Inspiration  →   Inspiration 列表    →  Chat
                 (搜索 + 筛选)           (消息流 + 输入)

Agents       →   Agent Pool 列表     →  Agent 详情
                 (Lead Agent)            (名称/角色/模型/提示词)

Settings     →   设置分类列表        →  LLM Provider CRUD
                 (LLM Providers)         (卡片列表 + 行内添加/编辑)
```

**规则：**
- Col2 始终显示当前 `activeNav` 对应的项列表
- Col3 始终显示 Col2 中选中项的详情
- 切换 Col1 → Col2 刷新为对应列表，Col3 显示默认选中项
- Col4 (RightPanel) 只在 Inspiration 下打开，显示 Team
- `uiStore.activeNav` 驱动全局: `"inspiration"` | `"agents"` | `"settings"`

**app-shell 伪代码：**
```tsx
function App() {
  const activeNav = useUIStore(s => s.activeNav);
  return (
    <div className="app-shell">
      <SideNavBar />
      <div className="app-main">
        {activeNav === "inspiration" && <><ProjectList /><ChatArea /></>}
        {activeNav === "agents"     && <><AgentPoolList /><AgentDetail /></>}
        {activeNav === "settings"   && <><SettingsNav /><SettingsDetail /></>}
      </div>
      {col4Open && <RightPanel />}
    </div>
  );
}
```

---

### Task 2.0: 前端 — Agents 导航 + Settings 导航 (LLM CRUD)

**前置条件：** 聊天需要 LLM 才能工作，Settings 必须先于 Chat 实现

**涉及文件：**
- `frontend/src/components/SideNavBar.tsx` — 按钮激活 + 切换 activeNav
- `frontend/src/components/AgentPoolList.tsx` — Col2: Agent 池列表 (NEW)
- `frontend/src/components/AgentDetail.tsx` — Col3: Agent 详情 (NEW)
- `frontend/src/components/SettingsNav.tsx` — Col2: 设置分类列表 (NEW)
- `frontend/src/components/SettingsDetail.tsx` — Col3: LLM Provider CRUD (NEW)
- `frontend/src/stores/llmStore.ts` — LLM Provider 状态 (NEW)
- `frontend/src/stores/agentPoolStore.ts` — Agent 池状态 (NEW)
- `frontend/src/stores/uiStore.ts` — 新增 activeNav 状态
- `frontend/src/App.tsx` — 条件渲染 Col2+Col3
- `src-tauri/src/lib.rs` — 添加 LLM config + agent template commands

---

#### 2.0a: 导航 — Agents 视图

**Col2 — AgentPoolList：**

```
┌──────────────────────────────┐
│ Agents                   [+] │  ← header, [+] disabled (MVP)
├──────────────────────────────┤
│ 🔍 Search agents...          │  ← 搜索框 (MVP disabled)
├──────────────────────────────┤
│ ┌──────────────────────────┐ │
│ │ 🤖 Lead Agent            │ │  ← 唯一项, 默认选中
│ │    lead                   │ │    头像 36×36 + 名字 + role
│ │    Default LLM            │ │    副标题: 当前使用的模型名
│ └──────────────────────────┘ │
│                              │
└──────────────────────────────┘
```

- 只有一个条目：Lead Agent，默认选中状态（active 高亮）
- 头像用 role hash 色
- 副标题显示当前绑定的默认 LLM 模型名

**Col3 — AgentDetail：**

```
┌──────────────────────────────────────────────────┐
│ Lead Agent                                       │  ← header
├──────────────────────────────────────────────────┤
│                                                  │
│  Profile                                         │
│  ───────                                         │
│                                                  │
│  Name                                             │
│  ┌──────────────────────────────────────────────┐ │
│  │ Lead Agent                                   │ │  ← 可编辑 (MVP disabled)
│  └──────────────────────────────────────────────┘ │
│                                                  │
│  Role                          [lead] badge      │  ← 只读
│                                                  │
│  Default Model                                    │
│  ┌──────────────────────────────────────────────┐ │
│  │ DeepSeek V4 Pro                        ▾    │ │  ← 从 LLM 池选择
│  └──────────────────────────────────────────────┘ │    保存后所有新 Inspiration
│                                                  │    的 Lead Agent 使用此模型
│  System Prompt                                    │
│  ┌──────────────────────────────────────────────┐ │
│  │ You are Sloth's Lead Agent, a general-       │ │  ← textarea, min 4 rows
│  │ purpose AI assistant. You help users         │ │
│  │ build software projects from idea to         │ │
│  │ production...                                │ │
│  └──────────────────────────────────────────────┘ │
│                                                  │
│  Auto-Join                                        │
│  [✓] 创建新 Inspiration 时自动加入其 Team         │  ← checkbox, checked (MVP)
│                                                  │
│                    [Save Changes]                 │
│                                                  │
└──────────────────────────────────────────────────┘
```

- Model 下拉从 Sloth LLM 池读取选项
- System Prompt 可编辑，提供默认模板
- Save 按钮保存后更新 AgentTemplate 记录
- MVP: Name/Role/Auto-Join 只读

---

#### 2.0b: 导航 — Settings 视图

**Col2 — SettingsNav：**

```
┌──────────────────────────────┐
│ Settings                     │
├──────────────────────────────┤
│ ┌──────────────────────────┐ │
│ │ ⚡ LLM Providers         │ │  ← 唯一分类项, 默认选中
│ │    Configure AI backends │ │    副标题: 说明
│ └──────────────────────────┘ │
│                              │
│ ┌──────────────────────────┐ │
│ │ 🔧 General        (soon) │ │  ← disabled, 未来扩展
│ └──────────────────────────┘ │
│                              │
│ ┌──────────────────────────┐ │
│ │ ℹ About           (soon) │ │  ← disabled, 未来扩展
│ └──────────────────────────┘ │
└──────────────────────────────┘
```

- MVP 只有一个可用的设置分类："LLM Providers"
- 默认选中
- 其他分类显示为 disabled 占位

**Col3 — SettingsDetail (LLM Provider CRUD)：**

```
┌──────────────────────────────────────────────────┐
│ LLM Providers                                    │  ← header
├──────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────────────────────────────────────┐    │
│  │ 🟢 DeepSeek V4 Pro          [Default]    │    │  ← 默认 LLM, 绿色标记
│  │    deepseek-v4-pro                        │    │
│  │    API Key: sk-****abcd           [Edit]  │    │  ← 点击 Edit 展开行内编辑
│  │    Base URL: https://api.deepseek.com     │    │
│  └──────────────────────────────────────────┘    │
│                                                  │
│  ┌──────────────────────────────────────────────┐ │
│  │ ⚪ Qwen Max                    [Set Default] │ │  ← 非默认, 可设默认
│  │    qwen3-max                                 │ │
│  │    API Key: sk-****wxyz              [Edit]  │ │
│  │    Base URL: https://dashscope.aliyuncs.com  │ │
│  │                                  [Delete]    │ │  ← 非默认可删除
│  └──────────────────────────────────────────────┘ │
│                                                  │
│  ┌──────────────────────────────────────────────┐ │
│  │ ⚪ OpenAI GPT-4o               [Set Default] │ │
│  │    gpt-4o                                    │ │
│  │    API Key: (not set)                [Edit]  │ │
│  │    Base URL: https://api.openai.com          │ │
│  │                                  [Delete]    │ │
│  └──────────────────────────────────────────────┘ │
│                                                  │
│  ─── Add LLM Provider ───                        │  ← 点击展开行内添加表单
│                                                  │
└──────────────────────────────────────────────────┘
```

**LLM Provider 卡片规格：**
- 圆角 12px，border `--border-default`，padding 16px 20px
- 左侧状态圆点：🟢 默认 / ⚪ 非默认
- Provider 名称 + Model 名：14px font-weight 600
- API Key 显示脱敏（前 4 位 + `****` + 后 4 位）
- "Set as Default" 按钮（非默认项显示，ghost 样式，点击即切换）
- 默认 LLM 不可删除，非默认项悬停显示 Delete

**行内添加（替代 Modal）：**

点击 "Add LLM Provider" → 在列表底部展开行内表单（不再用弹窗）：

```
│  ─── Add LLM Provider ─── (点击后)           │
│  ┌──────────────────────────────────────────┐ │
│  │ Provider: [DeepSeek ▾]                   │ │
│  │ API Format: [openai ▾]                   │ │  ← openai / anthropic
│  │ Model:    [deepseek-v4-pro ▾]            │ │
│  │ API Key:  [_________________________👁]  │ │
│  │ Base URL: [https://api.deepseek.com    ] │ │
│  │                                          │ │
│  │                [Cancel]    [Save]        │ │
│  └──────────────────────────────────────────┘ │
```

**行内添加交互：**
- 选择 Provider → 自动填充 Base URL + 推荐 Model
- Save → 验证 → POST 后端 → 列表新增 → 表单收起
- Cancel / Escape → 表单收起
- 默认为第一个 LLM 时自动标为 default

**行内编辑（点击 Edit）：**
- 卡片内的 API Key / Base URL 变为可编辑 input
- Edit 按钮变为 Save + Cancel
- 不弹窗，就地修改

**Provider 预设表（内置）：**

| Provider | API Format | Base URL | 推荐模型 |
|----------|-----------|----------|---------|
| DeepSeek | openai | https://api.deepseek.com | deepseek-v4-pro |
| Qwen | openai | https://dashscope.aliyuncs.com/compatible-mode/v1 | qwen3-max |
| OpenAI | openai | https://api.openai.com/v1 | gpt-4o |
| Kimi | openai | https://api.moonshot.cn/v1 | kimi-k2.5 |
| GLM | openai | https://open.bigmodel.cn/api/paas/v4 | glm-5.1 |
| MiniMax | openai | https://api.minimax.chat/v1 | minimax-m2.7 |
| Anthropic | anthropic | https://api.anthropic.com | claude-sonnet-4-6 |
| Custom | openai | (用户填写) | (用户填写) |

**默认模型：** Sloth 内置默认 LLM 为 **DeepSeek V4 Pro** (`deepseek-v4-pro`, OpenAI 兼容格式)

**API 格式路由规则：**
- `api_format = "openai"` → `POST {base_url}/chat/completions`，请求体和 SSE 流用 OpenAI 格式
- `api_format = "anthropic"` → `POST {base_url}/messages`，请求体和 SSE 流用 Anthropic Messages 格式
- `LLMService` 根据 `api_format` 字段构造不同的 HTTP 请求体和解析不同的响应格式
- MVP 阶段所有内置 Provider 都用 `openai` 格式（覆盖面最广）

---

**llmStore 状态：**
```typescript
interface LLMStore {
  providers: LLMConfig[]
  loading: boolean
  fetchAll: () => Promise<void>
  add: (data: { provider, model, api_key, base_url }) => Promise<void>
  update: (id: string, data: Partial<LLMConfig>) => Promise<void>
  remove: (id: string) => Promise<void>
  setDefault: (id: string) => Promise<void>
}
```

**agentPoolStore 状态：**
```typescript
interface AgentPoolStore {
  templates: AgentTemplate[]
  loading: boolean
  fetchAll: () => Promise<void>
  update: (id: string, data: Partial<AgentTemplate>) => Promise<void>
}
```

---

### Task 2.1: 后端 — LLM 配置存储 + Agent 模型 + LLM 服务

**文件：**
- `backend/app/models.py` — 新增 LLMConfig, Agent, Message 模型
- `backend/app/database.py` — `init_db()` 建表
- `backend/app/routers/llm.py` — LLM 配置 CRUD API (NEW)
- `backend/app/services/llm.py` — LLM 调用封装
- `backend/app/services/agent.py` — Agent 逻辑 + 自动创建

**数据模型：**

```python
# LLMConfig — Sloth 全局 LLM Provider 池
class LLMConfig(Base):
    id: str (uuid)
    provider: str       # deepseek / qwen / openai / kimi / glm / minimax / custom
    model: str          # deepseek-v4-pro / gpt-4o / ...
    api_key: str        # 加密存储 (MVP 阶段明文, 后续用 keyring)
    base_url: str       # https://api.deepseek.com
    api_format: str     # "openai" | "anthropic" — API 格式
    is_default: bool    # 是否默认 LLM
    created_at: datetime

# AgentTemplate — Sloth 全局 Agent 池（模板表）
class AgentTemplate(Base):
    id: str (uuid)
    name: str           # "Lead Agent"
    role: str           # "lead" / "reviewer" / "builder" / ...
    default_model: str  # 默认使用的模型名 "deepseek-v4-pro"
    auto_join: bool     # 创建 Inspiration 时是否自动加入其 Team
    system_prompt: str  # 系统提示词（可为空，MVP 用默认值）
    created_at: datetime

# InspirationAgent — Inspiration 的 Team 成员（关联表）
# 表示 Agent Pool 中的某个 Agent 被拉入了某个 Inspiration
class InspirationAgent(Base):
    id: str (uuid)
    inspiration_id: str (FK → inspirations)
    template_id: str (FK → agent_templates)  # 来源 Agent 模板
    name: str           # 可覆盖模板名称（MVP 用模板名）
    model: str          # 该 Inspiration 中实际使用的模型，可独立切换
    status: str         # "idle" / "working" / "error"
    joined_at: datetime

# Message — 聊天消息
class Message(Base):
    id: str (uuid)
    inspiration_id: str (FK → inspirations)
    agent_id: str (FK → inspiration_agents)   # 哪个 Agent 发的
    role: str           # "human" / "agent" / "system"
    content: str
    created_at: datetime
```

**关键设计：**
- `AgentTemplate` 是 Sloth 全局所有，不受 Inspiration 影响
- `InspirationAgent` 是 Agent Template 在某个 Inspiration 中的实例，可以独立切换 model
- 创建 Inspiration 时 → 查询所有 `auto_join=true` 的 AgentTemplate → 为每个创建 `InspirationAgent` 记录
- MVP 只有一个 Lead Agent `auto_join=true`，所以每个新 Inspiration 的 Team 里只有它

**LLM Config API (`routers/llm.py`)：**
- `GET /api/settings/llm` — 返回所有 LLM Provider 列表
- `POST /api/settings/llm` — 添加 LLM Provider (`{provider, model, api_key, base_url}`)
  - 如果是第一个 LLM，自动设为默认
- `PATCH /api/settings/llm/{id}` — 更新 Provider 配置
- `DELETE /api/settings/llm/{id}` — 删除（默认 LLM 不可删，除非只剩一个）
- `PUT /api/settings/llm/{id}/default` — 设为默认（取消其他默认标记）

**Agent Template API (`routers/agent_templates.py`)：**
- `GET /api/settings/agents` — 返回 Agent 池中所有模板
- `POST /api/settings/agents` — 添加 Agent 模板（MVP 禁用，只有 Lead Agent）
- `PATCH /api/settings/agents/{id}` — 更新模板（名称/默认模型/system_prompt）
- Lead Agent 不可删除（系统内置）

**LLM Service (`services/llm.py`)：**
- `LLMService` 类：从 `LLMConfig` 表读取配置
- 根据 `api_format` 字段路由到不同的实现：
  - `openai` → POST `{base_url}/chat/completions`，用 OpenAI 请求/响应/SSE 格式
  - `anthropic` → POST `{base_url}/messages`，用 Anthropic Messages 请求/响应/SSE 格式
- `chat(model, messages)` — 非流式调用（MVP 先跑通）
- `chat_stream(model, messages)` — 流式调用 async generator
- 支持 model 参数跨 LLM Provider 切换

**Agent Service (`services/agent.py`)：**
- `AgentService` 类
- `seed_lead_agent()` — 应用启动时确保 Agent Pool 中有 Lead Agent（如不存在则创建）
- `join_auto_agents(inspiration_id)` — 创建 Inspiration 后调用，将 `auto_join=true` 的模板加入其 Team
  - MVP 效果：将 Lead Agent 拉入新 Inspiration
  - 每个 `InspirationAgent` 继承模板的 `default_model`
- `list_by_inspiration(inspiration_id)` — 返回 Inspiration 的 Team 成员
- 创建 Inspiration 时自动调用（在 `routers/inspirations.py` 的 `POST` 中）

**后端 API 路径总览：**
```
/api/inspirations                  ← CRUD (已有)
/api/settings/llm                  ← LLM Provider 管理 (NEW)
/api/settings/agents               ← Agent 池管理 (NEW)
/api/inspirations/{id}/agents      ← Team 成员管理 (Iter-3)
/api/inspirations/{id}/chat        ← 聊天 (Task 2.2)
/api/inspirations/{id}/chat/stream ← SSE 流式 (Task 2.2)
/api/inspirations/{id}/messages    ← 消息历史 (Task 2.2)
```

**验证：**
- 添加 LLM Provider → GET 返回列表
- 设置默认 → `is_default` 变更，其他变为 false
- 应用启动 → Agent Pool 中有 Lead Agent
- 创建 Inspiration → Team 中自动出现 Lead Agent，绑定默认 LLM
- 手动调用 `chat_stream()` → 收到流式 tokens

---

### Task 2.2: 后端 — 聊天 API + SSE 流式

**文件：**
- `backend/app/routers/chat.py` — 聊天路由
- `backend/app/main.py` — 注册路由

**API 规格：**

1. `POST /api/inspirations/{id}/chat`
   - Body: `{ "content": "Hello, help me build a blog" }`
   - 流程：
     1. 查找该 Inspiration 的默认 Agent（Lead Agent）
     2. 保存 Human Message（role="human", agent_id=default_agent.id）
     3. 加载历史消息（最近 20 条）作为上下文
     4. 从 Agent 获取 model → 从 LLMConfig 获取 api_key/base_url
     5. 调用 `LLMService.chat()`
     6. 保存 Agent Message（role="agent", agent_id=default_agent.id）
     7. 返回 `{ "message": { id, role, content, ... }, "agent": { ... } }`

2. `POST /api/inspirations/{id}/chat/stream`
   - Body 同上
   - 返回 `StreamingResponse` with `text/event-stream`
   - 格式：`data: {"token": "Hello"}\n\n` ... `data: [DONE]\n\n`
   - 流结束后保存完整 Agent Message 到数据库

3. `GET /api/inspirations/{id}/messages`
   - Query: `?limit=50&before=<message_id>`（cursor 分页）
   - 返回 `{ "messages": [...], "has_more": bool }`
   - 消息按时间升序

**验证：**
- `curl -X POST /api/inspirations/{id}/chat` → 返回完整回复
- `curl -N -X POST /api/inspirations/{id}/chat/stream` → 看到逐行 SSE 数据
- 消息持久化到 SQLite，重启仍在

---

### Task 2.3: 前端 — Chat UI + 流式展示

**文件：**
- `frontend/src/components/ChatArea.tsx` — 重写
- `frontend/src/components/ChatMessage.tsx` — 消息气泡（NEW）
- `frontend/src/components/ChatInput.tsx` — 输入区（NEW）
- `frontend/src/stores/chatStore.ts` — 聊天状态（NEW）
- `src-tauri/src/lib.rs` — 添加 chat commands

**Rust Commands：**
```rust
// 非流式（MVP 快速跑通）
send_message(inspiration_id: String, content: String) -> Result<Message, String>

// 流式（生产用）
// 方案: Rust reqwest 读 SSE stream → app_handle.emit("chat-token", payload)
// 前端: listen("chat-token", (event) => { ... })
stream_message(app_handle: tauri::AppHandle, inspiration_id: String, content: String)
    -> Result<(), String>  // 通过 event 返回，不通过返回值

// 历史消息
get_messages(inspiration_id: String, limit: Option<u32>, before: Option<String>)
    -> Result<Vec<Message>, String>
```

**chatStore 状态：**
```typescript
interface ChatStore {
  messages: Message[]           // 当前 inspiration 的消息
  streaming: boolean            // 是否正在接收流
  streamContent: string         // 当前流的累积内容
  sendMessage: (inspirationId: string, content: string) => Promise<void>
  loadMessages: (inspirationId: string) => Promise<void>
  clearStream: () => void       // 流完成/取消时追加到 messages
}
```

---

#### 前端展现：ChatArea 完整布局

```
┌──────────────────────────────────────────────────────┐
│ Amazing Project  [MVP]  🟢 1 ACTIVE                  │  ← TopBar (现有, 微调)
│                              [👥 Team] [📊] [⋯]      │
├──────────────────────────────────────────────────────┤
│                                                      │
│ ┌── Agent (Lead Agent) ────────────────────────┐  │
│ │ 🤖 GA                                           │  │  ← Agent 气泡
│ │ ┌──────────────────────────────────────────────┐ │  │    灰色背景 #f3f3f3
│ │ │ Hello! I'm your default agent.               │ │  │    圆角: 2px 16px 16px 16px
│ │ │ How can I help you build something today?    │ │  │    最大宽度: 70%
│ │ └──────────────────────────────────────────────┘ │  │
│ │                                    12:03 PM      │  │  ← 时间右对齐
│ └──────────────────────────────────────────────────┘  │
│                                                      │
│              ┌── You ────────────────────────────┐   │
│              │                         12:04 PM  │   │  ← Human 气泡
│              │ ┌──────────────────────────────┐  │   │    白色背景 #fff
│              │ │ Let's build a markdown blog! │  │   │    绿色边框 #34c759
│              │ └──────────────────────────────┘  │   │    圆角: 16px 16px 2px 16px
│              └──────────────────────────────────┘   │    右对齐
│                                                      │
│ ┌── Agent (Lead Agent) ────────────────────────┐  │
│ │ 🤖 GA                                           │  │  ← 流式气泡
│ │ ┌──────────────────────────────────────────────┐ │  │    结构同 Agent 气泡
│ │ │ Sure! Let me outline the structure first▮   │ │  │    末尾 ▮ blink 闪烁
│ │ └──────────────────────────────────────────────┘ │  │    内容逐 token 追加
│ └──────────────────────────────────────────────────┘  │
│                                                      │
├──────────────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────────────┐ │
│ │ Build a markdown blog with tags and RSS...       │ │  ← ChatInput
│ │                                                  │ │    textarea
│ │                                       [📎] [➤]  │ │    发送按钮 accent 色
│ └──────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

---

#### ChatMessage 气泡详细规格

**Agent 气泡：**

```
┌────────────────────────────────────────────┐
│ 🤖 Agent Name                    12:03 PM  │  第一行: 头像 + 名称 + 时间
│ ┌────────────────────────────────────────┐ │
│ │ 消息内容...                             │ │  气泡本体
│ │                                        │ │
│ └────────────────────────────────────────┘ │
└────────────────────────────────────────────┘

规格:
  - 容器: flex 行, align-items: flex-start, gap: 10px, margin-bottom: 16px
  - 头像: 28×28 圆, bg hash 色, 文字 initials 10px
  - 名称: 12px, font-weight 600, color #1a1c1c
  - 时间: 10px, color #9ea7b0
  - 气泡: bg #f3f3f3, 圆角 2px 16px 16px 16px, padding 12px 16px
  - 文字: 14px, line-height 1.55, color #1a1c1c
  - 最大宽度: 70% (或 520px)
```

**Human 气泡：**

```
                              12:04 PM  You
              ┌────────────────────────────┐
              │ 消息内容...                  │
              └────────────────────────────┘

规格:
  - 容器: flex 行, justify-content: flex-end, gap: 10px
  - 时间: 10px, color #9ea7b0
  - "You": 12px, font-weight 500
  - 气泡: bg #fff, border 1px solid #34c759, 圆角 16px 16px 2px 16px
  - padding 12px 16px, 最大宽度 70%
  - 文字同 Agent
```

**System 消息：**

```
            ── Conversation started ──

规格:
  - 容器居中, margin: 16px 0
  - 文字: 11px, color #9ea7b0, font-style: italic (可选)
  - 无气泡背景
```

**流式 Agent 气泡：**
- 结构同 Agent 气泡 + 末尾渲染光标
- 光标 `▮`：CSS `@keyframes blink { 0%,100% { opacity:1 } 50% { opacity:0 } }`
- 流式内容追加 → auto-scroll
- 流完成 → 光标消失，`streamContent` 追加到 `messages`，重置 `streamContent`

---

#### ChatInput 详细规格

```
┌──────────────────────────────────────────────┐
│ ┌──────────────────────────────────────────┐ │
│ │                                          │ │  ← textarea
│ │ Message Agents or Team...                │ │    min-height: 44px
│ │                                          │ │    max-height: 150px
│ └──────────────────────────────────────────┘ │    overflow-y: auto
│                                              │    padding: 12px 16px
│ [📎]                              [➤]       │    bg: #f3f3f3
└──────────────────────────────────────────────┘    border-radius: 12px
                                                    resize: none
  发送按钮:
    - 圆形 40×40, bg: --color-accent, 白色箭头图标
    - disabled: opacity 0.4, cursor not-allowed
    - sending: 显示 spinner 替代箭头

  附件按钮:
    - 28×28, ghost, disabled (MVP)
```

**交互规格：**
- Enter（无 Shift）→ 发送消息
- Shift+Enter → 插入换行
- 空内容/纯空白 → 发送按钮 disabled
- 发送中 → textarea disabled, 发送按钮显示 spinner
- 发送完成 → 清空 textarea, 聚焦
- 最大输入高度 150px 后出现内部滚动条

---

#### 消息列表滚动行为

- 消息区域 `flex: 1 0 0`, `overflow-y: auto`
- 新消息到达 / 流式更新 → 自动 `scrollTo({ top: scrollHeight, behavior: 'smooth' })`
- 用户手动上滚 >100px 时暂停自动滚动，显示 "↓ New messages" 浮动按钮
- 点击浮动按钮 → 滚回底部, 恢复自动滚动
- 切换 Inspiration → 滚动到顶部（或加载历史时保持位置）

---

#### 空状态

**未选中 Inspiration：**
```
              💬
     Start a conversation
  Select an inspiration to begin chatting
```
- 图标 48×48，opacity 0.3
- 一级文字 16px, color #4e6073
- 二级文字 13px, color #9ea7b0

**选中但无消息（LLM 已配置）：**
```
              💬
     Send your first message
  "Lead Agent" is ready to help
```
- 同样居中布局 + 显示 Agent 名称

**选中但 LLM 未配置：**
```
              ⚙
     No LLM configured
  Go to Settings to add an LLM provider first
              [Go to Settings]
```
- 提供快捷跳转按钮

---

#### TopBar 微调

当前 TopBar 已有 Inspiration 名称 + MVP tag + status。Iter-2 不需要大改，只需：
- Status 指示器联动真实 Agent 状态（idle/working/error）
- working 时状态文字变绿 + dot 脉冲动画

---

## Iter-3: Agent Pool 初始化 + Agent 管理 + Right Panel

> 前置: Iter-2 完成 LLM 池 + Agent 池 + Lead Agent 自动加入 Team

---

### ✅ Task 3.0: 后端 — 5 个内置 Agent 模板初始化（已完成）

> 完成日期: 2026-04-29

**实际新增 4 个 Expert Agent（共 5 个内置）：**

| # | 名称 | role | auto_join | 来源 |
|---|------|------|-----------|------|
| 1 | General Manager | `lead` | true | 已有，保持不变 |
| 2 | Bazi Expert | `bazi` | false | `docs/ref/4-agents-info.md` |
| 3 | Zi Wei Expert | `ziwei` | false | `docs/ref/4-agents-info.md` |
| 4 | I Ching Expert | `iching` | false | `docs/ref/4-agents-info.md` |
| 5 | Astrologer | `astrologer` | false | `docs/ref/4-agents-info.md` |

**已修改文件：**
- `backend/app/services/agent.py` — 4 个 `DEFAULT_*_SYSTEM_PROMPT` 常量 + `seed_expert_agents()` 方法
- `backend/app/main.py` — lifespan 中调用 `seed_expert_agents()`
- `backend/app/routers/agent_templates.py` — `system_prompt` max_length 5000→15000
- `frontend/src/components/AgentPoolList.tsx` — role→letter 头像映射 (L/B/Z/I/A)
- `frontend/src/components/AgentDetail.tsx` — `isBuiltin` 保护内置 Agent 名称不可编辑

**已验证：** 冷启动 5 agent、重启无重复、TypeScript 编译通过、QA checklist 已生成

---

### ✅ Task 3.1: 后端 — Team 成员路由 (agents.py)

**文件：**
- `backend/app/routers/agents.py` — NEW: Team 成员路由（操作 InspirationAgent 表）
- `backend/app/main.py` — 注册路由

**API 规格：**
1. `GET /api/inspirations/{id}/agents` — 返回该 Inspiration 的 Team 成员列表
2. `POST /api/inspirations/{id}/agents` — 从 Agent Pool 拉入一个 Agent 到 Team
   - Body: `{ template_id }` — Agent 池中的模板 ID
   - 继承模板的 name/role/model，后续可独立覆盖
3. `PATCH /api/agents/{agent_id}` — 修改 Team 中 Agent 的模型
   - Body: `{ model? }` — model 从 Sloth LLM 池中选取
4. `DELETE /api/inspirations/{id}/agents/{agent_id}` — 从 Team 移除 Agent
   - Lead Agent (role="lead") 不可移除

**验证：**
- 从 Pool 拉入 Expert Agent → Team 列表中出现
- 切换模型 → PATCH 成功
- 尝试删除 Lead Agent → 返回 403

---

### ✅ Task 3.2: 前端 — Right Panel + Team 管理 UI

**文件：**
- `frontend/src/components/RightPanel.tsx` — 完整重写
- `frontend/src/stores/agentStore.ts` — Zustand Team 状态（NEW）
- `frontend/src/api/client.ts` — 添加 Team API 函数 + InspirationAgent 类型
- `src-tauri/src/lib.rs` — 添加 agent team commands

**RightPanel 展现（选中 Inspiration 时自动打开）：**

```
┌──────────────────────────────────┐
│ Team                         [✕] │
├──────────────────────────────────┤
│ AGENTS                    2      │
│                                  │
│ ┌──────────────────────────────┐ │
│ │ [B] Bazi Expert     🟢 idle  │ │  ← role→letter 头像
│ │    bazi                       │ │
│ │    [Remove]                  │ │
│ └──────────────────────────────┘ │
│ ┌──────────────────────────────┐ │
│ │ [L] General Manager 🟢 idle  │ │  ← Lead Agent, 不可移除
│ │    lead                       │ │
│ └──────────────────────────────┘ │
│                                  │
│ ─── + Add Agent ───              │  ← 展示未加入 Team 的模板列表
│                                  │
└──────────────────────────────────┘
```

**agentStore 状态：**
```typescript
interface AgentStore {
  teamMembers: InspirationAgent[]
  templatePool: AgentTemplate[]
  loading: boolean
  fetchTeam: (inspirationId: string) => Promise<void>
  addToTeam: (inspirationId: string, templateId: string) => Promise<void>
  removeFromTeam: (agentId: string) => Promise<void>
}
```

**交互规格：**
- 选中 Inspiration → RightPanel 自动打开（col4Open=true, col4Content="team"）
- 切换 Inspiration → 刷新 team 列表
- 点击 "+ Add Agent" → 下拉展示 Pool 中未入队的模板 → 点击即添加
- 非 Lead Agent hover 显示 Remove 按钮
- Model 切换 MVP 阶段不实现（Spec §8: "不做 Agent 角色行为区分"）

**验证：**
- 选中 Inspiration → RightPanel 显示 Team（至少 Lead Agent）
- Add Agent → Team 成员增加
- Remove agent → Team 成员减少，Lead Agent 不可移除
- 切换 Inspiration → team 列表刷新

---

## Iter-4: Brainstorm 会话沙箱（3 天）

> 为 Brainstorm 建立独立的、隔离的工作区。每次 Brainstorm 有一个独立沙箱目录，所有 Agent 产出落在此目录，与项目文件物理隔离。

### Task 4.0: 数据模型 — brainstorm_sessions + brainstorm_files 表

**状态：** ✅

**描述：** 新增两张表支持 Brainstorm 会话管理。brainstorm_files 表在 Iter-4 建好但实际写入延至 Iter-8。使用 Alembic 迁移管理 schema 变更。

**文件：**
- `backend/app/models.py` — 新增 BrainstormSession, BrainstormFile 模型
- Alembic 迁移文件 — `alembic/versions/xxxx_brainstorm_sessions.py`

**实现要点：**
- BrainstormSession 字段: id, inspiration_id, title, status("active"|"cooling_down"|"ended"|"summarized"), sandbox_path, max_messages(1000), cooldown_seconds(5), message_count(0), summary(None), started_by(None), notification_sent(False), created_at, ended_at
- BrainstormFile 字段: id, session_id(FK), file_path, content, created_by(FK→inspiration_agents), file_type("code"|"doc"|"test"|"config"|"other"), created_at
- status 字段 default="active"，message_count default=0
- 迁移文件含 upgrade() 和 downgrade()

**验证：**
- [ ] 运行 Alembic 迁移 → 两张表创建成功
- [ ] `alembic downgrade -1` → 表删除，可回滚

### Task 4.1: SandboxManager 服务

**状态：** ✅

**描述：** 管理沙箱目录的创建、文件树查询、清理。不负责文件写入（Iter-8）。

**文件：**
- `backend/app/services/sandbox.py` — 新建 SandboxManager 类

**实现要点：**
```python
class SandboxManager:
    BASE_DIR = "brainstorm-sessions"

    @staticmethod
    def create_session_dir(session_id: str) -> str:
        """创建 brainstorm-sessions/{session_id}/ 目录，返回绝对路径"""

    @staticmethod
    def get_file_tree(session_id: str) -> list[dict]:
        """递归遍历沙箱目录，返回文件树 [{name, path, type, size}]"""

    @staticmethod
    def get_session_path(session_id: str) -> str:
        """返回沙箱目录绝对路径"""

    @staticmethod
    def archive_session(session_id: str):
        """移到 .archive/ 子目录"""

    @staticmethod
    def cleanup_archive(max_age_days: int = 7):
        """清理过期归档"""
```

**验证：**
- [ ] `create_session_dir("test-uuid")` → `brainstorm-sessions/test-uuid/` 目录产生
- [ ] `get_file_tree()` 返回正确的目录结构（空目录返回空列表）
- [ ] 手动放文件后 `get_file_tree()` 返回对应文件信息

### Task 4.2: Brainstorm CRUD API

**状态：** ✅

**描述：** Brainstorm 会话的创建、列表、详情 API。创建会话时自动初始化沙箱目录。

**文件：**
- `backend/app/routers/brainstorm.py` — 新建 CRUD router
- `backend/app/main.py` — 注册 router

**API 规格：**
1. `POST /api/inspirations/{inspiration_id}/brainstorm-sessions`
   - Body: `{ "title": "Architecture Review" }`
   - 流程: 生成 UUID → 创建 DB 记录 → SandboxManager.create_session_dir() → 返回 session
2. `GET /api/inspirations/{inspiration_id}/brainstorm-sessions`
   - 返回该 Inspiration 下所有会话，按 created_at 降序
3. `GET /api/brainstorm-sessions/{session_id}`
   - 返回会话详情（含 sandbox_path + 文件树）
4. `PATCH /api/brainstorm-sessions/{session_id}`
   - 更新 status / title

**实现要点：**
- 创建会话时传入 inspiration_id，验证 Inspiration 存在
- 详情接口调用 SandboxManager.get_file_tree() 注入响应
- 错误处理：Inspiration 不存在返回 404

**验证：**
- [ ] `POST` → 返回 201 + 会话 JSON，`brainstorm-sessions/{uuid}/` 目录存在
- [ ] `GET /api/inspirations/{id}/brainstorm-sessions` → 返回列表
- [ ] `GET /api/brainstorm-sessions/{id}` → 返回详情含 file_tree
- [ ] 重启后端 → 会话数据持久化
- [ ] `brainstorm-sessions/` 已在 `.gitignore` 中

### Task 4.3: 前端 — Brainstorm 会话列表 + 创建

**状态：** ✅

**描述：** 前端新增 Brainstorm 视图入口。Col1 SideNavBar 新增 Brainstorm Tab。Col2 显示会话列表，Col3 显示会话详情占位（等 Iter-6）。

**文件：**
- `frontend/src/components/BrainstormList.tsx` — 新建 Col2 会话列表
- `frontend/src/components/SideNavBar.tsx` — 添加 Brainstorm Tab 按钮
- `frontend/src/stores/brainstormStore.ts` — 新建 Zustand store
- `frontend/src/stores/uiStore.ts` — 扩展 activeNav 支持 "brainstorm"
- `frontend/src/App.tsx` — 条件渲染 BrainstormList
- `frontend/src/api/client.ts` — 添加 Brainstorm API 函数
- `src-tauri/src/lib.rs` — 添加 brainstorm commands

**实现要点：**
- SideNavBar: 新增 Brainstorm 图标按钮（灯泡/闪电图标），点击切换 activeNav="brainstorm"
- BrainstormList: 顶部 "Brainstorm" 标题 + "+" 创建按钮，列表每项显示 title + status badge + 创建时间
- "+" 按钮 → 行内输入框（复用 Iter-1 Task 1.4 的交互模式）→ Enter 创建会话
- brainstormStore: sessions[], activeId, fetchAll(), create(title), setActive(id)
- Col3 在 Iter-4 阶段显示会话基本信息占位（title, status, sandbox_path, created_at），完整 UI 等 Iter-6

**验证：**
- [ ] SideNavBar 显示 Brainstorm Tab，点击切换
- [ ] 点击 "+" → 输入标题 → Enter → 列表中新增会话
- [ ] 点击会话 → Col3 显示会话基本信息
- [ ] 切换 Inspiration → 会话列表过滤为该 Inspiration 的会话

**完成备注（2026-05-01）：**
- UI 架构从"独立 Col2/Col3"改为"集成到 Inspiration Chat 内"（验证反馈 #12-16 驱动）
- BrainstormFile 表按计划延至 Iter-8
- 额外实现：slide toggle 状态控制、会话搜索、聊天分割线（start/end/transition）、角色颜色映射
- 版本发布：v0.5.3

---

## Iter-5: 讨论引擎 — 两轮投票 + SSE 流式（3 天，已完成）

> 后端讨论引擎。多个 Agent 并行发言，冷却计时器自然结束讨论。前端不在此迭代做彩色 UI（留给 Iter-6），只做基础 JSON 流式展示。

### Task 5.0: Messages 表扩展（Alembic 迁移）

**状态：** ✅

**描述：** Message 表新增 5 个字段支持 Brainstorm 讨论模式。Chat 模式下的消息这些字段保持默认值。

**文件：**
- `backend/app/models.py` — Message 模型新增字段
- Alembic 迁移文件 — `alembic/versions/xxxx_message_brainstorm_fields.py`

**新增字段：**
- `brainstorm_session_id: str | None` (FK → brainstorm_sessions, NULL = Chat 模式)
- `parent_message_id: str | None` (FK → messages, 回复引用)
- `round: int` (default 1)
- `intent: str | None` (NULL | "YES" | "NO")
- `truncated: bool` (default False)

**验证：**
- [ ] 迁移执行成功 → 现有 Chat 消息不受影响（新字段为默认值）
- [ ] 可写入含新字段的消息

### Task 5.1: BrainstormEngine — DecisionStrategy + CoolingTimer

**状态：** ✅

**描述：** 讨论引擎核心。包含两轮投票策略和冷却计时器状态机。

**文件：**
- `backend/app/services/brainstorm.py` — 新建 BrainstormEngine

**实现要点：**

1. **DecisionStrategy 抽象接口：**
```python
class DecisionStrategy(ABC):
    @abstractmethod
    async def collect_intents(self, agents, context, topic) -> dict[str, tuple[Literal["YES","NO"], str]]:
        """Round 1: 并行收集发言意向"""
    @abstractmethod
    async def generate_speeches(self, agents, intents, context, topic) -> AsyncIterator[SpeechChunk]:
        """Round 2: 并行生成发言, 流式产出"""
```

2. **TwoRoundVoting 实现：**
   - Round 1: N 个 Agent 并行调用 LLM，`max_tokens=20`，prompt: "回复 'YES: <方向>' 或 'NO'。不超过 10 个词。"
   - Round 2: YES 的 Agent 并行流式生成完整回复
   - Lead Agent 不参与 Round 1/2，负责生成轮次总结

3. **CoolingTimer 状态机：**
   - RUNNING → (5s 无人发言) → COOLING_DOWN
   - COOLING_DOWN → (3s 确认) → CONFIRMING
   - CONFIRMING → (3s) → ENDED
   - 新发言/agent_typing → 重置到 RUNNING
   - 达到 max_messages(1000) → 硬截断 → ENDED
   - 用户发新消息 → round_aborted → ENDED

4. **错误处理：**
   - 单个 Agent 超时/失败 → 重试 2 次 → 仍失败跳过
   - 所有 Agent 全失败 → 讨论终止

**验证：**
- [ ] 模拟 3 个 Agent 讨论 → Round 1 收集意向 → YES 的进 Round 2
- [ ] 5s 无人发言 → 冷却开始 → 3s 确认 → 讨论结束
- [ ] Agent 超时 → 重试 → 最终跳过，不影响其他 Agent

### Task 5.2: SSE Discuss 端点

**状态：** ✅

**描述：** SSE 端点接收用户消息，启动 BrainstormEngine，将事件流式推送到前端。单一 SSE 连接复用所有 Agent 事件。

**文件：**
- `backend/app/routers/brainstorm.py` — 新增 SSE discuss 端点

**API 规格：**
- `POST /api/brainstorm-sessions/{session_id}/discuss`
  - Body: `{ "content": "我们应该用 JWT 还是 Session?", "reply_to_message_id": null }`
  - Response: `text/event-stream`

**SSE 事件类型（13 种）：**
```
agent_start:      {agent_id, agent_name, agent_number}
agent_intent:     {agent_id, intent: "YES"|"NO", direction}
agent_typing:     {agent_id}
message_token:    {agent_id, message_id, token, parent_message_id}
message_done:     {agent_id, message_id, full_content, parent_message_id}
agent_error:      {agent_id, error, retry: bool}
cooldown_start:   {seconds: 5}
cooldown_reset:   {triggered_by: agent_id}
cooldown_confirm: {seconds: 3}
discussion_end:   {summary: null, message_count}  # summary 在 Iter-5 为 null
max_reached:      {limit: 1000}
round_aborted:    {reason}
error:            {error}
```

**实现要点：**
- 用户消息先保存为 Message（role="human", round=当前轮次）
- 加载当前会话历史消息作为上下文
- 获取 Inspiration 的 Team 成员作为参与 Agent
- BrainstormEngine 内部通过 asyncio.Queue 发送 SSE 事件
- 端点从 Queue 读取 → 格式化为 SSE → yield
- 用户中断处理：`asyncio.Task.cancel()` 取消进行中调用

**验证：**
- [ ] `curl -N -X POST /api/brainstorm-sessions/{id}/discuss` → 看到逐行 SSE 数据
- [ ] 每个 Team Agent 都收到 agent_start 事件
- [ ] Round 1 意向在 agent_intent 中返回
- [ ] message_token 流式推送 token
- [ ] message_done 含完整消息内容
- [ ] 消息持久化到 messages 表，含 brainstorm_session_id, round, parent_message_id

### Task 5.3: 前端 — 基础 SSE 消费 + JSON 展示

**状态：** ✅

**描述：** 前端实现 SSE 消费，在 Brainstorm 会话下以基础气泡展示讨论消息（不做彩色线程，留给 Iter-6）。

**文件：**
- `frontend/src/stores/brainstormStore.ts` — 扩展 SSE 消费 + per-agent streaming state
- `frontend/src/components/BrainstormArea.tsx` — 新建基础版讨论视图
- `frontend/src/components/ChatArea.tsx` — TopBar 加临时模式标记
- `src-tauri/src/lib.rs` — 添加 SSE proxy command

**实现要点：**
- brainstormStore 扩展：
  - `startDiscussion(sessionId, content, replyToMessageId?)` → fetch SSE
  - `Map<agentId, StreamingState>` 管理 per-agent 流式状态
  - `Map<messageId, Message>` 管理持久消息
  - `intents: Map<string, IntentResult>` 管理 Round 1 意向
- BrainstormArea: 基础消息列表（复用 ChatArea 的消息渲染逻辑），显示 agent_name, content, time
- 流式消息显示打字光标闪烁效果（复用 ChatArea ThinkingBubble 动画）
- 讨论状态指示器："Round 1 意向收集中..." / "Agent 发言中..." / "冷却中..." / "已结束"

**验证：**
- [ ] 在 Brainstorm 会话中输入消息 → SSE 连接建立
- [ ] 多个 Agent 消息并行流式渲染，打字效果
- [ ] 讨论自然结束 → 状态显示"已结束"
- [ ] 发新消息 → 上一轮标记结束，新轮开始

---

## Iter-6: 流体讨论引擎 + 彩色线程 UI（4 天，已完成）

> **范围扩展（2026-05-02 更新）：** 原计划仅做前端 UI，经 Review 发现后端 Brainstorm 交互存在根本性架构问题（request-response 模型无法支持用户随时插话），故将后端持久连接改造一并纳入 Iter-6。原前端任务保持，Task 6.0 新增后端改造。

### 背景：当前架构的 3 个根本性问题

1. **用户插话必须先中断讨论**：`sendOne()` 中检测到 `discussionActive` 时会调用 `waitForDiscussionIdle()` abort 当前 SSE，再重建新连接。用户每次发言都会截断 agent 正在说的话。
2. **Reply-to 无 UI 入口**：API 支持 `reply_to_message_id`，但 UI 没有 reply 按钮，前端调用也不传该字段。
3. **讨论状态清空机制脆弱**：`startDiscussion()` 开头强制 `discussionMessages: []`，靠 useEffect 追加，每次都从零重建。

**目标交互**：进入 Brainstorm 模式 → 建立一个持久 SSE 连接 → 用户随时可发消息（注入队列）→ agents 自然接住，不中断流 → 任何消息可 reply → 讨论持续直到手动结束或全员 PASS。

---

### Task 6.0: 后端 — 持久连接 + 消息队列注入

**状态：** ✅

**描述：** `BrainstormEngine` 由 one-shot `run()` 改为持久 queue-driven 循环。新增 `connect` 持久 SSE 端点和 `inject` 消息注入端点，原 `discuss` 端点废弃。

**文件：**
- `backend/app/services/brainstorm.py` — 重构 BrainstormEngine
- `backend/app/routers/brainstorm.py` — 新增 connect / inject 端点

**后端实现要点：**

**BrainstormEngine 重构**

```python
class BrainstormEngine:
    def __init__(self, session_id, inspiration_id, ...):
        self._queue: asyncio.Queue[dict] = asyncio.Queue()
        self._abort = False

    async def inject(self, content: str, reply_to_message_id: str | None = None):
        """用户随时调用，将消息放入队列。不中断当前讨论。"""
        await self._queue.put({"content": content, "reply_to": reply_to_message_id})

    async def run(self) -> AsyncIterator[SSEEvent]:
        """持久循环：等队列消息 → agents 响应 → 检查队列 → 继续。"""
        while not self._abort:
            # 等待下一条用户消息（有超时，以便定期检查 abort）
            try:
                msg = await asyncio.wait_for(self._queue.get(), timeout=30.0)
            except asyncio.TimeoutError:
                yield SSEEvent(event="heartbeat", data={})
                continue

            user_content = msg["content"]
            reply_to = msg["reply_to"]

            # 保存用户消息
            user_msg_id = await self._save_message(role="human", content=user_content,
                                                    parent_message_id=reply_to)
            yield SSEEvent(event="user_message", data={"message_id": user_msg_id, "content": user_content})

            # agents 顺序发言，每个 agent 之间检查队列是否有新消息
            agents = await self._load_agents()
            for agent in agents:
                if self._abort:
                    break
                # 若队列有新消息，优先结束本轮，让新消息先处理
                if not self._queue.empty():
                    break
                # 正常发言流程（与当前 run() 内的 agent 发言逻辑相同）
                yield* self._agent_turn(agent, user_msg_id, ...)

            # 全员 PASS 后发出 round_end（不关闭连接）
            yield SSEEvent(event="round_end", data={"round": ...})

        yield SSEEvent(event="discussion_end", data={...})
```

**新增端点**

```
POST /api/brainstorm-sessions/{id}/connect   → 建立持久 SSE 连接（不含消息）
POST /api/brainstorm-sessions/{id}/inject    → 向 queue 注入一条用户消息
DELETE /api/brainstorm-sessions/{id}/connect → 优雅关闭（设 _abort=True）
```

- `connect` 端点创建 `BrainstormEngine` 并注册到 `_active_connections[session_id]`，返回 SSE 流
- `inject` 端点查找 `_active_connections[session_id]`，调用 `engine.inject()`；若无活跃连接 → 400
- 原 `POST /discuss` 和 `DELETE /discuss` 端点保留但标注 deprecated，Iter-7 删除
- `_active_connections` 为持久连接注册表，`_active_engines` 仅保留给 legacy `/discuss` 路径

**新增 SSE 事件**

| 事件 | 载荷 | 说明 |
|------|------|------|
| `user_message` | `message_id, content` | 用户消息已入库（用于前端乐观更新确认）|
| `round_end` | `round, speeches` | 本轮 agent 发言完毕（连接保持）|
| `heartbeat` | `{}` | 空闲心跳，防止连接超时 |

**验证：**
- [ ] `POST /connect` 返回 SSE 流，连接保持（不因单次 inject 关闭）
- [ ] `POST /inject` 在 SSE 流中触发 agents 响应
- [ ] 连续 inject 两条消息时，第二条排队，等第一轮 agents 响应完后处理
- [ ] agent 正在流式输出时 inject 新消息，新消息进队列不中断当前 agent
- [ ] `DELETE /connect` 触发 `discussion_end` 事件后连接关闭

---

### Task 6.1: 前端 Store — 持久连接模型

**状态：** ✅

**描述：** `brainstormStore` 重构：`startDiscussion` 改为 `connectSession`（建立持久连接），`sendMessage` 只做 POST inject，完全分离连接生命周期和消息发送。

**文件：**
- `frontend/src/stores/brainstormStore.ts` — 重构

**实现要点：**

```ts
// 新接口
connectSession(sessionId: string): Promise<void>      // 建立持久 SSE 连接
disconnectSession(): void                              // 关闭连接（DELETE /connect）
injectMessage(sessionId: string, content: string, replyToMessageId?: string): Promise<void>

// 废弃（Iter-7 删除）
startDiscussion(...)   // → 改为调用 connectSession + injectMessage
stopDiscussion()       // → 改为调用 disconnectSession
```

- `connectSession` 打开 SSE 连接，持续监听 `user_message`, `agent_start`, `agent_token`, `message_done`, `agent_pass`, `round_end`, `heartbeat`, `discussion_end`
- `discussionConnected` 与 `discussionActive` 共存：前者表示 SSE 连接活跃，后者表示当前有 agent 正在生成响应
- `injectMessage` 做 `POST /inject`，立即返回（无需等待 SSE 响应）
- `replyingToId: string | null` 新状态字段，由 UI 设置，`injectMessage` 读取后自动清空
- `discussionMessages` 仅作为本会话消息增量 buffer，不再 `set({ discussionMessages: [] })` 清空
- `handleSSEEvent` 新增 `user_message`（确认消息已入库，替换乐观更新临时消息）、`round_end`、`heartbeat` 处理

**新增状态字段**

```ts
discussionConnected: boolean      // 持久连接是否活跃
replyingToId: string | null       // 当前 reply 目标消息 ID
replyingToContent: string | null  // 被引用消息预览文本（前 30 字）
```

**验证：**
- [ ] 进入 brainstorm 模式 → `connectSession` 自动调用，`discussionConnected = true`
- [ ] 输入消息 → `injectMessage` POST，不重建 SSE 连接
- [ ] 用户连续快速发两条消息 → 两条均进队列，SSE 流中依次收到 agents 响应
- [ ] 离开 brainstorm 模式 → `disconnectSession` 自动调用，连接关闭

---

### Task 6.2: 前端 UI — Reply 按钮 + 引用条

**状态：** ✅

**描述：** 消息气泡 hover 显示 Reply 按钮，点击后输入框上方出现引用条；发送带 `replyToMessageId`。

**文件：**
- `frontend/src/components/ChatArea.tsx` — 消息 hover 交互 + 引用条
- `frontend/src/stores/brainstormStore.ts` — `replyingToId` 状态已在 Task 6.1 添加

**实现要点：**
- 仅 brainstorm 模式下，消息 hover 显示 Reply 按钮（右上角，ghost 样式，`↩ Reply`）
- 点击 Reply → 调用 `useBrainstormStore.setState({ replyingToId, replyingToContent })`
- 输入框上方引用条：`↩ 回复 {agent_name} · "{内容前30字}" [✕]`，accent 色左边线
- `[✕]` 清空 `replyingToId`
- `handleSend` 中读取 `replyingToId`，传入 `injectMessage` 后清空
- 人类消息也可以被 reply（reply_to 不限 role）

**验证：**
- [ ] brainstorm 模式下 hover 消息 → Reply 按钮出现
- [ ] 点击 Reply → 引用条出现在输入框上方
- [ ] 发送后引用条消失，`replyingToId` 清空
- [ ] reply 发出后，`message_done` 事件携带正确 `parent_message_id`
- [ ] chat 模式下 hover 消息 → 无 Reply 按钮

---

### Task 6.3: 前端 UI — 彩色线程引用预览

**状态：** ✅

**描述：** 每条消息根据 `parent_message_id` 链计算线程根 ID，在消息气泡内顶部渲染带线程色的引用预览。

**文件：**
- `frontend/src/components/ChatArea.tsx` — 消息渲染处新增引用预览块
- `frontend/src/utils/threadColor.ts` — 新建，颜色计算工具

**实现要点：**
- `threadColor.ts`：
  ```ts
  // 计算消息的线程根 ID（沿 parent_message_id 链找到无 parent 的祖先）
  function getRootId(messageId: string, messages: Message[]): string
  // 根据根 ID 生成稳定色值（FNV-1a hash → palette index）
  function threadHue(rootId: string): number
  // 返回固定调色板中的线程 accent color
  function threadColor(rootId: string): string
  ```
- 无 `parent_message_id` 的消息：无引用预览（根消息）
- 有 `parent_message_id` 的消息：在气泡内顶部显示引用预览块，左侧 3px 色彩竖线，颜色 = 线程根的 `threadColor`
- 人类 reply 消息也显示同线程色的引用预览
- chat 模式不显示 brainstorm 引用预览

**验证：**
- [ ] 两条无关消息（不同根）引用预览 accent 颜色不同
- [ ] 同一 reply 链内所有消息引用预览 accent 颜色一致
- [ ] 根消息（无 parent）不显示引用预览
- [ ] chat 模式下所有消息无 brainstorm 引用预览

---

## Iter-7: Tool 系统 + 上下文引擎（3 天）

> Agent 可以读取项目文件作为讨论依据。**新判断标准：** 业务逻辑（@tool 装饰器、工具注册表、ROLE_BASE_TOOLS、function calling 循环、ContextEngine）全部放入 `src/sloth_agent/core/`，CLI 和 Desktop 均可直接 import。Desktop backend 退化为 SSE 传输 + SQLite 持久化的薄适配层。
>
> 变更文档: `docs/changes/iter7-tool-system/`

### 架构概览（按新 core 标准）

```
# ────────────────────────────────────────────────
# Core 层（新增，src/sloth_agent/core/）
# ────────────────────────────────────────────────
core/tools/
  decorators.py            # @tool 装饰器、ToolDef、ToolContext、ToolSecurityError
                           # resolve_safe_path（路径沙箱）、ToolPool（全局注册表）
  builtin/
    readonly_fs.py         # read / read_range / grep / grep_repo / glob / ls_dir
                           # 均用 @tool 定义，import 即注册到 ToolPool
core/agents/
  role_tools.py            # ROLE_BASE_TOOLS: dict[str, list[str]]
                           # lead: [read, grep]
                           # fortune: [read, read_range, glob, grep, grep_repo, ls_dir]
                           # bazi/ziwei/iching/astrologer: [read, grep]
  template.py              # AgentTemplate 纯 dataclass（无 DB 耦合）
core/brainstorm/
  tool_loop.py             # run_tool_loop(agent, messages, effective_tools, llm)
                           # function calling 调度：tool_calls → 执行 → role=tool 注入 → 继续生成
                           # 每轮上限 3 次、白名单验证、超限截断
core/context/
  engine.py                # ContextEngine（继承 ContextWindowManager）
                           # build(messages, mode, policy) → 三段输出 + diagnostics
                           # protect_reply_chains：parent_message_id 祖先链保护

# ────────────────────────────────────────────────
# Desktop 薄适配层（重构，backend/app/）
# ────────────────────────────────────────────────
backend/app/
  shared/
    llm_adapter.py         # DB LLMConfig → BaseLLMProvider 实例
                           # 统一 async chat() / chat_stream() 接口
  services/
    agent.py               # from sloth_agent.core.agents import role_tools, template
                           # effective_tools 计算 = ROLE_BASE_TOOLS[role] ∪ AgentTemplate.tools
    brainstorm.py          # SSE 传输 + 持久化；业务逻辑委托 core 层：
                           #   from sloth_agent.core.brainstorm.tool_loop import run_tool_loop
                           #   from sloth_agent.core.context.engine import ContextEngine
    context.py             # DB Messages → core ContextEngine 格式适配
    llm.py                 # 精简：仅保留 DB config 查询，删除重复 httpx 调用
  models.py
    AgentTemplate          # SQLAlchemy ORM 继承/引用 core AgentTemplate dataclass
    AgentTemplate.tools    # JSON 字段，存 agent 个性化追加工具（默认 "[]"）
```

### Agent-Tool 绑定（两层模型，定义在 core）

1. `ROLE_BASE_TOOLS`（core 中定义，role 基础工具，不可被 agent 覆盖）
   - `lead`, `bazi`, `ziwei`, `iching`, `astrologer`: `read`, `grep`
   - `fortune`: `read`, `read_range`, `glob`, `grep`, `grep_repo`, `ls_dir`
2. `AgentTemplate.tools`（agent 个性化追加，默认 `[]`，存于 DB）
3. 运行时：`effective_tools = ROLE_BASE_TOOLS[role] ∪ AgentTemplate.tools`（在 Desktop `agent.py` 中计算）

---

### Task 7.0a: backend path dependency + 共享模块验证（½ 天前置）

**状态：** ⬜

**文件：**
- `backend/pyproject.toml`

**实现要点：**
- 添加 `"sloth-agent @ file:///../"` path dependency
- 验证以下 import 可用，且不会引入 `typer`/CLI 运行时：
  ```python
  from sloth_agent.core.token_counter import TokenCounter
  from sloth_agent.core.context_window import ContextWindowManager
  from sloth_agent.providers.llm_providers import BaseLLMProvider
  ```

**验证：**
- [ ] `uv run pytest backend/tests/ -v` 无 import 破坏
- [ ] `uv run python -c "from sloth_agent.core.token_counter import TokenCounter; print('ok')"` 通过

---

### Task 7.0b: LLM 适配层重构（½ 天）

**状态：** ⬜

**文件：**
- `backend/app/shared/llm_adapter.py`（新建）
- `backend/app/services/llm.py`（精简）

**实现要点：**
- `llm_adapter.py`：从 DB `LLMConfig` 构造对应的 `BaseLLMProvider` 子类实例，暴露统一 `async chat(messages) → str` 和 `async chat_stream(messages) → AsyncIterator[str]` 接口
- `llm.py`：仅保留 `_get_default_llm_config` / `_get_llm_config_for_model` / `seed_default_llm`，删除重复的 `_chat_openai` / `_stream_openai` / `_chat_anthropic` / `_stream_anthropic` 实现
- `brainstorm.py` 改用 `LLMAdapter`（不再直接持有 httpx 调用代码）

**验证：**
- [ ] Brainstorm 流式生成仍正常工作（现有测试不回归）
- [ ] `backend/app/services/llm.py` 行数减少 ≥ 50%
- [ ] `uv run pytest backend/tests/ -v` 全通过

---

### Task 7.C0: [Core] @tool 装饰器 + ToolPool（½ 天）

**状态：** ⬜

**文件：**
- `src/sloth_agent/core/tools/decorators.py`（新建）
- `tests/core/test_tool_decorators.py`（新建）

**实现要点：**
- `ToolDef` dataclass：`name: str`, `description: str`, `parameters_schema: dict`, `fn: Callable`, `is_async: bool`
- `ToolContext` dataclass：`project_root: str`, `session_id: str`, `agent_id: str`
- `ToolSecurityError(Exception)`: 路径越界或权限拒绝时抛出
- `resolve_safe_path(project_root: str, user_path: str) -> Path`：将 user_path 规范化并确保在 project_root 内，否则抛 `ToolSecurityError`
- `ToolPool`：全局注册表 `dict[str, ToolDef]`；`@tool` 装饰器将函数注册到 `ToolPool`
- `@tool` 自动从类型注解和 docstring 生成 JSON Schema（parameters_schema）
- 模块内不 import `typer`、`fastapi`、`sqlalchemy` 等 CLI/Desktop 专属依赖

**验证：**
- [ ] `@tool` 注册成功，`ToolPool["read"]` 可检索
- [ ] `resolve_safe_path` 越界路径抛 `ToolSecurityError`
- [ ] `uv run pytest tests/core/test_tool_decorators.py -v` 通过

---

### Task 7.C1: [Core] 6 个内置只读工具（½ 天）

**状态：** ⬜

**文件：**
- `src/sloth_agent/core/tools/builtin/readonly_fs.py`（新建）
- `tests/core/test_readonly_fs_tools.py`（新建）

**实现要点：**

| 工具 | 签名 | 说明 |
|------|------|------|
| `read` | `(path: str, ctx: ToolContext) → str` | 读取文件全文，最多 500 行，超限截断并注明 |
| `read_range` | `(path: str, start: int, end: int, ctx: ToolContext) → str` | 读取指定行范围（1-based） |
| `grep` | `(pattern: str, path: str, ctx: ToolContext) → str` | 正则匹配，返回含行号结果，最多 50 条 |
| `grep_repo` | `(pattern: str, ctx: ToolContext) → str` | 全项目 grep，最多 100 条，排除 `.git`/`node_modules` |
| `glob` | `(pattern: str, ctx: ToolContext) → str` | glob 匹配文件，最多 200 条，相对路径输出 |
| `ls_dir` | `(path: str, ctx: ToolContext) → str` | 列目录，最多 100 条，显示类型和大小 |

- 所有工具用 `@tool` 定义，import 此模块即自动注册到 `ToolPool`
- 所有工具通过 `resolve_safe_path` 验证路径，越界返回 error 字符串而非抛异常
- 输出超限时截断并在结尾注明 `[截断：共 N 条，显示前 M 条]`

**验证：**
- [ ] `from sloth_agent.core.tools.builtin import readonly_fs` 后 `ToolPool` 含 6 个工具
- [ ] 越界路径返回 error 提示，不 crash
- [ ] `uv run pytest tests/core/test_readonly_fs_tools.py -v` 通过

---

### Task 7.C2: [Core] ROLE_BASE_TOOLS + AgentTemplate dataclass（¼ 天）

**状态：** ⬜

**文件：**
- `src/sloth_agent/core/agents/role_tools.py`（新建）
- `src/sloth_agent/core/agents/template.py`（新建）

**实现要点：**
- `ROLE_BASE_TOOLS: dict[str, list[str]]`：
  ```python
  ROLE_BASE_TOOLS = {
      "lead":       ["read", "grep"],
      "bazi":       ["read", "grep"],
      "ziwei":      ["read", "grep"],
      "iching":     ["read", "grep"],
      "astrologer": ["read", "grep"],
      "fortune":    ["read", "read_range", "glob", "grep", "grep_repo", "ls_dir"],
  }
  ```
- `AgentTemplate` 纯 dataclass：`id: str`, `name: str`, `role: str`, `tools: list[str]`（个性化追加），`system_prompt: str`
- 不 import 任何 DB、HTTP 模块

**验证：**
- [ ] `from sloth_agent.core.agents.role_tools import ROLE_BASE_TOOLS; assert "lead" in ROLE_BASE_TOOLS`
- [ ] `from sloth_agent.core.agents.template import AgentTemplate` 无副作用

---

### Task 7.C3: [Core] run_tool_loop（function calling 循环，½ 天）

**状态：** ⬜

**文件：**
- `src/sloth_agent/core/brainstorm/tool_loop.py`（新建）
- `tests/core/brainstorm/test_tool_loop.py`（新建）

**实现要点：**
```python
async def run_tool_loop(
    messages: list[dict],          # chat history
    effective_tools: list[str],    # 当前 agent 可用工具白名单
    tool_pool: ToolPool,           # 工具注册表
    ctx: ToolContext,              # 路径/会话上下文
    llm_call: Callable,            # async fn(messages, tools_schema) → dict  (LLM 返回)
    max_iterations: int = 3,
) -> AsyncIterator[ToolLoopEvent]:
    """
    执行 function calling 循环，yield 事件流（tool_call、tool_result、text_token、done）。
    - 每次迭代：调用 llm_call → 有 tool_calls → 执行 → 注入 role=tool 消息 → 继续
    - 超出 max_iterations 或无 tool_calls → 终止并 yield done
    - 非白名单工具调用 → yield tool_error(name, "not allowed") → 继续循环
    - 纯 Python，不 import fastapi / sqlalchemy / typer
    """
```

- `ToolLoopEvent` 为 Union 类型：`ToolCallEvent | ToolResultEvent | TextTokenEvent | DoneEvent`
- `llm_call` 参数让 Desktop 和 CLI 各自注入不同的 LLM 实现，解耦

**验证：**
- [ ] mock `llm_call` 返回 tool_calls → 工具执行 → 结果注入 → 循环终止
- [ ] 第 4 次 tool-call 被截断，yield `done`
- [ ] 非白名单工具 yield `tool_error`，不 crash
- [ ] `uv run pytest tests/core/brainstorm/test_tool_loop.py -v` 通过

---

### Task 7.C4: [Core] ContextEngine（½ 天）

**状态：** ⬜

**文件：**
- `src/sloth_agent/core/context/engine.py`（新建）
- `tests/core/context/test_context_engine.py`（新建）

**实现要点：**
- `ContextEngine` 继承 `sloth_agent.core.context_window.ContextWindowManager`
- `build(messages: list[dict], mode: str, policy: ContextPolicy) → ContextResult`
  - `model_visible_context`: 最终注入 LLM 的消息列表
  - `runtime_only_context`: 不注入模型但用于 UI/日志的元数据
  - `diagnostics`: `{token_utilization, compression_ratio, truncation_ratio}`
- `protect_reply_chains(messages)`：沿 `parent_message_id` 回溯祖先链，保护引用链不被截断
- 超预算降级策略复用 CLI `ContextWindowManager` 的摘要压缩，补充可解释错误码
- Iter-7 仅接入 Brainstorm（`mode="brainstorm"`），Chat/Autonomous 后续复用

**验证：**
- [ ] 相同输入 + policy → 构建结果稳定（确定性）
- [ ] `protect_reply_chains` 保留祖先消息，不因 token 预算截断引用链
- [ ] `uv run pytest tests/core/context/test_context_engine.py -v` 通过

---

### Task 7.D0: Desktop 适配 — 工具注册接线（¼ 天）

**状态：** ⬜

**文件：**
- `backend/app/services/brainstorm.py`（修改）
- `backend/app/services/agent.py`（修改）

**实现要点：**
```python
# brainstorm.py 中
from sloth_agent.core.tools import ToolPool
from sloth_agent.core.tools.builtin import readonly_fs  # import 即注册
from sloth_agent.core.brainstorm.tool_loop import run_tool_loop, ToolContext

# agent.py 中
from sloth_agent.core.agents.role_tools import ROLE_BASE_TOOLS

def get_effective_tools(role: str, agent_tools: list[str]) -> list[str]:
    base = ROLE_BASE_TOOLS.get(role, [])
    return list(dict.fromkeys(base + agent_tools))  # 去重，保序
```

- `BrainstormEngine` 的 agent 发言改为调用 `run_tool_loop`，注入 `LLMAdapter.chat` 和当前 `ToolContext`
- 将 `run_tool_loop` yield 的事件映射到已有 SSE 事件格式（`tool_call`, `tool_result`, `message_token`, `message_done`）

**验证：**
- [ ] Brainstorm 讨论仍正常触发（现有集成测试不回归）
- [ ] `ROLE_BASE_TOOLS` import 来自 core，不再在 Desktop 中重复定义

---

### Task 7.D1: AgentTemplate.tools DB 字段 + seed 更新（¼ 天）

**状态：** ⬜

**文件：**
- `backend/app/models.py`
- `backend/app/services/agent.py`
- `alembic/versions/` — 新迁移文件

**实现要点：**
- `AgentTemplate` ORM 模型新增 `tools: str`，默认 `"[]"`
- 语义：仅存 agent 个性化追加能力，不重复存 role 基础工具
- `seed_*_agents()` 保持 `tools="[]"`（role 基础工具由 core 定义）
- `GET /api/settings/agents/{id}` 返回：
  ```json
  {
    "role_tools": ["read", "grep"],
    "agent_tools": [],
    "effective_tools": ["read", "grep"]
  }
  ```

**验证：**
- [ ] Alembic 迁移执行成功，不破坏现有数据
- [ ] `effective_tools` 计算正确（role + agent 合并，无重复）

---

### Task 7.D2: BrainstormEngine 委托 core（½ 天）

**状态：** ⬜

**文件：**
- `backend/app/services/brainstorm.py`（重构）
- `backend/tests/test_brainstorm_context_integration.py`（新建）

**实现要点：**
- `BrainstormEngine._agent_turn()` 方法：
  1. 调用 `backend/app/services/context.py` 构建 `ContextEngine` 上下文
  2. 调用 `run_tool_loop(messages=context.model_visible_context, effective_tools=..., llm_call=llm_adapter.chat, ...)`
  3. 将 `ToolLoopEvent` 映射到 SSE 事件
- `backend/app/services/brainstorm.py` 中不再有直接的 LLM HTTP 调用或 tool_calls 解析逻辑
- 保留 SSE 传输、持久化（保存 Messages、BrainstormSession 更新）等 Desktop 专属代码

**验证：**
- [ ] Brainstorm 流式讨论正常工作（现有 SSE 事件格式不变）
- [ ] tool_call SSE 事件正确触发
- [ ] `uv run pytest backend/tests/ -v` 全通过

---

### Task 7.F: 前端 Tool 展示与 ToolCallBlock（½ 天）

**状态：** ⬜

**文件：**
- `frontend/src/components/AgentDetail.tsx`（修改）
- `frontend/src/components/ToolCallBlock.tsx`（新建）
- `frontend/src/components/BrainstormStreamBubble.tsx`（修改）

**实现要点：**
- AgentDetail：新增 **Tools** 区块，显示 `effective_tools`（只读 chips）
  - 颜色分两类：role 工具（灰色 chip）/ agent 追加工具（绿色 chip）
  - 数据来自 `GET /api/settings/agents/{id}` 返回的 `effective_tools`
- ToolCallBlock：
  - 订阅 `tool_call` SSE 事件（`{tool_name, args, result, success}`）
  - 在消息气泡内折叠展示，默认收起；header 显示 `🔧 tool_name` + 状态图标
  - 展开后显示 args（JSON）和 result 预览（前 200 字符）
- BrainstormStreamBubble：在流式气泡末尾追加 ToolCallBlock（按 message_id 聚合）

**验证：**
- [ ] AgentDetail 展示 role + agent 合并后的工具能力（带颜色区分）
- [ ] Brainstorm 触发 tool-call 后消息气泡内出现 ToolCallBlock
- [ ] ToolCallBlock 可折叠/展开，显示 args 和 result 预览

---

### Iter-7 验收标准（汇总）

- [ ] `sloth_agent.core.tools.ToolPool` 含 6 个只读工具（import `readonly_fs` 后自动注册）
- [ ] `ROLE_BASE_TOOLS` 在 `sloth_agent.core.agents.role_tools` 中定义，CLI 和 Desktop 均可 import
- [ ] `lead` 角色无法调用 `glob` / `grep_repo`（白名单来自 core，Desktop 仅传参）
- [ ] `run_tool_loop` 在 core 层，Desktop `brainstorm.py` 仅持有 SSE 传输 + 持久化
- [ ] `ContextEngine.build(...)` 三段输出 + diagnostics 稳定（确定性）
- [ ] `sloth_agent.core.*` 不 import `backend.*`、`typer`、`fastapi`、`sqlalchemy`（无 Desktop 依赖）
- [ ] `uv run pytest tests/ -v` 全通过（core 单元测试）
- [ ] `uv run pytest backend/tests/ -v` 全通过（Desktop 集成测试）

---

## Iter-8: 写 Tools + 受限执行器 + Toolset 抽象 + Agent 对象模型 + eval（5 天）

> **范围扩展（2026-05-07）：** 原计划仅做写工具，现叠加 ADK 对标 Phase A（Pydantic schema、BaseToolset、AgentConfig、model 继承链）和工具能力 eval。
> 新增任务详情：`docs/changes/adk-optimization/tasks.md` § Phase A
> Agent 的讨论结论落地为沙箱中的代码文件、文档、测试用例。用户审查后手动应用到项目。

### Task 8.0: 写 Tools 注册 + tool-whitelist.yaml

**状态：** ⬜

**描述：** 注册写 Tools 和受限执行 Tools。ToolPermissionGate 完善写路径路由。命令白名单由配置文件定义。

**文件：**
- `backend/app/services/tools.py` — 扩展，注册写/执行 Tools
- `tool-whitelist.yaml` — 新建（项目根目录）
- `backend/app/llm/tool_whitelist.py` — 新建白名单加载器

**写 Tools 注册：**
- `write_file(path: str, content: str)` → 写入沙箱目录，ToolPermissionGate 强制路径映射到 `brainstorm-sessions/{session_id}/`
- ToolPermissionGate 写路径规则：所有写操作的目标路径自动加沙箱前缀

**受限执行 Tools 注册：**
- `run_tests(test_dir: str = ".")` → 在沙箱目录执行白名单测试命令
- `run_linter(file_path: str)` → 对沙箱文件执行白名单 linter
- `run_build()` → 在沙箱目录执行白名单构建命令

**tool-whitelist.yaml 格式：**
```yaml
commands:
  test:
    - cmd: "npm test"
      working_dir: "."
    - cmd: "pytest"
      working_dir: "."
    - cmd: "cargo test"
      working_dir: "."
    - cmd: "go test ./..."
      working_dir: "."
  lint:
    - cmd: "npx eslint {file}"
      working_dir: "."
    - cmd: "ruff check {file}"
      working_dir: "."
  build:
    - cmd: "npm run build"
      working_dir: "."
    - cmd: "cargo build"
      working_dir: "."
```

**实现要点：**
- 白名单加载器解析 YAML → 构建命令索引
- 执行前验证：命令必须在白名单中，参数替换 `{file}` 占位符，working_dir 加上沙箱前缀
- 不使用 `subprocess.run(shell=True)`，使用 `subprocess.run([cmd, ...args], cwd=sandbox_dir)`
- 执行超时：test 60s, lint 30s, build 120s
- 执行结果（stdout + stderr + exit_code）返回给 Agent 和前端

**验证：**
- [ ] `write_file("auth/jwt-middleware.ts", content)` → 文件出现在 `brainstorm-sessions/{id}/auth/jwt-middleware.ts`
- [ ] `run_tests()` → 在沙箱目录执行 `npm test`
- [ ] 尝试执行白名单外命令 → ToolPermissionGate 拦截，返回错误信息
- [ ] 命令超时 → 进程被 kill，返回超时错误

### Task 8.0b: 受限网络只读工具（websearch/webfetch）

**状态：** ⬜

**描述：** 在不突破安全边界的前提下引入网络检索能力，仅用于补充外部事实，结果必须可追溯。

**文件：**
- `backend/app/services/tool_defs.py` — 新增 `websearch`、`webfetch`
- `backend/app/core/network_guard.py` — 新建，网络访问策略校验（协议、域名、地址段）
- `backend/app/core/tool_engine.py` — 统一错误码映射与审计记录钩子
- `backend/tests/test_tool_network_guard.py` — 新增网络策略测试

**实现要点：**
- `websearch(query: str, top_k: int = 5)`：
  - `top_k` 范围 1-10
  - 返回结构包含 `title`, `url`, `snippet`, `source` 字段
  - 最多返回 5 条（默认）
- `webfetch(url: str)`：
  - 仅允许 `https://`
  - 禁止访问回环、本地链路、私网地址（如 `127.0.0.1`, `localhost`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`）
  - 按 allowlist/denylist 规则校验域名
  - 连接超时 10s，整体超时 30s
  - 响应体上限 300KB，超限截断并标记
  - 仅提取可读文本，忽略二进制内容

**标准错误码（给前端和模型可解析）：**
- `NETWORK_FORBIDDEN_SCHEME`
- `NETWORK_FORBIDDEN_HOST`
- `NETWORK_DNS_RESOLUTION_FAILED`
- `NETWORK_TIMEOUT`
- `NETWORK_RESPONSE_TOO_LARGE`
- `NETWORK_FETCH_FAILED`

**审计字段（每次 tool_call 必填）：**
- `tool_name`
- `agent_id`
- `session_id`
- `request_url`（webfetch）/`query`（websearch）
- `resolved_ip`（可解析时）
- `status_code`（webfetch）
- `duration_ms`
- `bytes_received`
- `result_count`（websearch）
- `error_code`（失败时）
- `created_at`

**可执行验收清单：**
- [ ] `webfetch("http://example.com")` → 拒绝，`error_code=NETWORK_FORBIDDEN_SCHEME`
- [ ] `webfetch("https://127.0.0.1:8080")` → 拒绝，`error_code=NETWORK_FORBIDDEN_HOST`
- [ ] `webfetch` 请求超过 30s → 终止并返回 `NETWORK_TIMEOUT`
- [ ] 响应体超过 300KB → 截断并返回 `NETWORK_RESPONSE_TOO_LARGE`（或 `truncated=true`）
- [ ] `websearch(query, top_k=20)` → 参数校正或拒绝（最终 `top_k<=10`）
- [ ] `websearch` 结果每条都包含 `url` 与 `source`，可追溯
- [ ] 任一网络 tool 失败时，SSE `tool_call.success=false` 且包含 `error_code`
- [ ] 审计日志中可按 `session_id + agent_id + tool_name` 检索到完整记录

### Task 8.1: apply API + discussion_end 扩展

**状态：** ⬜

**描述：** 沙箱文件应用到项目的 API。discussion_end SSE payload 新增 sandbox_files 字段。

**文件：**
- `backend/app/routers/brainstorm.py` — 新增 apply-file / apply-all 端点
- `backend/app/services/sandbox.py` — 扩展，新增 apply_file / apply_all 方法
- `backend/app/services/brainstorm.py` — 修改 discussion_end payload

**API 规格：**
1. `POST /api/brainstorm-sessions/{session_id}/apply-file`
   - Body: `{ "file_path": "auth/jwt-middleware.ts" }`
   - 流程: 验证沙箱文件存在 → 复制到项目目录对应路径 → BrainstormFile 标记 applied → 返回结果
2. `POST /api/brainstorm-sessions/{session_id}/apply-all`
   - 流程: 遍历所有沙箱文件 → 逐文件复制 → 返回 `{applied: [...], failed: [...], skipped: [...]}`
3. discussion_end payload 扩展: `{summary, message_count, sandbox_files: ["auth/jwt-middleware.ts", "docs/architecture.md"]}`

**实现要点：**
- 复制前检查目标路径是否已有文件 → 已有则标记冲突，不覆盖
- 冲突由用户手动处理
- applied 状态保存在 BrainstormFile 记录或内存标记中

**验证：**
- [ ] `apply-file` → 文件从沙箱复制到项目正确路径
- [ ] 目标路径已有同名文件 → 返回冲突错误，不覆盖
- [ ] `apply-all` → 所有文件应用，返回统计
- [ ] `discussion_end` SSE payload 含 sandbox_files 字段

### Task 8.2: SandboxFileViewer 组件

**状态：** ⬜

**描述：** 前端组件显示沙箱文件树和内容预览。支持逐文件审核和应用到项目。

**文件：**
- `frontend/src/components/SandboxFileViewer.tsx` — 新建
- `frontend/src/components/BrainstormArea.tsx` — 修改，集成文件查看器

**实现要点：**
- 左侧文件树：递归展示目录结构，文件类型图标（📁/📄/🧪/⚙）
- 已应用文件标记为 ✓ applied（绿色）
- 新文件标记为 "new" badge
- 右侧内容预览：
  - 选中文件 → 显示内容（语法高亮，可用简单的 `<pre>` + 关键词着色）
  - 顶部工具栏：文件名 + [Apply This File] 按钮
- 底部 [Apply All] 按钮 → 一键应用所有新文件
- 文件类型图标映射：".ts"/".tsx"/".js"→📄, ".py"→📄, ".md"→📝, ".test.ts"→🧪, ".yaml"/".json"→⚙

**验证：**
- [ ] 沙箱有文件 → SandboxFileViewer 显示文件树
- [ ] 点击文件 → 内容预览区显示文件内容
- [ ] [Apply This File] → 调用 API → 文件标记为 applied
- [ ] [Apply All] → 调用 API → 所有新文件标记为 applied
- [ ] 无文件时显示空状态

---

## Iter-9: 异步自主模式 + Hooks 系统 + eval（5 天）

> **范围扩展（2026-05-07）：** 原计划仅做异步自主模式，现叠加 ADK 对标 Phase B（HookManager、8 种 HookPoint、tool/agent hook 接入）和讨论质量 eval。
> 新增任务详情：`docs/changes/adk-optimization/tasks.md` § Phase B
> 用户提一个问题后离线，Agent 自主讨论并产出结果。BrainstormEngine 从"SSE 驱动"重构为"生成即写 DB"模式。

### Task 9.0: BrainstormEngine — 生成即写 DB 重构

**状态：** ⬜

**描述：** 将 BrainstormEngine 的核心生成逻辑从"SSE 驱动"解耦。讨论可以在无 SSE 连接时运行，消息直接写入 DB。SSE 端点变为 DB 变更的实时投影。

**文件：**
- `backend/app/services/brainstorm.py` — 重构 BrainstormEngine
- `backend/app/routers/brainstorm.py` — SSE 端点改为 DB 订阅模式

**实现要点：**
- BrainstormEngine.run_discussion(session_id, topic, reply_to_message_id) → 内部循环生成消息 → 每条消息立即写 DB → 写完后通知
- SSE 端点模式：BrainstormEngine 运行 → 消息写 DB → 通过 asyncio.Queue 推送给可能连接的 SSE consumer
- 无 SSE consumer 时讨论仍正常运行（Queue 无 reader，消息跳过推送但 DB 写入正常）
- `started_by` 字段：用户手动触发为 "user"，Iter-9 异步触发为 "auto"
- 讨论结束后 `notification_sent` 标记

**验证：**
- [ ] SSE 无连接时发起讨论 → 消息写入 DB → 讨论正常结束
- [ ] SSE 有连接时 → 消息同步流式推送给前端
- [ ] 讨论中 SSE 断连 → 讨论继续 → 重连后恢复

### Task 9.1: start-async + status API

**状态：** ⬜

**描述：** 异步讨论的启动和状态查询 API。

**文件：**
- `backend/app/routers/brainstorm.py` — 新增 start-async / status 端点

**API 规格：**
1. `POST /api/brainstorm-sessions/{session_id}/start-async`
   - Body: `{ "topic": "我们应该用 JWT 还是 Session?" }`
   - 流程: 验证会话存在 → 创建 asyncio.Task 运行 BrainstormEngine → 立即返回 `{started: true, session_id}`
2. `GET /api/brainstorm-sessions/{session_id}/status`
   - 返回: `{status, message_count, round, active_agents: [...], started_by, created_at, ended_at}`

**实现要点：**
- asyncio.Task 引用存储在 app.state 的 dict 中（key=session_id）
- status API 直接从 DB 查询最新状态（不依赖内存中的 Task）
- active_agents: 查询该轮有发言记录的 Agent

**验证：**
- [ ] `start-async` → 返回 202 → 讨论在后台运行
- [ ] `status` → 返回正确的 message_count, round, active_agents
- [ ] 讨论未开始时 start-async → 返回 409 Conflict

### Task 9.2: 前端 — 断线恢复 + 浏览器通知

**状态：** ⬜

**描述：** 前端支持离开页面后恢复讨论状态。讨论完成时浏览器通知。

**文件：**
- `frontend/src/stores/brainstormStore.ts` — 扩展断线恢复 + 轮询逻辑
- `frontend/src/components/BrainstormArea.tsx` — 集成恢复和通知

**实现要点：**
- 页面加载时：检查是否有 active 状态的 Brainstorm 会话 → 调用 status API → 恢复消息列表
- 讨论进行中：每 5s 轮询 status API（只在非 SSE 连接模式时启用）
- 页面可见性变化（visibilitychange）：页面重新可见时立即检查状态 + 恢复消息
- 浏览器 Notification API：
  - 页面加载时请求通知权限
  - 讨论结束 → `new Notification("Brainstorm 讨论完成", {body: session.title, icon: "/icon.png"})`
  - 页面标题闪烁：`document.title = "🔔 讨论完成 - Sloth"` → 2s 后恢复
- 页面内通知：讨论结束时 TopBar 或消息列表顶部显示 "讨论已完成，查看结果" banner

**验证：**
- [ ] 异步讨论进行中 → 关闭页面 → 5 分钟后打开 → 讨论状态恢复
- [ ] 讨论结束 → 浏览器通知弹出（如已授权）
- [ ] 讨论结束 → 页面标题闪烁
- [ ] 多个异步讨论同时进行 → 各自状态独立

---

## Iter-10: events 全量 + Agent 树 + transfer + eval（6 天）

> **新增（2026-05-07）：** ADK 对标 Phase C。
> 详细任务：`docs/changes/adk-optimization/tasks.md` § Phase C + Iter-10
> 关联 spec: `specs/core/events/spec.md`（15KB）、`specs/coordination/spec.md` § Agent 树

### 核心交付

1. **EventBus 基建**：CloudEvents 事件模型 + 31 种事件类型 + 通配符订阅 + 同步/异步双队列 + JSONL 持久化 + DLQ + 背压控制
2. **EventHandler 处理器**：AutoReportHandler、BudgetAlertHandler、HookAdapter（EventBus ↔ HookManager 桥接）
3. **WorkflowRule 声明式规则**：trigger(通配符) + action + condition + cooldown
4. **AgentTreeManager**：build_tree / find_agent / walk_depth_first / validate（循环引用 + 重名检测）
5. **TransferToAgentTool**：LLM 可见的 transfer 工具，agent_name enum 防幻觉
6. **Agent-as-Tool**（基础）：Transfer 做完后封装为工具模式
7. **eval: Agent 协作评估**：8 个多 Agent 场景，验证 transfer 正确性

### 关键设计决策

- EventBus 禁止 handler 中 publish（防级联风暴）
- 有界队列 maxsize=256 + drop-oldest 背压
- Agent 树与现有平铺 Team 共存（渐进迁移）

---

## Iter-11: coordination 全量 + delta state + Agent-as-Tool + YAML + rewind + eval（6 天）

> **新增（2026-05-07）：** ADK 对标 Phase D。
> 详细任务：`docs/changes/adk-optimization/tasks.md` § Phase D + Iter-11
> 关联 spec: `specs/core/coordination/spec.md`（16KB）、`specs/session/spec.md`

### 核心交付

1. **Coordinator + TaskDAG**：拓扑分层执行、层内并行（asyncio.gather）、依赖满足检测
2. **LaneManager**：同 lane 串行、异 lane 并行、背压策略（drop_oldest/drop_newest/reject）
3. **MessageBus**：Agent 间点对点 + 广播通信、幂等去重、TTL 清理
4. **WorktreeManager**：Git worktree 创建/清理/文件变更追踪
5. **ConflictDetector**：文件级 + 行级冲突检测
6. **失败恢复**：L1 重试 / L2 重规划 / L3 分解 + CheckpointManager + StuckDetector
7. **Runner 重构**：独立调度器，BrainstormEngine 退化为 SequentialFlow
8. **Session delta state**：delta-tracking dict + commit/rollback + rewind
9. **Agent-as-Tool**（完整）：子 agent 包装为工具、结果返回封装
10. **YAML from_config**：从 YAML 加载 Agent 树配置
11. **eval: 编排效率评估**：5 个并行 DAG 场景

---

---

## Iter-12: Memory Foundation（5 天）

> **变更来源:** `docs/changes/memory-architecture/`
> 参考: ADK BaseMemoryService、Karpathy LLM Wiki、agentmemory

### 核心交付

1. **Memory 数据库**：SQLite FTS5 全文索引 + chromadb collection + Episodic/Semantic ORM
2. **Ingest Pipeline**：session 结束 → LLM 生成摘要/key_points/entities → 写入 Episodic Memory
3. **Consolidation**：从 Episodic 提取跨 session 事实 → 写入 Semantic Memory → 更新索引
4. **Confidence Scoring**：Ebbinghaus 遗忘曲线，按 fact 类型不同衰减速率（架构 0.01/天、bug 0.1/天）
5. **Hybrid Search**：BM25 (FTS5) + vector (chromadb) → RRF 融合，top_k=10
6. **Context Injection**：Agent prompt 自动注入 `[Relevant Memory]` block（含 confidence 标注）
7. **Memory API**：`POST /api/memory/sessions/{id}/ingest`、`POST /api/memory/consolidate`、`GET /api/memory/search`

### 关键设计决策

- Memory 独立数据库（`memory/chroma/` + `memory/fts.db`），不混入业务 DB
- Embedding 先用 all-MiniLM-L6-v2（本地轻量），预留 API 切换
- Iter-12 手动触发（API call），Iter-13 接 hooks 自动化
- 不替代现有 `Message` 表，memory 是额外的索引层

---

## Iter-13: Memory Advanced（5 天）

> **变更来源:** `docs/changes/memory-architecture/`

### 核心交付

1. **Knowledge Graph**：实体提取 + 类型化关系（uses/depends_on/contradicts/caused）+ networkx 图遍历
2. **Supersession**：新声明可 supersede 旧声明，旧记录保留完整 provenance chain
3. **Crystallization**：Brainstorm 讨论 → LLM 生成 structured digest → wiki + facts + graph update
4. **Procedural Memory**：从重复 tool_call 序列提取 workflow/pattern → 匹配 trigger → 自动建议
5. **Self-Healing**：lint（broken refs/orphan entities/stale facts）→ auto-fix + 定时 decay→archive
6. **Event-Driven**：接入 Iter-9 hooks（on_session_end→auto-ingest）+ Iter-10 EventBus（session.completed→ingest）+ 定时 consolidation
7. **扩展 API**：graph/traverse、crystallize、procedures、lint、stats

---

## Iter-14+ 候选池

> **新增（2026-05-07）：** ADK 对标 Phase E。
> 按收益排序，实施时按 delta 流程创建独立变更。

| # | 模块 | spec | 核心交付 | 约天数 |
|---|------|------|---------|--------|
| 1 | `eval/` 体系化 | 5971B | UserSimulator + LLM-as-judge + rubric + trajectory evaluator | 3 |
| 2 | `errors/` 错误处理 | 1134B | CircuitBreaker + 重试接入 Desktop、统一错误码 | 1 |
| 3 | `cost/` 费用追踪 | 961B | BudgetAwareRouter 接入 Desktop、费用 dashboard | 1 |
| 4 | `observability/` | 370B | OpenTelemetry tracing + metrics + 调用链 | 2 |
| 5 | `sandbox/` 容器 | 526B | ContainerCodeExecutor、GkeCodeExecutor | 2 |
| 6 | `skills/` 插件 | 1161B | PluginManager + 第三方插件加载 | 2 |
| 7 | `runtime/` processor | 2430B | 12+ 可组合 processor 管道 | 2 |
| 8 | `coordination/` A2A | §2.3 | A2A adapter + agent card 发布 | 2 |

---

## 跨迭代关注

### 端口与进程管理
- 后端固定使用 `127.0.0.1:8080`
- Tauri 启动前 `taskkill` 清理残留 uvicorn
- Sidecar 崩溃检测：前端定时 health check + 自动重启提示

### 测试策略
- 每个后端 router 至少 1 个集成测试
- 前端不写测试（MVP 阶段）
- 每个迭代结束时手动 smoke test（对照 Iter QA checklist）

### 提交策略
- 每个 Task 完成即提交（atomic commits）
- 迭代结束时打 tag（`v0.5.0-iter4`, `v0.5.0-iter5`, ...）

### Brainstorm 模式关键设计决策
- **沙箱隔离是硬约束**：所有 Agent 写操作路由到 `brainstorm-sessions/{session_id}/`，项目文件只读
- **单一 SSE 连接复用**：所有 Agent 事件通过一个 SSE 连接推送，不创建 N 个并发流
- **冷却计时器自然结束**：不依赖硬编码轮数限制，Agent 沉默触发冷却 → 确认 → 结束
- **命令白名单，非任意 shell**：受限执行器只执行 `tool-whitelist.yaml` 中定义的命令
- **架构可扩展**：DecisionStrategy ABC 支持未来替换投票策略；ToolRegistry 支持增量注册
- **共享 Context Engine 延至 Iter-7**：从原计划 Iter-5 后移，与读 Tools 一起交付，避免 Iter-5 过载

---

*Plan 版本: 5.2 — 2026-05-03*
*变更: v5.4 — 2026-05-07 新增 Memory 架构重设计（Iter-12 Foundation + Iter-13 Advanced），参考 ADK + Karpathy LLM Wiki + agentmemory。四层 consolidation pipeline (Working→Episodic→Semantic→Procedural) + hybrid search + confidence scoring + knowledge graph + crystallization。Iter-14+ 候选池（eval 体系化 + errors + cost + observability + sandbox + plugin + pipeline + A2A）。详细变更见 `docs/changes/adk-optimization/` 和 `docs/changes/memory-architecture/`。*
