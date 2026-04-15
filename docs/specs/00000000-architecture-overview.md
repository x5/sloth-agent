# Sloth Agent 总体架构设计

> 版本: v2.0.0
> 日期: 2026-04-16
> 状态: 草案

---

## 1. 产品定位

Sloth Agent 是一个**产品级的 AI 开发助手**，可理解为 OpenClaw + Hermes Agent 的组合体，借鉴 Claude Code 和 Codex 的最佳实践，并针对中国开发者生态进行深度定制。

**核心价值**：通过 Phase-Role-Architecture（阶段-角色-技能架构），将开发流程标准化为 8 个阶段，每个阶段由专门的 Agent 角色执行，并可在需要时调用 37 个预定义技能。同时提供一个通用 Agent，可跨阶段自由调用任意技能，处理非结构化任务。

**两种工作模式**：
- **自主模式**：昼夜循环，夜间半自主（需求分析→计划制定→人工审批），日间全自主（编码→审查→测试→发布），支持 Persistent Daemon 常驻运行
- **对话模式**：REPL 交互，自由对话、技能触发、工作流控制，可从对话中启停自主模式

**目标用户**：中国开发者、技术团队、需要自动化开发流程的工程师。

---

## 2. 设计原则

| 原则 | 说明 |
|------|------|
| **专用 Agent + 通用 Agent** | 8 个专职 Agent 保障并行能力和上下文隔离；1 个通用 Agent 处理自由形态请求 |
| **工具优先** | Agent 通过工具层执行操作，不直接写文件或跑命令，所有操作可审计 |
| **技能即指令** | SKILL.md 就是 prompt 模板，运行时注入，与 Claude Code 生态兼容 |
| **渐进式记忆** | 文件系统为主（可回溯、可审计、可手动编辑），SQLite 为索引层（可选），ChromaDB 为向量层（可选） |
| **场景即工作流** | 场景 = Phase 调用序列 + 门控条件，Phase 间通过摘要传递上下文 |
| **事件驱动** | 模块间通过发布-订阅事件总线通信，而非直接调用 |
| **安全默认** | 5 层安全防护，沙箱隔离，路径白名单，命令黑名单，资源限制 |
| **多模型支持** | 6 个 LLM Provider 自动切换 + 熔断降级 |
| **文件系统即真相** | 所有状态、对话、产出物以 JSON/jsonl 存储于文件系统，可手动编辑 |

---

## 3. 系统全景

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              CLI 入口 (typer)                                    │
│         sloth run | sloth chat | sloth daemon | sloth status | sloth install     │
└──────────┬──────────────────────────────────────────────┬────────────────────────┘
           │                                              │
           ▼                                              ▼
┌──────────────────────────┐            ┌─────────────────────────────────────────┐
│    AUTONOMOUS MODE       │            │              CHAT MODE                   │
│  AgentEvolve / Daemon    │            │         ChatSession.loop()               │
│  昼夜循环 / Persistent    │            │         REPL 交互                        │
│  后台常驻 / 健康检查      │            │         技能触发 / 工作流控制             │
└──────────┬───────────────┘            └────────────┬────────────────────────────┘
           │                                         │
           │    ┌────────────────────────────────────┼─────────────────────┐
           │    ▼                                    ▼                     ▼
           │ ┌─────────────┐  ┌──────────────────┐  ┌──────────────────────┐
           │ │ LLMProvider │  │ Conversation     │  │   SessionManager     │
           │ │ Manager     │  │ Context          │  │   + Worktree Mgmt    │
           │ │ (6 Providers│  │ (max_turns,      │  │   + Checkpoint       │
           │ │  incl. mimo)│  │  truncation)     │  │   + Lifecycle        │
           │ └─────────────┘  └──────────────────┘  └──────────────────────┘
           │                                                   │
           └──────────────────────┬────────────────────────────┘
                                  ▼
              ┌──────────────────────────────────────────────────────────┐
              │                    共享基础设施层                          │
              ├────────────┬────────────┬────────────┬───────────────────┤
              │PhaseReg    │SkillReg    │ToolReg     │MemoryStore        │
              │istry       │istry       │istry +     │+ Index (SQLite)   │
              │(8 Phase +  │(37 skills  │Plugin      │+ Vector (ChromaDB)│
              │ 8 Scenarios│SKILL.md)   │(Claude Code│                   │
              │ + Pipeline)│            │ 对齐)      │                   │
              └────────────┴────────────┴────────────┴───────────────────┘
                                  │
           ┌──────────────────────┼──────────────────────┐
           ▼                      ▼                      ▼
