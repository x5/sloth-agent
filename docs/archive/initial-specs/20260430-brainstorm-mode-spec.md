# Brainstorm 模式 规格

> 关联设计: `~/.gstack/projects/x5-sloth-agent/TUF-master-design-20260430-brainstorm-full-plan.md`
> 关联 Plan: `docs/plans/20260425-mvp-desktop-app-plan.md`
> 日期: 2026-04-30
> 状态: DRAFT

---

## 1. 产品概述

Brainstorm 是 Sloth Agent 的多 Agent 协作模式。用户发起一个讨论话题，多个内置 Expert Agent 并行发言、辩论、协作产出代码和文档。核心差异化：**安全提案式多 Agent 协作** —— Agent 可以读取项目文件作为上下文，但所有产出写入隔离沙箱（`brainstorm-sessions/{session-id}/`），项目文件零风险。用户审查后手动合并。

给谁用：需要多角度分析的开发者、产品经理、技术决策者。解决什么问题：单人决策盲区、方案评审缺乏对立面、AI 产出无法安全落地到代码库。

**原则：**
- 每个迭代最多 3 天工作量
- 每个迭代独立可验证，不依赖下一个迭代
- 小步快跑：每个迭代只动一个核心系统
- 沙箱隔离是硬约束，Brainstorm 永远不能直接修改项目文件
- 支持 5-10 个 Agent 并发参与讨论
- 中国 LLM 生态（DeepSeek、通义千问等）必须可用

---

## 2. 技术栈

| 层 | 技术 |
|---|------|
| 桌面壳 | Tauri v2 (Rust) |
| 前端 | React 18 + TypeScript + Vite |
| 后端 | Python FastAPI Sidecar |
| 数据库 | SQLite (SQLAlchemy + Alembic 迁移) |
| 实时通信 | SSE (Server-Sent Events)，单一连接复用 |
| LLM 路由 | 复用现有 LLMService（OpenAI/Anthropic 双格式） |

---

## 3. 功能需求

### 3.1 会话沙箱（迭代 4）

| 功能 | 描述 | API |
|------|------|-----|
| 创建会话 | 为指定 Inspiration 创建 Brainstorm 会话，自动创建隔离沙箱目录 | `POST /api/inspirations/{id}/brainstorm-sessions` |
| 会话列表 | 返回某 Inspiration 下所有 Brainstorm 会话 | `GET /api/inspirations/{id}/brainstorm-sessions` |
| 会话详情 | 返回会话信息，含沙箱路径和文件树 | `GET /api/brainstorm-sessions/{id}` |
| 文件树查询 | 查询沙箱内文件结构（空会话时返回空树） | 含在会话详情中 |
| 过期会话 | 结束或已合并的会话状态标记 | `PATCH /api/brainstorm-sessions/{id}` |

### 3.2 讨论引擎 — 两轮投票 + SSE 流式（迭代 5）

| 功能 | 描述 | API |
|------|------|-----|
| 发起讨论 | 用户发送话题，触发多 Agent 讨论 | `POST /api/brainstorm-sessions/{id}/discuss` |
| SSE 事件流 | 单一 SSE 连接复用，推送所有 Agent 消息和状态变更 | 同上（SSE 响应） |
| Round 1 意向收集 | N 个 Agent 并行调用，返回 YES（含方向）或 NO | 引擎内部，通过 SSE `agent_intent` 暴露 |
| Round 2 并行发言 | YES 的 Agent 并行生成完整回复，流式推送 | 引擎内部，通过 SSE `message_token` / `message_done` 暴露 |
| 冷却计时器 | 5s 无人发言 → 3s 确认 → 讨论自然结束 | 引擎内部，通过 SSE `cooldown_start` / `cooldown_confirm` / `discussion_end` 暴露 |
| 用户中断 | 用户发新消息 → 取消所有进行中 LLM 调用 → 新轮开始 | 通过 SSE `round_aborted` 暴露 |
| 消息持久化 | 所有讨论消息写入 messages 表，含 parent_message_id、round、intent 字段 | 引擎写入 |
| Lead Agent 总结 | role="lead" 的 Agent 在每轮结束时生成轮次总结 | 通过 SSE `discussion_end.summary` 暴露 |
| Agent 错误处理 | 单个 Agent 失败重试 2 次，仍失败跳过；全部失败则终止讨论 | 通过 SSE `agent_error` / `error` 暴露 |

### 3.3 彩色线程 UI（迭代 6）

