# Sloth Agent 桌面版 MVP 实现计划

> Spec: `docs/specs/20260425-mvp-desktop-app-spec.md`
> Arch: `docs/design/desktop-app-architecture.md`
> 日期: 2026-04-25
> 更新: 2026-04-26
> 状态: IN PROGRESS

---

## 迭代概览

| 迭代 | 天数 | 范围 | 关键产出 |
|------|------|------|---------|
| Iter-1 | Day 1-3 | 项目外壳 + Inspiration CRUD | 4 列布局 + 数据库 + API |
| Iter-2 | Day 4-7 | Settings + 聊天 + 默认 Agent | LLM 管理页 + 消息流 + SSE 流式 |
| Iter-3 | Day 8-10 | Agent 管理 + 模型配置 | Right Panel + 多 Agent 协作 |

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

## Iter-3: Agent 管理 + 模型配置

> 前置: Iter-2 完成 LLM 池 + Agent 池 + Lead Agent 自动加入 Team

### Task 3.1: 后端 — Team 成员管理 API

**文件：**
- `backend/app/routers/agents.py` — Team 成员路由（操作 InspirationAgent 表）

**API 规格：**
1. `GET /api/inspirations/{id}/agents` — 返回该 Inspiration 的 Team 成员列表
2. `POST /api/inspirations/{id}/agents` — 从 Agent Pool 拉入一个 Agent 到 Team
   - Body: `{ template_id }` — Agent 池中的模板 ID
   - 继承模板的 name/role/model，后续可独立覆盖
3. `PATCH /api/inspirations/{id}/agents/{agent_id}` — 修改 Team 中 Agent 的模型或名称
   - Body: `{ model? , name? }`
   - model 从 Sloth LLM 池中选取
4. `DELETE /api/inspirations/{id}/agents/{agent_id}` — 从 Team 移除 Agent
   - Lead Agent (role="lead") 不可移除
5. `GET /api/settings/agents` — 获取可用的 Agent 模板列表（供 Add Agent 下拉）

**验证：**
- 从 Pool 拉入 Agent → Team 列表中出现
- 切换模型 → PATCH 成功，后续聊天使用新模型
- 尝试删除 Lead Agent → 返回错误

### Task 3.2: 前端 — Right Panel Team 管理

**文件：**
- `frontend/src/components/RightPanel.tsx` — 完整重写
- `frontend/src/components/AgentListItem.tsx` — 单个 Team 成员（NEW）
- `frontend/src/stores/agentStore.ts` — Zustand Team 状态（NEW）
- `src-tauri/src/lib.rs` — 添加 agent commands

**Rust Commands：**
```rust
list_agents(inspiration_id: String) -> Result<Vec<InspirationAgent>, String>
add_agent_to_team(inspiration_id: String, template_id: String) -> Result<InspirationAgent, String>
update_agent_model(agent_id: String, model: String) -> Result<InspirationAgent, String>
remove_agent_from_team(agent_id: String) -> Result<(), String>
```

**RightPanel 完整展现：**

```
┌──────────────────────────────────┐
│ Team                         [✕] │  ← header
├──────────────────────────────────┤
│                                  │
│ COLLABORATORS                    │  ← section 标题 11px, uppercase
│                                  │
│ 🟢 You (Owner)                   │  ← 当前用户, 绿色 dot
│                                  │
│ AGENTS                    1      │  ← section 标题 + 计数
│                                  │
│ ┌──────────────────────────────┐ │
│ │ 🤖 Lead Agent       🟢 idle  │ │  ← Team 成员（来自 Agent Pool）
│ │    lead                       │ │    头像 32×32 + 名字 + 角色 + 状态灯
│ │    Model: [DeepSeek V4 Pro ▾]  │ │    模型下拉从 LLM 池读取
│ │                              │ │    切换立即 PATCH
│ │    [Remove]                  │ │  ← Lead Agent 不显示此按钮
│ └──────────────────────────────┘ │
│                                  │
│ ─── Add from Agent Pool ───      │  ← 从 Agent 池中选择添加
│                                  │    (MVP 只有一个 Lead Agent, 此按钮暂 disabled)
└──────────────────────────────────┘
```

**AgentListItem 规格：**
- 28×28 头像：role icon + hash 色背景
- 第一行：Agent name (13px, 600) + Status dot (绿 idle / pulsating 绿 working / 灰 error)
- 第二行：role 名称 (11px, #9ea7b0)
- 第三行：Model 下拉框
  - 选项来自 Sloth LLM 池（`GET /api/settings/llm`）
  - 切换立即调用 `update_agent_model()`
  - 当前使用的模型默认选中
- hover 显示背景，active 有高亮边框
- Remove 按钮：Lead Agent (role="lead") 不显示，其他 Agent hover 时显示

**Add Agent 交互（从 Agent Pool 选取）：**
- 点击 "Add from Agent Pool" → 弹出下拉，显示 Agent 池中尚未加入 Team 的模板
- 每个模板显示：头像 + name + role + model
- 点击选中 → 调用 `add_agent_to_team()` → 列表中新增
- MVP 阶段 Pool 中只有 Lead Agent（已自动加入），所以此按钮 disabled
- 未来 Pool 中有多个模板时，可随时拉入

**状态联动：**
- 发送消息 → 参与聊天的 Agent status 变 "working"
- 回复完成 → 变 "idle"
- 通过 SSE `[DONE]` 事件触发状态更新

**agentStore 状态：**
```typescript
interface AgentStore {
  teamMembers: InspirationAgent[]
  templatePool: AgentTemplate[]       // 可选的 Agent 模板（Pool）
  loading: boolean
  fetchTeam: (inspirationId: string) => Promise<void>
  fetchTemplates: () => Promise<void>
  addFromPool: (inspirationId: string, templateId: string) => Promise<void>
  updateModel: (agentId: string, model: string) => Promise<void>
  remove: (agentId: string) => Promise<void>
}
```

**验证：**
- 选中 Inspiration → RightPanel 显示 Team（至少包含 Lead Agent）
- 下拉切换模型 → 保存成功，不影响 Agent Pool 模板
- 聊天时状态灯变化（idle → working → idle）

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
- 迭代结束时打 tag（`v0.5.0-iter1`, `v0.5.0-iter2`, `v0.5.0-iter3`）

---

*Plan 版本: 2.0 — 2026-04-26*
*变更: 新增 Task 2.0 Settings/LLM 管理页面 + 全部 Task 前端展现细化 + LLM→Agent→Inspiration 关系模型*
