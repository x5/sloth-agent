# Sloth Agent 总体架构设计

> 版本: v1.0.0
> 日期: 2026-04-15
> 状态: 待审批

---

## 1. 产品定位

Sloth Agent 是一个**产品级的 AI 开发助手工具**，可理解为轻量、定制化的 OpenClaw + Hermes Agent 组合体，借鉴 Claude Code 和 Codex 的最佳实践。

**核心价值**：通过 Phase-Role-Architecture（阶段-角色-技能架构），将开发流程标准化为 8 个阶段，每个阶段由专门化的 Agent 角色执行，并可在需要时调用 37 个预定义技能。

**两种工作模式**：
- **自主模式**：昼夜循环，夜间半自主（需求分析→计划制定→人工审批），日间全自主（编码→监控）
- **对话模式**：REPL 交互，自由对话、技能触发、工作流控制

---

## 2. 系统全景

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          CLI 入口 (typer)                                │
│                        src/cli/app.py                                    │
│                  sloth run | sloth chat | sloth skills                    │
└──────────────┬──────────────────────────────────────┬────────────────────┘
               │                                      │
               ▼                                      ▼
┌──────────────────────────┐        ┌─────────────────────────────────────┐
│    AUTONOMOUS MODE       │        │           CHAT MODE                  │
│   AgentEvolve.run()      │        │       ChatSession.loop()             │
│   昼夜循环控制器          │        │       REPL 交互                      │
└──────────┬───────────────┘        └────────────┬────────────────────────┘
           │                                     │
           │         ┌───────────────────────────┼───────────────────┐
           │         ▼                           ▼                   ▼
           │  ┌─────────────┐  ┌──────────────────┐  ┌──────────────────┐
           │  │ LLMProvider │  │ Conversation     │  │ SessionManager   │
           │  │ Manager     │  │ Context          │  │                  │
           │  │ (现有)      │  │ (新增)           │  │ (新增)           │
           │  └─────────────┘  └──────────────────┘  └──────────────────┘
           │                                                   │
           └──────────────────────┬────────────────────────────┘
                                  ▼
              ┌──────────────────────────────────────────────────┐
              │              共享基础设施层                         │
              ├──────────┬──────────┬───────────┬────────────────┤
              │PhaseReg  │SkillReg  │ToolReg    │MemoryStore     │
              │istry     │istry     │istry      │+ Index         │
              │(场景+阶段)│(37 skills)│(bash/git  │(文件系统+SQLite │
              │          │          │ /file)    │ + ChromaDB)    │
              └──────────┴──────────┴───────────┴────────────────┘
                                  │
                                  ▼
              ┌──────────────────────────────────────────────────┐
              │              外部集成层                             │
              ├──────────────────────┬───────────────────────────┤
              │ FeishuServer (v1.2) │ LLM Providers              │
              │ /feishu/webhook      │ (deepseek, glm-4, etc.)    │
              │ /feishu/card-callback│                            │
              └──────────────────────┴───────────────────────────┘
```

---

## 3. 两种执行模式

### 3.1 自主模式（Autonomous）

```
时间触发:
  22:00 → 夜模式开始
    ├── Phase-1: 需求分析 (Analyst Agent)
    ├── Phase-2: 计划制定 (Planner Agent)
    ├── Human Review: 飞书审批卡片推送
    └── 等待确认 → 确认则继续，拒绝则记录

  09:00 → 日模式开始
    ├── Phase-3: 编码实现 (Coder Agent + TDD)
    ├── Phase-4: 调试排错 (Debugger Agent)
    ├── Phase-5: 代码审查 (Reviewer Agent)
    ├── Phase-6: 质量验证 (QA Agent)
    ├── Phase-7: 发布上线 (Release Agent)
    └── Phase-8: 上线监控 (Monitor Agent)
```

**控制器**：`src/core/agent.py` (AgentEvolve)
**共享基础设施**：LLM Provider Manager, Tool Registry, Memory Store

### 3.2 对话模式（Chat）

```
用户输入 → REPL (sloth>)
  ├── 普通文本 → LLM 对话 → 显示响应
  ├── /skill <name> → 匹配技能 → 注入技能 prompt → 执行
  ├── /run <scenario> → 触发工作流 → Phase 切换 → 执行
  ├── /start autonomous → 启动自主模式（后台）
  ├── /stop → 中止自主模式
  ├── /status → 查看状态
  └── /clear, /context, /help, /quit → REPL 控制