| 功能 | 描述 | API |
|------|------|-----|
| Brainstorm 布局 | 多 Agent 讨论的专用前端视图 | 前端 Zustand store |
| 色彩线程 | 同一根消息下的回复共享颜色竖线（`hsl(hash(root_msg_id) % 360, 45%, 55%)`） | 纯前端 |
| 回复标签 | 显示"回复 FE-1 · 原文前30字"标签 | 纯前端 |
| 用户指定回复 | Hover 消息 → 回复按钮 → 输入框出现回复标签 | 纯前端 |
| 泛回复 | 不指定回复目标，parent_message_id = NULL | 前端 → SSE |
| Per-agent 流式状态 | 前端维护 Map<agentId, StreamingState>，区分不同 Agent 的并行流 | 纯前端 |
| 模式开关 | ChatArea TopBar [Chat] [Brainstorm] 切换 | 前端 uiStore |
| Round 1 意向可视化 | Agent 头像旁显示"正在思考..."或"跳过" | 纯前端 |

### 3.4 读 Tools + 上下文引擎（迭代 7）

| 功能 | 描述 | API |
|------|------|-----|
| 读文件 | Agent 可读取项目文件作为讨论依据 | Tool: `read_file(path)` |
| 列目录 | Agent 可浏览项目目录结构 | Tool: `list_directory(path)` |
| 代码搜索 | Agent 可搜索项目代码 | Tool: `grep(pattern, path)` |
| 读设计文档 | Agent 可读 Markdown 设计文档 | Tool: `read_spec(path)` |
| 权限门 | 读 Tools → 项目目录，写 Tools → 沙箱目录 | ToolPermissionGate |
| ContextWindowManager | 双模：Chat 模式按 agent 隔离，Brainstorm 模式 reply-to 链保护 | 引擎内部 |
| Tool-call 展示 | 前端消息气泡内嵌 tool-call 折叠块 | 纯前端 |

### 3.5 写 Tools + 受限执行器（迭代 8）

| 功能 | 描述 | API |
|------|------|-----|
| 写文件 | Agent 将产出写入沙箱 | Tool: `write_file(path, content)` |
| 运行测试 | 在沙箱内执行白名单测试命令 | Tool: `run_tests()` |
| 运行 Linter | 对沙箱文件执行白名单 linter | Tool: `run_linter(file)` |
| 运行构建 | 在沙箱内执行白名单构建命令 | Tool: `run_build()` |
| 命令白名单 | 项目 `tool-whitelist.yaml` 定义可执行命令 | 配置文件 |
| 沙箱文件查看 | 前端显示沙箱文件树 + 内容预览 + 语法高亮 | SandboxFileViewer 组件 |
| 逐文件应用 | 用户逐文件审核 → 复制到项目目录 | `POST /api/brainstorm-sessions/{id}/apply-file` |
| 全部应用 | 一键应用所有沙箱文件 | `POST /api/brainstorm-sessions/{id}/apply-all` |
| discussion_end 扩展 | SSE discussion_end payload 新增 sandbox_files 字段 | 引擎 SSE 输出 |

### 3.6 异步自主模式（迭代 9）

| 功能 | 描述 | API |
|------|------|-----|
| 启动异步讨论 | 讨论在后端运行，不依赖前端 SSE 连接 | `POST /api/brainstorm-sessions/{id}/start-async` |
| 查询讨论进度 | 返回当前消息数、轮数、活跃 Agent、状态 | `GET /api/brainstorm-sessions/{id}/status` |
| 断线恢复 | 前端重连后从 DB 恢复讨论状态 | 前端轮询 + store 恢复 |
| 讨论完成通知 | 浏览器 Notification API + 页面视觉提示 | 前端 |
| 架构过渡 | BrainstormEngine 从"SSE 驱动"重构为"生成即写 DB"模式 | 引擎内部 |

### 3.7 记忆与人格（迭代 10+，远期）

| 功能 | 描述 |
|------|------|
| Agent 长期记忆 | 跨会话的知识积累 |
| Agent 人格 | 每个 Agent 发展观点和风格偏好 |
| 具体设计 | 留到迭代 9 完成后重新评估 |

---

## 4. UI 结构

### 4.1 Brainstorm 布局（迭代 6）

