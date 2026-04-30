# Sloth Agent 桌面版 MVP 实现计划

> Spec: `docs/specs/20260425-mvp-desktop-app-spec.md`
> Brainstorm Spec: `docs/specs/20260430-brainstorm-mode-spec.md`
> Arch: `docs/design/desktop-app-architecture.md`
> 日期: 2026-04-25
> 更新: 2026-04-30
> 状态: IN PROGRESS

---

## 迭代概览

| 迭代 | 天数 | 范围 | 关键产出 |
|------|------|------|---------|
| Iter-1 | Day 1-3 | 项目外壳 + Inspiration CRUD | 4 列布局 + 数据库 + API | ✅ |
| Iter-2 | Day 4-7 | Settings + 聊天 + 默认 Agent | LLM 管理页 + 消息流 + SSE 流式 | ✅ |
| Iter-3 | Day 8-14 | Agent Pool 初始化 + Agent 管理 + Right Panel | 5 内置 Agent + Team API + Right Panel 团队面板 | ✅ |
| Iter-4 | Day 15-17 | Brainstorm 会话沙箱 | SandboxManager + BrainstormSession CRUD + 前端列表 | ⬜ |
| Iter-5 | Day 18-20 | 讨论引擎 — 两轮投票 + SSE | BrainstormEngine + DecisionStrategy + CoolingTimer | ⬜ |
| Iter-6 | Day 21-23 | 彩色线程 UI | BrainstormArea + 色彩竖线 + 回复标签 | ⬜ |
| Iter-7 | Day 24-26 | 读 Tools + 上下文引擎 | ToolRegistry + ToolPermissionGate + ContextWindowManager | ⬜ |
| Iter-8 | Day 27-29 | 写 Tools + 受限执行器 | 写 Tools + tool-whitelist.yaml + SandboxFileViewer | ⬜ |
| Iter-9 | Day 30-32 | 异步自主模式 | start-async + 断线恢复 + 浏览器通知 | ⬜ |

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

**状态：** ⬜

**描述：** 新增两张表支持 Brainstorm 会话管理。brainstorm_files 表在 Iter-4 建好但实际写入延至 Iter-8。使用 Alembic 迁移管理 schema 变更。

**文件：**
- `backend/app/models.py` — 新增 BrainstormSession, BrainstormFile 模型
- Alembic 迁移文件 — `alembic/versions/xxxx_brainstorm_sessions.py`

**实现要点：**
- BrainstormSession 字段: id, inspiration_id, title, status("active"|"cooling_down"|"ended"|"summarized"), sandbox_path, max_messages(500), cooldown_seconds(5), message_count(0), summary(None), started_by(None), notification_sent(False), created_at, ended_at
- BrainstormFile 字段: id, session_id(FK), file_path, content, created_by(FK→inspiration_agents), file_type("code"|"doc"|"test"|"config"|"other"), created_at
- status 字段 default="active"，message_count default=0
- 迁移文件含 upgrade() 和 downgrade()

**验证：**
- [ ] 运行 Alembic 迁移 → 两张表创建成功
- [ ] `alembic downgrade -1` → 表删除，可回滚

### Task 4.1: SandboxManager 服务

**状态：** ⬜

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

**状态：** ⬜

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

**状态：** ⬜

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

---

## Iter-5: 讨论引擎 — 两轮投票 + SSE 流式（3 天）

> 后端讨论引擎。多个 Agent 并行发言，冷却计时器自然结束讨论。前端不在此迭代做彩色 UI（留给 Iter-6），只做基础 JSON 流式展示。

### Task 5.0: Messages 表扩展（Alembic 迁移）

**状态：** ⬜

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

**状态：** ⬜

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
   - 达到 max_messages(500) → 硬截断 → ENDED
   - 用户发新消息 → round_aborted → ENDED

4. **错误处理：**
   - 单个 Agent 超时/失败 → 重试 2 次 → 仍失败跳过
   - 所有 Agent 全失败 → 讨论终止

**验证：**
- [ ] 模拟 3 个 Agent 讨论 → Round 1 收集意向 → YES 的进 Round 2
- [ ] 5s 无人发言 → 冷却开始 → 3s 确认 → 讨论结束
- [ ] Agent 超时 → 重试 → 最终跳过，不影响其他 Agent

### Task 5.2: SSE Discuss 端点

**状态：** ⬜

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
max_reached:      {limit: 500}
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

**状态：** ⬜

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

## Iter-6: 彩色线程 UI（3 天）

> 前端 Brainstorm 专用视图。颜色区分线程，用户可指定回复目标。纯前端工作，后端无变更。

### Task 6.0: BrainstormMessage 组件 — 色彩竖线 + 回复标签

**状态：** ⬜

**描述：** 替换基础消息气泡为 Brainstorm 专用气泡。包含线程色彩竖线、回复标签、Agent 信息行。