```

**控制器**：`src/cli/chat.py` (ChatSession)
**上下文管理**：`src/cli/context.py` (ConversationContext)
**Session 管理**：`src/memory/session.py` (SessionManager)

### 3.3 模式关系

```
自主模式和对话模式是平行入口，共享同一套基础设施：

  自主模式 = 时间驱动 → Phase 自动执行
  对话模式 = 用户驱动 → 可手动触发 Phase / 技能 / 自主模式

  两者共享：
  ├── LLM 提供商（deepseek, glm-4, ...）
  ├── 工具注册（bash, git, file, ...）
  ├── 技能注册（37 个预定义技能）
  ├── 内存存储（文件系统 + SQLite + ChromaDB）
  └── Phase 注册（8 个阶段 + 场景编排）
```

---

## 4. 核心模块

### 4.1 Phase-Role-Architecture

**文件**：`src/workflow/`

```
Phase (阶段)
├── 1:1 Agent (角色) — 每个 phase 有专属 Agent 角色
├── 1:N Skills (技能) — 每个 phase 可调用多个技能
├── 前置约束 — 依赖的前序 phase
└── 后置约束 — 输出交付物

Scenario (场景)
├── 由多个 Phase 编排而成
├── standard: 标准开发流程 (phase-1 → phase-8)
├── hotfix: 紧急修复 (phase-4 → phase-5 → phase-6)
└── review-only: 仅审查 (phase-5 → phase-6)
```

**注册表**：`src/workflow/registry.py`
- `PhaseRegistry`：管理场景和阶段定义
- `SkillRegistry`：管理 37 个技能元数据

### 4.2 Memory 三层架构

**文件**：`src/memory/`

```
memory/
├── sessions/                    # 会话层（用户交互）
│   └── {session_id}/
│       ├── chat.jsonl           # 完整对话记录
│       ├── context.json         # 活跃摘要
│       └── metadata.json        # 元信息
│
├── scenarios/                   # 场景层（Phase 数据）
│   └── {scenario_id}/
│       └── {phase_id}/
│           ├── input.json       # phase 输入
│           ├── output.json      # phase 输出
│           ├── chat.jsonl       # phase 对话
│           └── artifacts/       # 产出文件
│
└── shared/                      # 共享层（跨 session 知识）
    ├── skills/                  # 技能进化记录
    ├── knowledge/               # 长期学习成果
    └── reports/                 # 场景执行报告

存储引擎：
├── 文件系统 (JSON/jsonl) — 主存储，truth source
├── SQLite — 索引层，快速查询
└── ChromaDB — 向量索引，语义检索
```

**核心模块**：
- `MemoryStore` (`store.py`)：文件系统存储管理
- `MemoryIndex` (`index.py`)：SQLite 索引管理
- `MemoryRetrieval` (`retrieval.py`)：检索引擎
- `SkillManager` (`skills.py`)：技能加载与进化
- `SessionManager` (`session.py`)：Session 生命周期

### 4.3 CLI 入口

**文件**：`src/cli/`

| 子命令 | 模块 | 说明 |
|--------|------|------|
| `sloth run` | `app.py` | 自主模式（现有入口） |
| `sloth chat` | `chat.py` | 交互对话模式 |
| `sloth status` | `app.py` | 显示 Agent 状态 |
| `sloth skills` | `app.py` | 列出/查看技能 |
| `sloth scenarios` | `app.py` | 列出工作流场景 |
| `sloth feishu` | `feishu_server.py` (v1.2) | 启动飞书 webhook |

### 4.4 技能管理

**文件**：`src/memory/skills.py`, `src/memory/skill_router.py`

```
技能来源：
├── Superpowers (14 个，skills/superpowers/，auto+manual 触发)
├── gstack (23 个，skills/gstack/，manual 触发)
├── 用户自定义 (skills/user/)
└── 自动进化 (skills/evolved/ — 仅全新技能)

统一格式（Claude Code SKILL.md）：
{skill_dir}/
├── SKILL.md              # YAML frontmatter + 指令
├── references/           # 参考资料
└── templates/            # 模板文件

匹配策略（v1.1）：
├── 关键词匹配
├── 斜杠命令直接匹配
└── FTS 搜索