```
┌──────────────────────────────────────────────────────────┐
│ Amazing Project  [Chat] [Brainstorm]  🟢 2 ACTIVE  [👥] [📊] [⋯] │  ← TopBar + 模式开关
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─ Thread #1 (root: "用 JWT 还是 Session?") ──┐       │
│  │ ┃ 🔵 FE-1 (Bazi Expert)    12:03           │       │  ← 蓝色竖线
│  │ ┃ ┌─────────────────────────────────────┐   │       │
│  │ ┃ │ 从时空能量角度看，JWT 的无状态性     │   │       │
│  │ ┃ │ 更符合当前项目的发展周期...          │   │       │
│  │ ┃ └─────────────────────────────────────┘   │       │
│  │ ┃                                          │       │
│  │ ┃ 🔵 FE-3 (I Ching Expert)  12:04         │       │  ← 同色竖线（同一线程）
│  │ ┃ ┌─────────────────────────────────────┐   │       │
│  │ ┃ │ 回复 FE-1 · "从时空能量角度..."     │   │       │  ← 回复标签
│  │ ┃ │ JWT 确实更优，但需考虑...            │   │       │
│  │ ┃ └─────────────────────────────────────┘   │       │
│  │ └──────────────────────────────────────────┘       │
│  │                                                      │
│  │  ┌─ Thread #2 (root: "数据库选型") ──┐              │
│  │  ┃ 🟠 FE-2 (Astrologer)   12:05      │              │  ← 橙色竖线
│  │  ┃ ┌──────────────────────────────┐   │              │
│  │  ┃ │ SQLite 足够，但未来可考虑 PG  │   │              │
│  │  ┃ └──────────────────────────────┘   │              │
│  │  └───────────────────────────────────┘              │
│                                                          │
├──────────────────────────────────────────────────────────┤
│ [回复 FE-1 · "从时空能量角度..."] [✕]                    │  ← 回复标签（可取消）
│ ┌──────────────────────────────────────────────────────┐ │
│ │ 我觉得 JWT 方案更好...                               │ │  ← 输入框
│ └──────────────────────────────────────────────────────┘ │
│                                              [📎] [➤]   │
└──────────────────────────────────────────────────────────┘
```

### 4.2 SandboxFileViewer（迭代 8）

```
┌──────────────────────────────────┐
│ Sandbox Files            [Apply All] │
├──────────────────────────────────┤
│ 📁 auth/                        │
│   📄 jwt-middleware.ts    ✓ applied │  ← 已应用标记
│   📄 auth.test.ts          new     │  ← 新文件，待审核
│ 📁 docs/                        │
│   📄 architecture.md       new     │
├──────────────────────────────────┤
│ 选中: auth/auth.test.ts          │
│ ┌──────────────────────────────┐ │
│ │ 1  import { describe, it }  │ │  ← 内容预览 + 语法高亮
│ │ 2                          │ │
│ │ 3  describe('JWT', () => { │ │
│ │ ...                        │ │
│ └──────────────────────────────┘ │
│           [Apply This File]      │
└──────────────────────────────────┘
```

---

## 5. 数据模型

### 5.1 新增表: brainstorm_sessions

```
id: str (UUID)
inspiration_id: str (FK → inspirations)
title: str
status: str  — "active" | "cooling_down" | "ended" | "summarized"
sandbox_path: str  — 沙箱目录绝对路径
max_messages: int  — 默认 500
cooldown_seconds: int  — 默认 5
message_count: int  — BrainstormEngine 在 message_done 时递增
summary: str | None  — Lead Agent 总结
started_by: str | None  — "user" | "auto" (Iter-9)
notification_sent: bool  — 默认 False (Iter-9)
created_at: datetime
ended_at: datetime | None
```

### 5.2 修改表: messages（新增字段，Iter-5 Alembic 迁移）

```
brainstorm_session_id: str | None  — NULL = Chat 模式消息
parent_message_id: str | None  — 回复引用，NULL = 新话题根
round: int  — 讨论轮次，默认 1
intent: str | None  — "YES" | "NO" | None
truncated: bool  — 默认 False，用户打断时标记
```

### 5.3 新增表: brainstorm_files（Iter-4 建表，Iter-8 写入）

```
id: str (UUID)
session_id: str (FK → brainstorm_sessions)
file_path: str  — 沙箱内相对路径
content: str  — 文件内容
created_by: str  — agent_id
file_type: str  — "code" | "doc" | "test" | "config" | "other"
created_at: datetime
```

---

## 6. 迭代规划

### 迭代 4: 会话沙箱（3 天）

**目标：** 为 Brainstorm 建立独立的、隔离的工作区。用户能创建 Brainstorm 会话，沙箱目录自动生成。

**交付物：** `brainstorm_sessions` 表 + CRUD API + SandboxManager + 前端会话列表