**文件：**
- `frontend/src/components/BrainstormMessage.tsx` — 新建
- `frontend/src/components/BrainstormArea.tsx` — 修改集成新组件

**实现要点：**
- 色彩生成：`const threadColor = hsl(hash(root_message_id) % 360, 45%, 55%)`
- 根消息 ID 计算：若无 parent_message_id → 自身为根；若有 → 递归找到最顶层根消息
- 4px 宽色彩竖线在气泡左侧，`border-left: 4px solid threadColor`
- 回复标签格式：`回复 {agent_number} · "{被回复消息内容前30字}"`
- 所有消息左对齐，无缩进
- Agent 信息行：avatar(28×28, role→letter) + agent_name + 时间
- Round 1 意向状态：头像旁显示 "thinking..." / "跳过"

**验证：**
- [ ] 两个不同根线程的消息颜色不同
- [ ] 同一线程下回复消息颜色与根消息一致
- [ ] 回复消息显示回复标签
- [ ] 无 parent_message_id 的消息不显示回复标签和竖线

### Task 6.1: BrainstormInput 组件 — 回复引用

**状态：** ⬜

**描述：** Brainstorm 专用输入组件。支持泛回复和指定回复两种模式。

**文件：**
- `frontend/src/components/BrainstormInput.tsx` — 新建
- `frontend/src/components/BrainstormArea.tsx` — 集成输入组件

**实现要点：**
- 默认模式：泛回复（parent_message_id = NULL），输入框无标签
- Hover 消息 → 显示回复按钮（ghost 样式，消息右上角）
- 点击回复按钮 → 输入框上方出现回复标签："回复 {agent_number} · "{原文前30字}" [✕]"
- 点击 [✕] → 取消引用，回到泛回复模式
- 发送时带上 `parent_message_id`

**验证：**
- [ ] Hover 消息 → 回复按钮出现
- [ ] 点击回复 → 输入框上方出现回复标签
- [ ] 点击 [✕] → 标签消失
- [ ] 带 parent_message_id 发送 → 新消息正确关联到被回复消息

### Task 6.2: 模式开关 + 布局集成

**状态：** ⬜

**描述：** ChatArea TopBar 新增 Chat/Brainstorm 模式切换。Brainstorm 模式时 Col3 渲染 BrainstormArea。

**文件：**
- `frontend/src/components/ChatArea.tsx` — TopBar 新增模式开关
- `frontend/src/stores/uiStore.ts` — 扩展 chatMode: "chat" | "brainstorm"
- `frontend/src/components/BrainstormArea.tsx` — 完善整体布局

**实现要点：**
- TopBar 模式开关：两个 pill 按钮 `[Chat] [Brainstorm]`，选中态 accent 色背景
- 默认 "chat" 模式
- 切换 Brainstorm → Col3 渲染 BrainstormArea（含消息列表 + 输入框）
- Brainstorm 模式下隐藏 ChatArea 原有的 ChatInput
- 如果当前 Inspiration 无 Brainstorm 会话 → 提示创建
- 讨论结束时显示 Lead Agent 总结卡片（如 summary 不为 null）

**验证：**
- [ ] [Chat] [Brainstorm] 切换按钮可见
- [ ] 切换 Brainstorm → UI 变为 Brainstorm 布局
- [ ] 切换回 Chat → 恢复 Chat 布局
- [ ] 讨论自然结束后 → 显示总结卡片

---

## Iter-7: 读 Tools + 上下文引擎（3 天）

> Agent 可以读取项目文件作为讨论依据。引入 ToolPermissionGate 和 ContextWindowManager。

### Task 7.0: ToolRegistry + ToolPermissionGate

**状态：** ⬜

**描述：** 注册读 Tools（read_file, list_directory, grep, read_spec），ToolPermissionGate 强制读→项目目录、写→沙箱目录的路由规则。

**文件：**
- `backend/app/services/tools.py` — 新建 ToolRegistry + ToolPermissionGate

**实现要点：**
- ToolRegistry 注册 4 个读 Tools：
  - `read_file(path: str)` → 读项目根目录下的文件，返回内容
  - `list_directory(path: str)` → 列项目目录，返回 `[{name, type, size}]`
  - `grep(pattern: str, path: str)` → 在项目目录搜索，返回匹配行
  - `read_spec(path: str)` → 读 Markdown 设计文档
- ToolPermissionGate:
  - 读 Tools → 路径解析到项目根目录（`os.getcwd()`），禁止 `..` 越界
  - 写 Tools → 路径解析到沙箱目录（Iter-8 注册）
  - 所有路径操作前做 `os.path.realpath()` 验证，防止符号链接逃逸
- Tool 调用格式：System prompt 注入 Tool 列表 JSON → Agent 回复含 `[TOOL_CALL: tool_name, args]` → 引擎解析 → 执行 → 结果注入上下文