┌──────────────────┐  ┌────────────────────┐  ┌──────────────────────────┐
│  横切能力层        │  │  事件驱动层         │  │  外部集成层               │
│                  │  │                    │  │                          │
│ Observability    │  │  Event Bus         │  │ Feishu (webhook + card)  │
│ Error Recovery   │◄─┤  (pub/sub)         │  │ LLM Providers (6)        │
│ Report Generator │  │  Workflow Rules    │  │ Email (SMTP)             │
│ Cost Tracker     │  │  Dead Letter Queue │  │ Generic Webhook          │
│ Knowledge Base   │  │  Event Replay      │  │ Notification Channels    │
│ Security Sandbox │  │                    │  │                          │
└──────────────────┘  └────────────────────┘  └──────────────────────────┘
```

---

## 4. 功能模块架构（15 个模块）

### 4.1 模块总览

| # | 模块 | Spec 文件 | 优先级 | 核心职责 |
|---|------|-----------|--------|---------|
| 1 | Phase-Role Architecture | `phase-role-architecture-spec.md` | P0 | 8 专职 Agent + 1 通用 Agent、8 阶段、37 技能、8 场景编排 |
| 2 | Tools Invocation | `tools-invocation-spec.md` | P0 | 4 层调用链（Intent→Risk→Execute→Format）、Plugin 架构 |
| 3 | Multi-Agent Coordination | `multi-agent-coordination-spec.md` | P0 | 任务分发、Worktree 隔离、结果合并、冲突解决 |
| 4 | Memory Management | `memory-management-spec.md` | P0 | 三层记忆（FS 主 + SQLite 索引 + ChromaDB 向量） |
| 5 | Session Management | `session-management-spec.md` | P0 | 会话生命周期、checkpoint、摘要传递 |
| 6 | Skill Management | `skill-management-spec.md` | P0 | SKILL.md 加载、路由匹配、自动进化 |
| 7 | Chat Mode | `chat-mode-spec.md` | P0 | REPL 交互、斜杠命令、上下文管理 |
| 8 | Observability & Logging | `observability-logging-spec.md` | P0 | 统一日志、Trace ID、日志查询 CLI、健康诊断 |
| 9 | Error Handling & Recovery | `error-handling-recovery-spec.md` | P0 | 4 级错误分类、熔断器、优雅降级、人工介入 |
| 10 | Report Generation | `report-generation-spec.md` | P0 | 7 种报告类型、模板引擎、多渠道交付 |
| 11 | Notification & Integration | `notification-integration-spec.md` | P1 | 飞书/邮件/Webhook 适配器、通知路由、去重限流 |
| 12 | Cost & Budget Tracking | `cost-budget-spec.md` | P1 | 6 Provider 定价（含 mimo）、预算软硬停机、费用预测 |
| 13 | Session Lifecycle | `session-lifecycle-spec.md` | P1 | 会话创建/暂停/恢复、分支映射、序列化 |
| 14 | Event System | `event-system-spec.md` | P1 | 发布-订阅事件总线、工作流触发、死信队列 |
| 15 | Knowledge Base | `knowledge-base-spec.md` | P2 | 项目上下文、代码库摘要、语义检索 |
| 16 | Daemon & Health | `daemon-health-spec.md` | P1 | Persistent Daemon、心跳检查、看门狗、自动恢复 |
| 17 | Sandbox Security | `sandbox-security-spec.md` | P0 | 5 层安全、路径白名单、资源限制、审计日志 |
| 18 | Installation | `installation-onboarding-spec.md` | P1 | 交互式安装、环境检查、配置引导 |
| 19 | Feishu Integration | `feishu-integration-spec.md` | P2 | Webhook 服务器、卡片交互、审批通道 |

> 注：模块编号 1-15 为核心模块，16-19 为辅助模块。

### 4.2 模块依赖关系

```
                    ┌─────────────┐
                    │   CLI       │
                    │  (入口层)    │
                    └──────┬──────┘
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
     ┌────────────┐ ┌────────────┐ ┌────────────┐
     │ Autonomous  │ │   Chat     │ │  Daemon    │
     │  (自主模式)  │ │  (对话模式) │ │  (常驻)     │
     └─────┬──────┘ └─────┬──────┘ └─────┬──────┘
           │              │              │
           └──────────────┼──────────────┘
                          ▼
                 ┌────────────────┐
                 │ Orchestrator   │
                 │ (控制流入口)    │
                 └───────┬────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
   ┌────────────┐ ┌────────────┐ ┌────────────┐
   │  Phase-    │ │  Multi-    │ │  Session   │
   │  Role Arch │ │  Agent     │ │  Lifecycle │
   │  (#1)      │ │  Coord (#3)│ │  (#13)     │
   └─────┬──────┘ └─────┬──────┘ └─────┬──────┘
         │              │              │
         └──────────────┼──────────────┘
                        ▼
               ┌─────────────────┐
               │  Core Services  │
               │                 │
               │  #2 Tools       │
               │  #4 Memory      │
               │  #5 Session     │
               │  #6 Skills      │
               │  #15 Knowledge  │
               │  #17 Security   │
               └───────┬─────────┘
                       │
              ┌────────┼────────┐
              ▼        ▼        ▼
        ┌────────┐ ┌────────┐ ┌────────┐
        │ #8 Obs │ │ #9 Err │ │ #12 Cost│
        │ #10 Rep│ │ #14 Ev │ │ #11 Not │
        │ #16 Dmn│ │        │ │ #18 Inst│
        │ #19 Fei│ │        │ │         │
        └────────┘ └────────┘ └────────┘
```

---

## 5. Agent 架构

### 5.1 8 个专用 Agent + 1 个通用 Agent

设置专用 Agent 而非单一 Agent 的原因：
1. **并行执行**：多个独立任务可同时推进（如前端和后端同时开发）
2. **上下文隔离**：每个 Agent 有独立的上下文窗口，避免上下文膨胀和信息丢失
3. **角色专业化**：每个 Agent 只能调用所在 Phase 内的技能，行为更可预测
4. **模型优化**：不同 Agent 可使用最适合其任务的模型（编码用 DeepSeek，审查用 Claude）

| Agent 角色 | 所属 Phase | 可用技能 | 推荐模型 | 最大实例 |
|-----------|-----------|---------|---------|---------|
| **Analyst** | Phase 1 需求分析 | brainstorming, writing-plans | qwen-plus | 1 |
| **Planner** | Phase 2 计划制定 | writing-plans, brainstorming | qwen-max | 1 |
| **Engineer** | Phase 3 编码实现 | test-driven-development, subagent-driven-development | deepseek-chat | 3 |
| **Debugger** | Phase 4 调试排错 | /investigate, /debug | deepseek-chat | 2 |
| **Reviewer** | Phase 5 代码审查 | requesting-code-review, /review | claude-sonnet | 2 |
| **QA** | Phase 6 质量验证 | /qa, /cso | claude-sonnet | 2 |
| **Release** | Phase 7 发布上线 | /ship, finishing-a-branch | deepseek-chat | 1 |
| **Monitor** | Phase 8 上线监控 | /health, /retro | qwen-plus | 1 |
| **General** | 无（通用） | 任意技能 | 可配置 | 1 |

### 5.2 通用 Agent

通用 Agent 的特点：
- 可调用所有 37 个技能，不受 Phase 限制
- 处理对话模式中的自由形态请求
- 处理跨 Phase 的复合任务
- 自主模式中的兜底执行器

### 5.3 Agent 间通信

```
专用 Agent A ──→ 消息总线 ──→ 专用 Agent B
     │                            │
     │                            │
     ▼                            ▼
  独立上下文                   独立上下文
  独立 worktree               独立 worktree
  独立分支                    独立分支
```

通过 `MessageBus`（SQLite 后端）实现异步通信，支持：
- 任务结果传递
- 依赖就绪通知
- 错误上报
- 同步请求

---

## 6. Phase 执行模型

### 6.1 8 个 Phase

| Phase | 名称 | Agent | 输入 | 输出 | 门控 |
|-------|------|-------|------|------|------|
| 1 | 需求分析 | Analyst | 用户描述/Issue | 需求文档 | 需求完整性检查 |
| 2 | 计划制定 | Planner | 需求文档 | 实施计划 | 计划可行性审查 |
| 3 | 编码实现 | Engineer | 实施计划 | 代码 + 测试 | TDD 门控 |
| 4 | 调试排错 | Debugger | Bug 报告/失败测试 | 修复代码 | 测试通过 |
| 5 | 代码审查 | Reviewer | 代码变更 | 审查报告 | 无阻塞问题 |
| 6 | 质量验证 | QA | 可运行代码 | 测试报告 | E2E 测试通过 |
| 7 | 发布上线 | Release | 审查通过的代码 | 发布 | 人工审批（夜间模式） |
| 8 | 上线监控 | Monitor | 运行中的系统 | 监控报告 | 自动生成 |

### 6.2 场景编排

| 场景 | Phase 序列 | 用途 |
|------|-----------|------|
| **standard** | 1→2→3→4→5→6→7→8 | 标准开发流程 |
| **hotfix** | 4→5→6→8 | 紧急修复 |
| **review-only** | 5→6→8 | 仅代码审查 |
| **feature** | 1→2→3→4→5→6 | 新功能开发（不含发布） |
| **night-analysis** | 1→2 | 夜间分析（需审批） |
| **day-execute** | 3→4→5→6→7→8 | 日间执行 |
| **deploy** | 7→8 | 仅发布 |
| **monitor** | 8 | 仅监控 |

### 6.3 Phase 间上下文传递

```
Phase N 完成 → Phase N+1 开始：

1. 生成摘要（ContextSummarizer）
   从 Phase N 的 output.json + chat.jsonl 提取关键信息

2. 保存摘要
   追加到 session context.json

3. 创建 Phase N+1 目录
   scenarios/{scenario}/phase-N+1/

4. 构建系统提示
   ├── Phase N+1 角色定义
   ├── 前序摘要（从 context.json 读取）
   └── Phase N+1 可用技能列表

5. 执行 Phase N+1
   对话写入 phase chat.jsonl

三层信息保证：
├── 完整层：所有原始对话在 chat.jsonl（永不丢失）
├── 摘要层：context.json 供 LLM 快速理解
└── 结构层：output.json 供后续 Phase 结构化使用
```

---

## 7. 核心基础设施

### 7.1 工具层（Tools Invocation）

```
工具调用链: LLM → IntentResolver → RiskGate → Executor → ResultFormatter

内置工具（对齐 Claude Code）:
├── read_file          — 读取文件内容
├── write_file         — 写入文件（新建/覆盖）
├── edit_file          — 精确字符串替换
├── run_command        — 执行 Shell 命令
├── use_mcp_tool       — 调用 MCP 工具
├── access_mcp_resource — 访问 MCP 资源
├── glob               — 文件模式匹配搜索
├── grep               — 内容搜索
└── skill_activate     — 激活技能

Plugin 架构:
├── 内置工具（上述 9 个）
├── MCP 插件（通过 MCP Protocol 接入）
└── 自定义插件（Python 模块，@tool 装饰器注册）

风险等级:
├── Level 1: 只读（read_file, glob, grep）— 自主批准
├── Level 2: 低风险写操作（write_file 新文件）— 自主批准
├── Level 3: 修改现有文件（edit_file）— 自主模式批准，交互模式确认
├── Level 4: 执行命令（run_command）— 黑名单检查 + 资源限制
└── Level 5: 高危操作（git push --force 等）— 必须人工审批
```

### 7.2 记忆层（Memory）

```
memory/
├── sessions/                    # 会话层
│   └── {session_id}/
│       ├── chat.jsonl           # 完整对话记录
│       ├── context.json         # 活跃摘要
│       └── metadata.json        # 元信息
│
├── scenarios/                   # 场景层
│   └── {scenario_id}/
│       └── {phase_id}/
│           ├── input.json       # Phase 输入
│           ├── output.json      # Phase 输出
│           ├── chat.jsonl       # Phase 对话
│           └── artifacts/       # 产出文件
│
└── shared/                      # 共享层（跨 Session 知识）
    ├── skills/                  # 技能进化记录
    ├── knowledge/               # 长期学习成果
    └── reports/                 # 执行报告

存储引擎:
├── 文件系统 (JSON/jsonl) — 主存储，truth source，可手动编辑
├── SQLite — 索引层，快速查询（可选）
└── ChromaDB — 向量索引，语义检索（可选）

Persistent + Learning:
├── 跨 Session 知识聚合（同一知识点被多次引用后自动提升权重）
├── 技能自进化（错误驱动的技能改进）
├── 项目上下文持久化（架构文档、编码规范、重要文件注释）
└── 语义文档摄入（自动摄入 markdown 文档到 ChromaDB）
```

### 7.3 LLM Provider 管理

```
支持的 Provider 和模型:
├── DeepSeek
│   ├── deepseek-chat          # 主力编码模型
│   └── deepseek-reasoner      # 推理模型
├── Qwen (通义千问)
│   ├── qwen-turbo             # 低成本
│   ├── qwen-plus              # 标准
│   └── qwen-max               # 高能力
├── Kimi (月之暗面)
│   ├── moonshot-v1-8k
│   ├── moonshot-v1-32k
│   └── moonshot-v1-128k
├── GLM (智谱)
│   └── glm-4
├── MiniMax
│   └── minimax-pro
└── Xiaomi (小米)
    └── mimo-v2

自动降级:
├── 首选模型不可用 → 按 fallback 顺序切换
├── 全部 Provider 不可用 → 队列等待 + 定期重试
└── 熔断器: 连续失败 5 次触发熔断，5 分钟后尝试恢复
```

### 7.4 事件系统

```
事件总线 (Event Bus):
├── 发布-订阅模式
├── 通配符匹配（"phase.*" 匹配所有 Phase 事件）
├── 同步队列（高优先级事件）+ 异步队列（低优先级事件）
├── 事件持久化（用于回放和调试）
└── 死信队列（处理失败的事件）

内置工作流规则:
├── Phase 完成 → 自动生成 Phase 报告
├── Phase 完成 → 自动触发下一 Phase
├── Phase 失败 → 触发自动恢复
├── 场景完成 → 生成场景报告
├── 预算警告 → 发送通知
└── 预算超支 → 触发优雅关闭
```

---

## 8. 安全架构

### 8.1 5 层安全

```
Layer 5: 审计与监控
  - 安全审计日志、异常检测、自动告警

Layer 4: 权限控制
  - 文件权限、网络权限、工具权限

Layer 3: 资源限制
  - CPU (5 min)、内存 (1GB)、进程数 (10)、文件大小 (100MB)、超时 (10 min)

Layer 2: 沙箱隔离
  - 目录隔离（workspace 限定）、进程隔离、网络隔离

Layer 1: 危险操作拦截
  - Bash 命令黑名单、路径白名单、Git 操作限制
```

### 8.2 工具权限矩阵

| 工具 | 自主模式 | 交互模式 | 说明 |
|------|---------|---------|------|
| `read_file` | ✅ | ✅ | 限制在 workspace 内 |
| `glob` / `grep` | ✅ | ✅ | 限制在 workspace 内 |
| `write_file` (新文件) | ✅ | ✅ | 限制在 workspace 内 |
| `edit_file` | ⚠️ 需确认 | ⚠️ 需确认 | 修改现有文件 |
| `run_command` | ⚠️ 黑名单 | ❌ 需确认 | 黑名单 + 资源限制 |
| `git` (安全命令) | ✅ | ⚠️ 需确认 | 仅允许非破坏性操作 |
| `use_mcp_tool` | ⚠️ 需确认 | ⚠️ 需确认 | MCP 工具需审批 |

---

## 9. 目录结构

```
src/sloth_agent/
├── __main__.py                    # 入口（typer app）
│
├── cli/                           # CLI 层
│   ├── __init__.py
│   ├── app.py                     # CLI 子命令 (run/chat/status/skills/scenarios)
│   ├── chat.py                    # Chat REPL
│   ├── context.py                 # 对话上下文
│   ├── install.py                 # 交互式安装
│   └── feishu_server.py           # 飞书 webhook (v1.2)
│
├── core/                          # 核心层
│   ├── __init__.py
│   ├── config.py                  # 配置模型 (pydantic)
│   ├── agent.py                   # AgentEvolve（自主模式）
│   └── tools/
│       ├── tool_registry.py       # 工具注册
│       ├── orchestrator.py        # 工具调度链 (4 层)
│       ├── intent_resolver.py     # 意图解析
│       ├── risk_gate.py           # 风险门控
│       ├── executor.py            # 执行器
│       └── builtin/
│           ├── file_ops.py        # read/write/edit
│           ├── shell.py           # run_command
│           ├── git_ops.py         # git 操作
│           ├── search.py          # glob/grep
│           └── mcp_client.py      # MCP 工具/资源
│
├── agents/                        # Agent 层
│   ├── __init__.py
│   ├── base.py                    # Agent 基类
│   ├── analyst.py                 # 需求分析 Agent
│   ├── planner.py                 # 计划制定 Agent
│   ├── engineer.py                # 编码实现 Agent
│   ├── debugger.py                # 调试排错 Agent
│   ├── reviewer.py                # 代码审查 Agent
│   ├── qa.py                      # 质量验证 Agent
│   ├── release.py                 # 发布上线 Agent
│   ├── monitor.py                 # 上线监控 Agent
│   └── general.py                 # 通用 Agent
│
├── multiagent/                    # 多 Agent 协调
│   ├── __init__.py
│   ├── coordinator.py             # 协调器（任务分发）
│   ├── roles.py                   # 角色定义
│   ├── worktree_manager.py        # Worktree 管理
│   ├── merger.py                  # 结果合并
│   ├── message_bus.py             # 消息总线
│   ├── dependency.py              # 依赖管理
│   ├── conflict_detector.py       # 冲突检测
│   └── models.py                  # 数据模型
│
├── workflow/                      # 工作流层
│   ├── __init__.py
│   ├── registry.py                # Phase + Skill 注册表
│   ├── phases/                    # Phase 实现
│   │   ├── phase_1_analyst.py
│   │   ├── phase_2_planner.py
│   │   └── ...
│   └── gates.py                   # 门控验证
│
├── memory/                        # 记忆层
│   ├── __init__.py
│   ├── store.py                   # 文件系统存储
│   ├── index.py                   # SQLite 索引
│   ├── retrieval.py               # 检索引擎
│   ├── session.py                 # SessionManager
│   ├── summarizer.py              # ContextSummarizer
│   ├── skills.py                  # SkillManager
│   ├── skill_router.py            # SkillRouter
│   └── skill_validator.py         # SkillValidator
│
├── context/                       # 知识库与项目上下文
│   ├── __init__.py
│   ├── project_context.py         # 项目上下文加载器
│   ├── codebase_summary.py        # 代码库摘要
│   ├── semantic_retriever.py      # 语义检索 (ChromaDB)
│   └── injector.py                # prompt 注入器
│
├── observability/                 # 可观测性
│   ├── __init__.py
│   ├── log_manager.py             # 统一日志管理器
│   ├── trace_context.py           # Trace ID 生成
│   ├── log_query.py               # 日志查询 CLI
│   ├── health_diagnosis.py        # 基于日志的健康诊断
│   └── models.py                  # 日志数据模型
│
├── errors/                        # 错误处理
│   ├── __init__.py
│   ├── retry.py                   # 重试处理器
│   ├── circuit_breaker.py         # 熔断器
│   ├── recovery.py                # 场景恢复
│   ├── degradation.py             # 优雅降级
│   ├── escalation.py              # 人工介入
│   └── models.py                  # 错误数据模型
│
├── reports/                       # 报告生成
│   ├── __init__.py
│   ├── generator.py               # 报告生成器
│   ├── delivery.py                # 报告交付渠道
│   ├── collector.py               # 数据收集器
│   ├── templates/                 # 报告模板
│   │   ├── daily.md
│   │   ├── phase.md
│   │   └── exception.md
│   └── models.py                  # 报告数据模型
│
├── integration/                   # 通知与集成
│   ├── __init__.py
│   ├── notification_manager.py    # 通知管理器
│   ├── feishu.py                  # 飞书适配器
│   ├── email.py                   # 邮件适配器
│   ├── webhook.py                 # Webhook 适配器
│   └── models.py                  # 通知数据模型
│
├── cost/                          # 费用与预算
│   ├── __init__.py
│   ├── tracker.py                 # 费用追踪
│   ├── budget_router.py           # 预算感知 LLM 路由
│   ├── pricing.py                 # 定价表加载器
│   └── models.py                  # 费用数据模型
│
├── session/                       # 会话生命周期
│   ├── __init__.py
│   ├── manager.py                 # 会话管理器
│   ├── worktree.py                # Worktree 管理
│   ├── checkpoint.py              # Checkpoint 管理
│   └── models.py                  # 会话数据模型
│
├── events/                        # 事件系统
│   ├── __init__.py
│   ├── bus.py                     # 事件总线
│   ├── handlers.py                # 内置事件处理器
│   ├── workflow_rules.py          # 工作流触发规则
│   ├── replay.py                  # 事件回放
│   └── models.py                  # 事件数据模型
│
├── daemon/                        # 常驻进程
│   ├── __init__.py
│   ├── health.py                  # 健康检查
│   └── watchdog.py                # 看门狗
│
├── security/                      # 安全层
│   ├── __init__.py
│   ├── path_validator.py          # 路径校验
│   ├── sandbox.py                 # 沙箱
│   └── auditor.py                 # 审计日志
│
└── providers/                     # 外部服务
    ├── __init__.py
    ├── llm_providers.py           # LLM 提供商管理
    └── feishu_client.py           # 飞书客户端
```

---

## 10. 数据流

### 10.1 自主模式数据流

```
时钟触发 (cron / schedule / daemon heartbeat)
  → AgentEvolve.run() / Orchestrator.loop()
  → 判断时段（日/夜）
  → 选择 Scenario（standard / hotfix / review-only / ...）
  → 按序执行 Phase：
     ├── Phase.start() → 创建 phase 目录
     ├── Agent.run() → 对话 + 工具调用
     ├── 工具调用 → IntentResolver → RiskGate → Executor → Formatter
     ├── Phase 对话 → 写入 scenarios/{scenario}/{phase}/chat.jsonl
     ├── Phase 输出 → 写入 output.json
     ├── 生成摘要 → 追加到 session context.json
     ├── 发布事件 → Event Bus → 触发报告/通知/下一Phase
     └── Phase.complete() → 进入下一 phase
  → 夜模式 Phase-2 完成 → 推送飞书审批卡片
  → 等待人工确认 → 确认后继续日间 phase
  → 日间 Phase 完成 → 生成日报 → 发送飞书卡片
  → Daemon 写入心跳 → HealthChecker 检查 → Watchdog 监控
```

### 10.2 对话模式数据流

```
用户输入 (REPL: sloth>)
  → ChatSession.loop()
  → 判断输入类型：
     ├── 斜杠命令 → CommandHandler 执行
     ├── 普通对话 → General Agent 响应 → 显示
     ├── /run scenario → SessionManager.start_phase()
     ├── /start autonomous → 启动自主模式（后台）
     ├── /stop → 中止自主模式
     ├── /status → 查看状态
     └── /clear, /context, /help, /quit → REPL 控制
  → 每轮对话 → SessionManager.save_message() → chat.jsonl
  → 工具调用 → 通过工具层执行 → 审计日志 → 费用记录
```

### 10.3 多 Agent 并行数据流

```
Coordinator 分发任务
  → 为每个任务创建独立 worktree + 分支
  → 启动对应角色的 Agent 实例
  → Agent 在独立环境中执行
  → 执行结果写入各自 worktree
  → 结果通过 MessageBus 传递
  → Coordinator 收集所有结果
  → ConflictDetector 检测文件冲突
  → ResultMerger 按策略合并
  → 合并结果提交到目标分支
  → 发布 scene.complete 事件
  → 报告生成 → 通知发送
```

---

## 11. 配置模型

```yaml
# configs/agent.yaml

# 全局
agent:
  name: "sloth-agent"
  workspace: "./workspace"
  timezone: "Asia/Shanghai"

# LLM Provider
llm:
  default_provider: "deepseek"
  fallback_order: ["qwen", "kimi", "glm", "minimax", "xiaomi"]
  fuse_threshold: 5              # 熔断阈值
  fuse_recovery_seconds: 300     # 熔断恢复时间

# 对话
chat:
  max_context_turns: 20
  auto_approve_risk_level: 2
  stream_responses: true
  prompt_prefix: "sloth> "

# 执行
execution:
  auto_execute_hours: "09:00-18:00"
  require_approval_hours: "18:00-09:00"

# 记忆
memory:
  store_path: "./memory/"
  index_enabled: true             # SQLite 索引
  vector_enabled: false           # ChromaDB 向量
  cross_session_learning: true    # 跨 Session 知识聚合
  skill_evolution: true           # 技能自进化

# 安全
security:
  sandbox_enabled: true
  allowed_paths: ["./src/", "./tests/", "./docs/"]
  denied_paths: ["/etc/", "/root/", "~/.ssh/", "~/.aws/"]

# 多 Agent
multi_agent:
  enabled: false
  max_workers: 4
  worktrees:
    base_dir: ".worktrees"
    auto_cleanup: true

# 可观测性
observability:
  logging:
    max_file_mb: 100
    retention_days: 30
  tracing:
    enabled: true
    trace_id_format: "sloth-{session_id}-{phase_id}-{suffix}-{seq}"

# 错误处理
error_handling:
  retry:
    tool: { max_retries: 3, backoff_base: 1.0 }
    skill: { max_retries: 2, backoff_base: 5.0 }
    phase: { max_retries: 1, backoff_base: 10.0 }
  circuit_breaker:
    failure_threshold: 5
    recovery_timeout: 300

# 报告
reports:
  daily:
    enabled: true
    send_time: "22:00"
    channels: ["feishu_card", "file"]
  exception:
    enabled: true
    channels: ["feishu_alert", "file"]

# 通知
notification:
  channels:
    feishu: { enabled: true, webhook_url: "${FEISHU_WEBHOOK_URL}" }
    email: { enabled: false }
    webhook: { enabled: false }

# 费用
cost:
  budget:
    daily_limit: 10.0
    scenario_limit: 3.0
    soft_limit_percent: 0.8
    hard_limit_percent: 1.0

# 会话
session:
  max_concurrent: 5
  checkpoint_interval: 300
  worktrees:
    auto_cleanup: true

# 事件
events:
  persist: true
  max_history: 10000
  dead_letter: { enabled: true }

# 项目上下文
project:
  name: ""
  tech_stack: []
  coding_standards: []

# 守护进程
daemon:
  mode: "foreground"              # foreground | daemon
  heartbeat_interval: 180
  max_missed_heartbeats: 3
  watchdog:
    restart_delay: 60
    max_restart_count: 5
```

---

## 12. 架构优势

### 12.1 优势

| 优势 | 说明 |
|------|------|
| **专用 + 通用 Agent** | 专用 Agent 保障并行能力和上下文隔离，通用 Agent 处理自由形态请求，两者互补 |
| **事件驱动解耦** | 模块间通过事件总线通信，新增模块只需订阅事件，不修改现有代码 |
| **5 层安全默认** | 从命令黑名单到沙箱隔离到资源限制到权限控制到审计，安全层层递进 |
| **文件系统即真相** | 所有状态以 JSON/jsonl 存储，可回溯、可审计、可手动编辑、不依赖数据库 |
| **多模型生态** | 6 个中国 LLM Provider 支持 + 自动熔断降级，不依赖单一模型 |
| **技能可进化** | SKILL.md 格式与 Claude Code 生态兼容，技能可自动进化、用户可自定义 |
| **昼夜循环** | 夜间半自主（需审批）、日间全自主，适配"黑灯工厂"场景 |
| **可观测性内置** | Trace ID 贯穿所有操作，5 层日志分层，CLI 可查询，基于日志的健康诊断 |
| **成本控制** | 定价表 + 预算软硬停机 + 费用预测 + 预算感知 LLM 路由 |

### 12.2 可扩展性

| 扩展点 | 方式 |
|--------|------|
| **新增 Agent** | 继承 Agent 基类，注册到 PhaseRegistry，配置技能和模型即可 |
| **新增 Phase** | 定义 Phase 元数据（Agent、技能、门控、输入输出），注册到 PhaseRegistry |
| **新增技能** | 创建 SKILL.md 文件到对应目录，自动被发现和注册 |
| **新增工具** | 实现 Tool 接口，通过 `@tool` 装饰器注册，或使用 MCP Protocol 接入 |
| **新增通知渠道** | 实现 NotificationChannel 接口，注册到 NotificationManager |
| **新增报告类型** | 创建 Markdown 模板，注册到 ReportGenerator |
| **新增事件处理器** | 实现 EventHandler 接口，通过 EventBus.subscribe() 订阅 |
| **新增 LLM Provider** | 配置 Provider 元数据（API endpoint、定价），注册到 LLMProviderManager |
| **新增安全规则** | 在配置文件中添加路径白名单/命令黑名单，无需修改代码 |
| **新增场景** | 在 YAML 中定义 Phase 序列，注册到 ScenarioRegistry |

扩展性设计保证：
- **开闭原则**：对扩展开放（注册新模块），对修改关闭（不改动现有代码）
- **接口隔离**：每个模块定义清晰的接口，依赖接口而非实现
- **配置驱动**：行为通过 YAML 配置控制，不硬编码
- **事件总线**：模块间通过事件通信，新增模块只需订阅事件

### 12.3 可维护性

| 维护维度 | 设计保障 |
|----------|---------|
| **模块边界清晰** | 15 个功能模块各有明确的职责，通过事件总线通信而非直接调用 |
| **文件系统存储** | 所有状态以 JSON/jsonl 存储，无需数据库管理工具即可检查和修复 |
| **日志可追溯** | Trace ID 贯穿所有操作，可通过 `sloth logs --trace <id>` 查询完整操作链 |
| **Checkpoints** | 关键操作前自动保存 checkpoint，出问题时可恢复到任意检查点 |
| **配置即文档** | YAML 配置即系统行为的文档，无需额外维护配置说明 |
| **错误分类体系** | 4 级错误分类，每级有明确的重试策略和恢复动作 |
| **Runbook** | 常见故障处理手册，自动恢复 + 人工介入双路径 |
| **独立测试** | 每个模块可独立测试，不依赖其他模块的运行状态 |
| **SKILL.md 格式** | 技能指令以人类可读的 Markdown 定义，非代码，非配置，易于修改和审查 |
| **Git 集成** | 所有代码变更通过 Git 管理，worktree 隔离保证并行开发不冲突 |

### 12.4 与参考框架的对比

| 特性 | OpenClaw | Hermes Agent | Claude Code | Codex | **Sloth Agent** |
|------|----------|-------------|-------------|-------|----------------|
| 多 Agent 架构 | ❌ 单 Agent | ✅ 子代理 | ❌ 单 Agent | ❌ 单 Agent | ✅ 8 专用 + 1 通用 |
| 持久常驻 | ✅ Gateway | ✅ Persistent | ❌ | ❌ | ✅ Daemon + Watchdog |
| 技能系统 | ✅ Skills | ✅ Skills | ✅ Skills | ❌ | ✅ SKILL.md (兼容) |
| 持久记忆 | ✅ | ✅ 自积累 | Session | Session | ✅ FS + Learning |
| 自进化能力 | ❌ | ✅ | 部分 | ❌ | ✅ 技能进化 |
| 安全沙箱 | ✅ Risk | ✅ | Risk levels | Risk | ✅ 5 层安全 |
| 多模型支持 | ✅ | ✅ | ❌ | ❌ | ✅ 6 Provider |
| 可观测性 | ✅ | ✅ | ❌ | ❌ | ✅ 日志 + Trace + 指标 |
| 工作流编排 | ✅ Multi | ❌ | ❌ | ❌ | ✅ Phase + Scenario |
| 成本控制 | ❌ | ❌ | ❌ | ❌ | ✅ 预算 + 定价 + 预测 |
| 事件驱动 | ❌ | ❌ | ❌ | ❌ | ✅ Pub-Sub Bus |
| 中国生态 | ❌ | ❌ | ❌ | ❌ | ✅ 6 中国 Provider |

**我们的差异化优势**：多 Agent 并行 + 事件驱动 + 成本控制 + 中国 LLM 生态 + 技能自进化 + 工作流编排。

---

## 13. 规格文档索引

| # | 规格 | 文件 | 状态 |
|---|------|------|------|
| 1 | 总体架构 | `00000000-architecture-overview.md` | 本文件 |
| 2 | Phase-Role Architecture | `20260416-phase-role-architecture-spec.md` | 待审批 |
| 3 | Tools Invocation | `20260416-tools-invocation-spec.md` | 待审批 |
| 4 | Multi-Agent Coordination | `20260416-multi-agent-coordination-spec.md` | 待审批 |
| 5 | Memory Management | `20260416-memory-management-spec.md` | 待审批 |
| 6 | Session Management | `20260416-session-management-spec.md` | 待审批 |
| 7 | Skill Management | `20260416-skill-management-spec.md` | 待审批 |
| 8 | Chat Mode | `20260416-chat-mode-spec.md` | 待审批 |
| 9 | Observability & Logging | `20260416-observability-logging-spec.md` | 已记录 |
| 10 | Error Handling & Recovery | `20260416-error-handling-recovery-spec.md` | 已记录 |
| 11 | Report Generation | `20260416-report-generation-spec.md` | 已记录 |
| 12 | Notification & Integration | `20260416-notification-integration-spec.md` | 已记录 |
| 13 | Cost & Budget | `20260416-cost-budget-spec.md` | 已记录 |
| 14 | Session Lifecycle | `20260416-session-lifecycle-spec.md` | 已记录 |
| 15 | Event System | `20260416-event-system-spec.md` | 已记录 |
| 16 | Knowledge Base | `20260416-knowledge-base-spec.md` | 已记录 |
| 17 | Daemon & Health | `20260416-daemon-health-spec.md` | 已记录 |
| 18 | Sandbox Security | `20260416-sandbox-security-spec.md` | 已记录 |
| 19 | Installation | `20260416-installation-onboarding-spec.md` | 已记录 |
| 20 | Feishu Integration | `20260416-feishu-integration-spec.md` | 待审批 |
| 21 | Architecture v2 | `20260416-architecture-v2.md` | 参考 |

---

## 14. 版本路线图

| 版本 | 核心交付 | 状态 |
|------|---------|------|
| **v1.0** | Phase-Role-Architecture 实现<br>Chat Mode 基础（自由对话 + REPL）<br>Memory 三层结构 + 文件系统存储<br>Session 生命周期管理<br>Skill 统一格式 + 加载机制 | 规划中 |
| **v1.1** | Skill Router（意图识别 + 自动激活）<br>自主模式控制（从 chat mode 启停）<br>Phase 切换上下文衔接（摘要传递）<br>向量检索（ChromaDB 启用）<br>Skill 自动进化<br>Tools Invocation 4 层链 | 规划中 |
| **v1.2** | Multi-Agent 并行协调<br>飞书集成（webhook server + 卡片交互）<br>飞书 session 与 CLI session 统一<br>跨 session 知识聚合<br>Daemon 常驻 + 健康检查 | 规划中 |
| **v1.3** | Observability 统一日志<br>Error Handling 熔断 + 恢复<br>Report Generation 引擎<br>Notification 多渠道<br>Cost & Budget 追踪<br>Event System 事件总线<br>Knowledge Base 项目上下文 | 规划中 |
| **v2.0** | 完整 15 模块架构<br>Plugin 工具生态<br>语义检索增强<br>全链路可观测性<br>生产级稳定性和性能 | 远期 |

---

## 15. 关键设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| Agent 数量 | 8 专用 + 1 通用 | 专用保障并行和上下文隔离，通用处理自由请求 |
| 存储引擎 | 文件系统为主，SQLite/ChromaDB 为索引 | 文件系统可回溯、可审计、可手动编辑 |
| 会话格式 | jsonl（每行一条 JSON） | 流式写入、不丢失、易追加 |
| 技能格式 | Claude Code SKILL.md | 自然兼容、开源生态可复用 |
| CLI 框架 | typer | 与现有 pydantic 自然集成 |
| Phase 切换 | 摘要传递 + 完整记录 | 信息不丢失 + LLM context 有限 |
| 自主/对话模式 | 平行入口，共享基础设施 | 不耦合、各自独立演进 |
| 模块通信 | 事件总线（pub-sub） | 解耦、可扩展、支持事件驱动工作流 |
| 安全策略 | 5 层递进 | 从拦截到隔离到限制到权限到审计 |
| 模型选择 | 6 中国 Provider + 自动降级 | 不依赖单一模型，适配中国生态 |
| 费用控制 | 定价 + 预算 + 预算感知路由 | 自主模式下必须控制成本 |
| 持久化 | Daemon + Watchdog + Checkpoint | 黑灯工厂需要进程常驻和自动恢复 |
| 知识管理 | 4 层（常驻→摘要→结构化→语义） | 渐进式复杂度，按需启用 |

---

*规格版本: v2.0.0*
*创建日期: 2026-04-16*