**验收标准：**
- [ ] `POST /api/inspirations/{id}/brainstorm-sessions` → 会话创建 → `brainstorm-sessions/{uuid}/` 目录产生
- [ ] `GET /api/inspirations/{id}/brainstorm-sessions` → 返回会话列表
- [ ] `GET /api/brainstorm-sessions/{id}` → 返回会话详情（含 sandbox_path + 文件树）
- [ ] 重启后端，会话数据持久化在 SQLite
- [ ] `brainstorm-sessions/` 已在 `.gitignore` 中
- [ ] 前端 Brainstorm 列表 Tab 可见，可创建新会话

### 迭代 5: 讨论引擎 — 两轮投票 + SSE 流式（3 天）

**目标：** 多个 Agent 并行发言，冷却计时器自然结束讨论。Lead Agent 生成轮次总结。

**交付物：** BrainstormEngine (DecisionStrategy + CoolingTimer) + SSE discuss 端点 + messages 表扩展

**验收标准：**
- [ ] 发送讨论请求 → SSE 流返回 `agent_start` 事件（每个 Agent 一个）
- [ ] Round 1 各 Agent 返回 YES/NO → `agent_intent` 事件，NO 的 Agent 被排除
- [ ] YES 的 Agent 并行流式返回发言 → `message_token` → `message_done`
- [ ] 5s 无人发言 → `cooldown_start` → 3s 确认 → `cooldown_confirm` → `discussion_end`
- [ ] 用户发新消息 → `round_aborted` → 新轮开始
- [ ] `parent_message_id` 链正确：回复消息指向被回复的消息
- [ ] 消息持久化到 SQLite，含新增 5 个字段
- [ ] 模拟 Agent 超时 → `agent_error(retry=True)` → 重试 2 次 → 最终跳过
- [ ] 所有 Agent 全失败 → `error` 事件 → 讨论终止

### 迭代 6: 彩色线程 UI（3 天）

**目标：** 前端渲染多 Agent 讨论，颜色区分线程，用户可指定回复目标。

**交付物：** BrainstormArea + BrainstormMessage + BrainstormInput 组件 + brainstormStore 扩展

**验收标准：**
- [ ] Chat/ Brainstorm 模式开关可用，切换后 UI 正确渲染
- [ ] 发送消息 → 多个 Agent 气泡并行渲染，流式打字效果
- [ ] 同一线程的消息共享颜色竖线（hash 根消息 ID）
- [ ] 不同线程颜色不同
- [ ] 回复消息显示"回复 FE-1 · 原文前30字"标签
- [ ] Hover 消息 → 回复按钮出现 → 点击 → 输入框上方出现回复标签
- [ ] 点击回复标签 [✕] → 取消引用，回到泛回复模式
- [ ] Round 1 意向可视化：Agent 头像旁显示状态
- [ ] 用户发新消息 → 旧轮消息折叠或标记结束

### 迭代 7: 读 Tools + 上下文引擎（3 天）

**目标：** Agent 可以读取项目文件作为讨论依据。引入完整的上下文窗口管理。

**交付物：** ToolRegistry + ToolPermissionGate + ContextWindowManager + ToolCallBlock 组件

**验收标准：**
- [ ] Agent 调用 `read_file` → 读取正确的项目文件内容（不是沙箱路径）
- [ ] Agent 调用 `list_directory` → 返回项目目录结构
- [ ] Agent 调用 `grep` → 返回匹配的代码行
- [ ] Agent 尝试写文件 → ToolPermissionGate 拒绝（Iter-7 未注册写 Tools）
- [ ] ContextWindowManager Brainstorm 模式正确执行 reply-to 链保护
- [ ] 前端展示 tool-call 块（Agent 读了什么文件）
- [ ] 读文件操作不影响项目文件（纯只读）

### 迭代 8: 写 Tools + 受限执行器（3 天）

**目标：** Agent 的讨论结论落地为沙箱中的代码文件、文档、测试用例。用户可逐文件审核并应用到项目。

**交付物：** 写 Tools 注册 + tool-whitelist.yaml + SandboxFileViewer + apply API

**验收标准：**
- [ ] Agent 在沙箱中写文件 → 文件出现在 `brainstorm-sessions/{id}/` 下
- [ ] Agent 执行 `run_tests()` → 测试在沙箱目录执行 → 结果显示在消息流
- [ ] Agent 尝试执行白名单外命令 → ToolPermissionGate 拦截
- [ ] SandboxFileViewer 显示所有生成文件 + 文件树
- [ ] 点击文件 → 内容预览（语法高亮）
- [ ] "Apply This File" → 文件从沙箱复制到项目 → 标记为 "applied"
- [ ] "Apply All" → 全部应用
- [ ] discussion_end SSE payload 含 sandbox_files 字段

### 迭代 9: 异步自主模式（3 天）