**验证：**
- [ ] `read_file("frontend/src/App.tsx")` → 返回项目文件内容
- [ ] `read_file("../../../etc/passwd")` → 被 ToolPermissionGate 拒绝（路径越界）
- [ ] 写文件 Tool 未注册 → 调用被拒绝

### Task 7.1: ContextWindowManager — Brainstorm 模式

**状态：** ⬜

**描述：** 引入上下文窗口管理，Brainstorm 模式实现 reply-to 链保护算法。Chat 模式先用现有扁平逻辑，如进度紧张可延后 Chat 模式重构。

**文件：**
- `backend/app/services/context.py` — 新建 ContextWindowManager
- `backend/app/services/brainstorm.py` — 修改，BrainstormEngine 集成 ContextWindowManager

**实现要点：**
- Reply-to 链保护算法:
  1. 取尾部 max_count 条消息
  2. 对每条尾部消息，沿 parent_message_id 链回溯，标记保护
  3. 最终保留: 尾部消息 ∪ 被保护祖先消息
- Chat 模式（暂不重构）：沿用现有扁平 `messages[-N:]` 截断
- 集成到 BrainstormEngine: 每轮开始时调用 `protect_reply_chains(messages, max_tokens)` 裁剪上下文

**验证：**
- [ ] 讨论 100 条消息，窗口设为 20 条 → 尾部 20 条存在
- [ ] 尾部某条回复的消息链上祖先（超过窗口的消息）被保留 → 上下文完整
- [ ] 孤立消息（无引用链）超过窗口的被丢弃

### Task 7.2: Agent Tool-call 循环

**状态：** ⬜

**描述：** Agent system prompt 注入可用 Tools 列表。Agent 在发言中可调用读 Tools。实现 tool_call → 执行 → 结果注入 → 继续生成的循环。每个 Agent 每轮最多 3 次 tool-call（防无限循环）。

**文件：**
- `backend/app/services/brainstorm.py` — 修改 TwoRoundVoting.generate_speeches()

**实现要点：**
- System prompt 末尾追加 Tool 列表（JSON 格式，含名称、参数、描述）
- Prompt 指令："你可以使用以下工具读取项目文件。工具调用格式: [TOOL_CALL: tool_name, {"arg": "value"}]"
- Round 2 发言循环：
  1. LLM 流式生成
  2. 检测到 `[TOOL_CALL: ...]` → 暂停生成 → 解析 → ToolPermissionGate 验证 → 执行
  3. Tool 结果注入上下文 → 继续生成
  4. 最多 3 个 tool-call，超过强制结束
- Tool-call 和结果不存储为独立 Message，而是附加在 Agent 消息的 content 中

**验证：**
- [ ] Agent 在讨论中说"让我看看现有代码" → `[TOOL_CALL: read_file, ...]` → 读取成功
- [ ] Tool 结果注入上下文 → Agent 基于文件内容继续发言
- [ ] Agent 尝试第 4 次 tool-call → 引擎阻止，强制结束本轮发言

### Task 7.3: 前端 — ToolCallBlock 组件

**状态：** ⬜

**描述：** 消息气泡内展示 Agent 的 tool-call 记录。折叠显示，点击展开查看详情。

**文件：**
- `frontend/src/components/ToolCallBlock.tsx` — 新建
- `frontend/src/components/BrainstormMessage.tsx` — 修改，集成 ToolCallBlock

**实现要点：**
- 解析消息 content 中的 `[TOOL_CALL: ...]` 和结果标记
- 折叠状态：显示 "📄 读取了 `frontend/src/components/App.tsx`" 或 "🔍 搜索了 `useState` in `frontend/src/`"
- 展开状态：显示文件内容摘要（前 20 行或匹配行）
- 样式：bg #f8f9fa, border-left 3px solid #6366f1, border-radius 4px, padding 8px 12px, 12px 字号

**验证：**
- [ ] Agent 消息含 tool-call → 气泡内显示折叠块
- [ ] 点击展开 → 显示读取内容摘要
- [ ] 多个 tool-call → 每个独立展示

---

## Iter-8: 写 Tools + 受限执行器（3 天）

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

## Iter-9: 异步自主模式（3 天）

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
- **ContextWindowManager 延至 Iter-7**：从原计划 Iter-5 后移，与读 Tools 一起交付，避免 Iter-5 过载

---

*Plan 版本: 4.0 — 2026-04-30*
*变更: Brainstorm 模式全面重规划。旧 Iter-4 stub (Tasks 4.0-4.6) 替换为完整 Iter-4 至 Iter-9 任务，对应 Brainstorm Spec `docs/specs/20260430-brainstorm-mode-spec.md`。新增: Iter-4 会话沙箱 (3 tasks), Iter-5 讨论引擎+SSE (3 tasks), Iter-6 彩色线程UI (3 tasks), Iter-7 读Tools+上下文 (3 tasks), Iter-8 写Tools+执行器 (3 tasks), Iter-9 异步自主模式 (3 tasks)。总迭代数从 4 扩展到 9。*