匹配策略（v1.2）：
└── 向量检索（嵌入模型语义匹配）
```

### 4.5 飞书集成

**文件**：`src/cli/feishu_server.py`, `src/providers/feishu_client.py`

```
两条通道：
├── 审批通道（现有）：Agent → webhook → 用户收到审批卡片
└── 对话通道（新增）：用户 → 飞书消息 → webhook server → ChatSession

路由：
├── POST /feishu/webhook — 接收飞书消息
├── POST /feishu/card-callback — 接收卡片回调
└── GET /feishu/health — 健康检查

Session：feishu-{user_id} 与 CLI session 共享 SessionManager
```

---

## 5. 数据流

### 5.1 自主模式数据流

```
时钟触发 (cron / schedule)
  → AgentEvolve.run()
  → 判断时段（日/夜）
  → 选择 Scenario（standard）
  → 按序执行 Phase：
     ├── Phase.start() → 创建 phase 目录
     ├── Agent.run() → 对话 + 工具调用
     ├── Phase 对话 → 写入 scenarios/{scenario}/{phase}/chat.jsonl
     ├── Phase 输出 → 写入 output.json
     ├── 生成摘要 → 追加到 session context.json
     └── Phase.complete() → 进入下一 phase
  → 夜模式 Phase-2 完成 → 推送飞书审批卡片
  → 等待人工确认 → 确认后继续日间 phase
```

### 5.2 对话模式数据流

```
用户输入 (REPL)
  → ChatSession.loop()
  → 判断输入类型：
     ├── 斜杠命令 → CommandHandler 执行
     ├── 普通对话 → LLM 响应 → 显示
     └── /run scenario → SessionManager.start_phase()
         ├── 保存当前摘要
         ├── 切换 LLM（chat → phase-specific）
         ├── 注入系统提示（角色定义 + 前序摘要 + 技能列表）
         ├── 执行 Phase 对话
         └── Phase 完成 → 保存输出 → 追加摘要
  → 每轮对话 → SessionManager.save_message() → chat.jsonl
```

### 5.3 Phase 切换上下文衔接

```
Phase N 完成 → Phase N+1 开始:

1. 生成摘要 (ContextSummarizer)
   → 从 Phase N 的 output.json + chat.jsonl 提取关键信息

2. 保存摘要
   → 追加到 session context.json

3. 创建 Phase N+1 目录
   → scenarios/{scenario}/phase-N+1/

4. 切换 LLM
   → Phase N 的 LLM → Phase N+1 的 LLM

5. 构建系统提示
   ├── Phase N+1 角色定义
   ├── 前序摘要（从 context.json 读取）
   └── Phase N+1 可用技能列表

6. 执行 Phase N+1
   → 对话写入 phase chat.jsonl

三层保证：
├── 完整层：所有原始对话在 chat.jsonl
├── 摘要层：context.json 供 LLM 快速理解
└── 结构层：output.json 供后续 phase 使用
```

---

## 6. 配置模型

**文件**：`src/core/config.py`, `configs/agent.yaml`

```yaml
# 全局配置
model:
  default: deepseek-chat
  providers:
    deepseek:
      api_key: "${DEEPSEEK_API_KEY}"
      model: deepseek-chat
    glm:
      api_key: "${GLM_API_KEY}"
      model: glm-4

chat:
  max_context_turns: 20
  auto_approve_risk_level: 2
  stream_responses: true
  prompt_prefix: "sloth> "

feishu:                    # v1.2
  app_id: "${FEISHU_APP_ID}"
  app_secret: "${FEISHU_APP_SECRET}"
  webhook: "${FEISHU_WEBHOOK}"
  verification_token: "${FEISHU_VERIFICATION_TOKEN}"
  encrypt_key: "${FEISHU_ENCRYPT_KEY}"
  enabled: true

memory:
  store_path: "./memory/"
  index_enabled: true
  vector_enabled: false    # v1.1 启用