**目标：** 用户提一个问题后离线，Agent 自主讨论并产出结果。回来查看讨论结果和通知。

**交付物：** start-async API + status API + 断线恢复 + 浏览器通知

**验收标准：**
- [ ] 发起异步讨论 → 关闭浏览器 → 5 分钟后回来 → 讨论已完成，消息完整
- [ ] 讨论中重新打开页面 → 恢复当前讨论状态（已有消息、活跃 Agent）
- [ ] 讨论结束 → 浏览器通知（如已授权）+ 页面标题闪烁
- [ ] 同时进行多个异步讨论 → 各自独立沙箱，互不干扰
- [ ] BrainstormEngine 写入 DB 不依赖 SSE 连接

---

## 7. 错误处理

### 后端错误

| 场景 | 处理方式 |
|------|---------|
| 单个 Agent LLM 调用超时 | `agent_error(retry=True)` → 重试最多 2 次 → 仍失败 → `agent_error(retry=False)` → 跳过 |
| Agent 返回乱码/空响应 | 同上，重试后跳过 |
| 所有 Agent 全部失败 | `error` 事件 → 讨论终止 |
| LLM Provider 全部不可用 | `error` 事件 → 讨论终止 |
| 沙箱目录创建失败 | 返回 500，记录错误日志 |
| 白名单外命令尝试执行 | ToolPermissionGate 拦截，返回 `"命令 '{cmd}' 不在白名单中"` |
| 用户中断（发新消息） | `round_aborted` → 取消所有进行中 LLM 调用 → 保留已完成的完整消息 → 截断消息标记 truncated=True |

### 前端错误

| 场景 | 处理方式 |
|------|---------|
| SSE 连接断开 | 自动重连（exponential backoff，最大 3 次） |
| SSE 事件解析失败 | 跳过该行，不中断流 |
| 页面关闭时讨论进行中 | 讨论继续（Iter-9），下次打开恢复 |
| 文件应用到项目失败（路径冲突） | 提示用户，不覆盖，建议手动处理 |

---

## 8. 不做什么

- **不实现 ContextWindowManager Chat 模式重构** — 如 Iter-7 进度紧张，Chat 模式沿用现有扁平逻辑，只交付 Brainstorm 模式的 reply-to 链保护
- **不实现 Docker 沙箱** — Iter-8 用白名单受限执行器，Docker 容器沙箱延至未来版本
- **不实现 Agent 网络请求能力** — ToolPermissionGate 永久拦截 http_client 等工具
- **不实现 Agent 角色行为区分** — 所有非 Lead Agent 平等参与讨论，不做角色差异化发言逻辑
- **不实现跨会话 Agent 记忆** — 延至 Iter-10+
- **不实现 Agent 人格和风格偏好** — 延至 Iter-10+
- **不在 Iter-4 实现讨论引擎** — 沙箱先行，讨论引擎在 Iter-5
- **不在 Iter-5 实现前端彩色 UI** — 后端讨论引擎先行，前端在 Iter-6
- **不在 Iter-5 实现 ContextWindowManager** — 移到 Iter-7 与读 Tools 一起交付

---

## 9. 项目结构（目标）

```
sloth-agent/
├── brainstorm-sessions/       # 沙箱产出目录（gitignore）
│   ├── {session-id}/          # 每次 Brainstorm 的隔离工作区
│   └── .archive/              # 已合并/归档的会话
├── backend/
│   └── app/
│       ├── models.py          # +BrainstormSession, +BrainstormFile, Message 扩展
│       ├── routers/
│       │   └── brainstorm.py  # Brainstorm CRUD + SSE discuss + apply API
│       ├── services/
│       │   ├── sandbox.py     # SandboxManager
│       │   ├── brainstorm.py  # BrainstormEngine (DecisionStrategy + CoolingTimer)
│       │   └── tools.py       # ToolRegistry + ToolPermissionGate
│       └── main.py            # 注册路由
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── BrainstormArea.tsx     # 多 Agent 讨论视图
│       │   ├── BrainstormMessage.tsx  # 消息气泡（含线程颜色）
│       │   ├── BrainstormInput.tsx    # 输入区域（含回复标签）
│       │   ├── SandboxFileViewer.tsx  # 沙箱文件查看器
│       │   └── ToolCallBlock.tsx      # Tool-call 展示块
│       └── stores/
│           └── brainstormStore.ts     # Brainstorm 状态管理
└── tool-whitelist.yaml        # 受限执行器命令白名单
```

---

*Spec 版本: 1.0 — 2026-04-30*
*变更: 初始版本，覆盖 Iter-4 至 Iter-9 完整功能规格*