```

---

## 7. 目录结构

```
src/
├── __main__.py                    # 入口（typer app）
├── cli/
│   ├── __init__.py
│   ├── app.py                     # CLI 子命令
│   ├── chat.py                    # Chat REPL
│   ├── context.py                 # 对话上下文
│   ├── autonomous_controller.py   # (v1.1) 自主模式控制
│   └── feishu_server.py           # (v1.2) 飞书 webhook
├── core/
│   ├── config.py                  # 配置模型
│   ├── agent.py                   # AgentEvolve（自主模式）
│   └── tools/                     # 工具注册
│       └── tool_registry.py
├── providers/
│   ├── llm_providers.py           # LLM 提供商管理
│   └── feishu_client.py           # (v1.2) 飞书 API 客户端
├── workflow/
│   ├── registry.py                # Phase + Skill 注册表
│   └── phases/                    # Phase 实现
│       ├── phase_1_analyst.py
│       ├── phase_2_planner.py
│       └── ...
└── memory/
    ├── __init__.py
    ├── store.py                   # 文件系统存储
    ├── index.py                   # SQLite 索引
    ├── retrieval.py               # 检索引擎
    ├── session.py                 # SessionManager
    ├── summarizer.py              # ContextSummarizer
    ├── skills.py                  # SkillManager
    ├── skill_router.py            # (v1.1) SkillRouter
    └── skill_validator.py         # SkillValidator
configs/
└── agent.yaml                     # Agent 配置
skills/                            # 技能目录
├── superpowers/                   # 14 个内建技能（auto+manual，可就地进化）
├── gstack/                        # 23 个内建技能（manual，可就地进化）
├── user/                          # 用户自定义
└── evolved/                       # 全新技能（37 个预定义之外的）
memory/                            # 运行时数据（gitignored）
├── sessions/
├── scenarios/
└── shared/
tests/
├── cli/
│   ├── test_chat.py
│   └── test_config.py
├── memory/
│   ├── test_store.py
│   ├── test_index.py
│   ├── test_retrieval.py
│   ├── test_session.py
│   ├── test_skills.py
│   └── test_skill_router.py
└── workflow/
    └── test_registry.py
pyproject.toml
docs/
└── specs/                         # 设计规格
```

---

## 8. 规格文档索引

| 规格 | 文件 | 状态 |
|------|------|------|
| 总体架构 | `00000000-architecture-overview.md` | 本文件 |
| Phase-Role-Architecture | `20260416-phase-role-architecture-spec.md` | 待审批 |
| Chat Mode | `20260416-chat-mode-spec.md` | 待审批 |
| Memory Management | `20260416-memory-management-spec.md` | 待审批 |
| Session Management | `20260416-session-management-spec.md` | 待审批 |
| Skill Management | `20260416-skill-management-spec.md` | 待审批 |
| Feishu Integration | `20260416-feishu-integration-spec.md` | 待审批 |
| 开发流程规范 | `20260415-workflow-process-spec.md` | 已记录 |

---

## 9. 版本路线图

| 版本 | 核心交付 | 时间 |
|------|---------|------|
| **v1.0** | Phase-Role-Architecture 实现<br>Chat Mode 基础（自由对话 + REPL）<br>Memory 三层结构 + 文件系统存储<br>Session 生命周期管理<br>Skill 统一格式 + 加载机制 | 当前 |
| **v1.1** | Skill Router（意图识别 + 自动激活）<br>自主模式控制（从 chat mode 启停）<br>Phase 切换上下文衔接（摘要传递）<br>向量检索（ChromaDB 启用）<br>Skill 自动进化 | 下一 |
| **v1.2** | Phase 触发（从 chat mode /run scenario）<br>飞书集成（webhook server + 卡片交互）<br>飞书 session 与 CLI session 统一<br>跨 session 知识聚合 | 后续 |

---

## 10. 关键设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 存储引擎 | 文件系统为主，SQLite/ChromaDB 为索引 | 文件系统可回溯、可审计、可手动编辑 |
| 会话格式 | jsonl（每行一条 JSON） | 流式写入、不丢失、易追加 |
| 技能格式 | Claude Code SKILL.md | 自然兼容、开源生态可复用 |
| CLI 框架 | typer | 与现有 pydantic 自然集成 |
| Phase 切换 | 摘要传递 + 完整记录 | 信息不丢失 + LLM context 有限 |
| 自主/对话模式 | 平行入口，共享基础设施 | 不耦合、各自独立演进 |
| 飞书集成 | 补全对话通道，不替换审批通道 | 两者互补，审批推+对话收 |

---

*规格版本: v1.0.0*
*创建日期: 2026-04-15*
