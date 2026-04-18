# Sloth Agent 总体架构设计

> 版本: v2.0.0
> 日期: 2026-04-16
> 状态: 草案

> 规范状态说明：本文件是唯一 canonical architecture spec。此前 `archive/20260416-architecture-v2.md` 中已采纳的运行时内核设计已合并入本文件；该文档后续仅作为归档/导读，不再承载独立规范。

---

## 1. 产品定位

Sloth Agent 是一个**产品级的 AI 开发助手**，可理解为 OpenClaw + Hermes Agent 的组合体，借鉴 Claude Code 和 Codex 的最佳实践，并针对中国开发者生态进行深度定制。

**核心价值**：v1.0 聚焦于 **Plan → 全自主开发 → 部署** 的核心场景。通过 3-Agent 串行流水线（Builder → Reviewer → Deployer），实现从计划到上线的全程自主执行，关键节点由自动门控（lint / type-check / test / coverage / smoke-test）把关质量。远期将扩展为 Phase-Role-Architecture（8 阶段 × 8+1 Agent × 37 技能）支持完整开发生命周期。

**工作模式**：
- **v1.0 — 自主模式**：输入一份 Plan，全自主执行 Builder → Reviewer → Deployer 流水线，自动门控替代人工审批
- **v1.1+ — 对话模式**：REPL 交互，自由对话、技能触发、工作流控制
- **v2.0+ — 昼夜循环**：Persistent Daemon 常驻运行，夜间半自主（需求分析→计划→审批），日间全自主

**目标用户**：中国开发者、技术团队、需要自动化开发流程的工程师。

### v1.0 核心场景

> **输入**：一份已完成的 Plan（人工编写或 AI 辅助产出）
> **输出**：代码已开发、测试通过、部署上线
> **约束**：全程自主执行，关键节点自动门控

```
Plan ─→ [Builder Agent] ─→ 门控1 ─→ [Reviewer Agent] ─→ 门控2 ─→ [Deployer Agent] ─→ 门控3 ─→ Done
         解析+编码+测试       lint      代码审查+质量验证     test       部署+验证         smoke
         deepseek            type      qwen-max/claude     coverage   deepseek          test
```

v1.0 不需要需求分析和计划制定（输入已是 plan），不需要 Chat Mode（核心是自主执行），不需要飞书审批（自动门控替代人工）。8-Agent 完整架构保留为远期目标。

---

## 2. 设计原则

> 原则分为 **v1.0（当前实现）** 和 **远期（v2.0+）** 两档。v1.0 追求最小可用，远期保留扩展空间。

| 原则 | v1.0 | 远期（v2.0+） |
|------|------|--------------|
| **Agent 架构** | 3-Agent 串行流水线（Builder → Reviewer → Deployer） | 8 专职 Agent + 1 通用 Agent，支持并行执行 |
| **工具优先** | Agent 通过工具层执行操作，所有操作可审计 | 同左 + Plugin 扩展机制 |
| **技能即指令** | SKILL.md prompt 模板，运行时注入，兼容 Claude Code | 同左 + 技能自动进化 |
| **存储** | 纯文件系统（jsonl），所有状态可手动编辑、可回溯 | + SQLite 索引 + ChromaDB 向量检索 |
| **质量保障** | 自动门控（lint / type / test / coverage / smoke） | + 事件驱动工作流规则 |
| **模型路由** | Stage 级路由：deepseek-v3.2（编码）/ deepseek-r1-0528（调试）/ qwen3.6-plus（审查） | Agent 级独立模型配置 + 自动降级 |
| **自我纠错** | Reflection + Stuck Detection + 自动回滚 | + Speculative Execution（best-of-N） |
| **安全默认** | 路径白名单 + 命令黑名单 + 幻觉防护（HallucinationGuard） | 5 层安全 + 沙箱隔离 + 审计日志 |
| **成本控制** | Token 预算 + Context Window Manager | + 熔断降级 + 费用预测 + 多 Provider 自动切换 |
| **文件系统即真相** | JSON/jsonl 存储，可回溯、可审计、可手动编辑 | 同左 |

---

## 3. 系统全景

### 3.1 v1.0 架构

```
┌─────────────────────────────────────────────────────────────┐
│                      CLI 入口 (typer)                        │
│                  sloth run | sloth init                       │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
               ┌──────────────────────────┐
               │       Orchestrator       │
               │   Plan 解析 → 流水线调度   │
               │   Adaptive Planning      │
               └────────────┬─────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│  Builder Agent │ │ Reviewer Agent │ │ Deployer Agent │
│  deepseek-v3.2   │→│ qwen3.6-plus /  │→│ deepseek-v3.2  │
│  + reasoner    │ │ claude         │ │                │
│  编码+调试+测试 │ │ 审查+质量验证  │ │ 部署+验证      │
│  Reflection    │ │                │ │                │
│  StuckDetector │ │                │ │                │
└───────┬────────┘ └───────┬────────┘ └───────┬────────┘
        │ Gate 1           │ Gate 2           │ Gate 3
        │ lint+type        │ test+coverage    │ smoke-test
        └──────────────────┼──────────────────┘
                           ▼
             ┌──────────────────────────────┐
             │        共享基础设施           │
             ├───────┬───────┬──────┬───────┤
             │ Tools │Skills │Memory│ LLM   │
             │ (CC   │(SKILL │(FS/  │ Stage │
             │ 对齐) │ .md)  │jsonl)│ Route │
             ├───────┴───────┴──────┴───────┤
             │ ContextWindowManager          │
             │ HallucinationGuard            │
             │ StreamProcessor               │
             │ Git Checkpoint (3-level)      │
             │ HookManager (lifecycle hooks) │
             └──────────────────────────────┘
```

          #### 3.1.1 Runtime Kernel：产品入口与执行内核分离

          v1.0 虽然采用 3-Agent 串行流水线，但运行时层面不应理解为“3 个 Agent 各自拥有独立循环”。顶层必须只有一个执行内核。

          ```
          CLI / Daemon / Chat
            │
            ▼
          Product Orchestrator（产品层入口）
            │
            ▼
          Runner（唯一运行时内核）
            │
            ├── prepare()   组装 active agent / phase / context
            ├── think()     调模型得到 next step
            ├── resolve()   final / tool / handoff / retry / interrupt
            ├── persist()   写回 RunState / session / memory
            └── observe()   hooks / tracing / gate / reflection
          ```

          边界规则：
          - `Product Orchestrator` 只负责模式入口、创建/恢复 `RunState`、调用 `Runner.run(...)`
          - `Runner` 是唯一执行循环，推进同一个 run 直到完成、中断或终止
          - `current_agent`、`current_phase` 只是 `RunState` 中的当前所有权指针，而不是独立真相源
          - gate failure、tool approval、resume 都发生在同一个 run 内，而不是被重新拼装成新任务

### 3.2 远期架构（v2.0+）

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
           └──────────────────────┬──────────────────┘
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

## 4. 功能模块架构（19 个模块）

### 4.1 模块总览

每个功能模块有唯一编号（01-99），用于全文引用、TODO 映射和 spec 文档命名。

| # | 模块 | Spec 文件 | 优先级 | 核心职责 |
|---|------|-----------|--------|---------|
| 01 | Phase-Role Architecture | `20260416-01-phase-role-architecture-spec.md` | P0 | 8 专职 Agent + 1 通用 Agent、8 阶段、37 技能、8 场景编排 |
| 02 | Tools Invocation | `20260416-02-tools-invocation-spec.md` | P0 | 4 层调用链（Intent→Risk→Execute→Format）、Plugin 架构 |
| 03 | Multi-Agent Coordination | `20260416-03-multi-agent-coordination-spec.md` | P0 | 任务分发、Worktree 隔离、结果合并、冲突解决 |
| 04 | Memory Management | `20260416-04-memory-management-spec.md` | P0 | 三层记忆（FS 主 + SQLite 索引 + ChromaDB 向量） |
| 05 | Session Management | `20260416-05-session-management-spec.md` | P0 | 会话生命周期、checkpoint、摘要传递 |
| 06 | Skill Management | `20260416-06-skill-management-spec.md` | P0 | SKILL.md 加载、路由匹配、自动进化 |
| 07 | Chat Mode | `20260416-07-chat-mode-spec.md` | P0 | REPL 交互、斜杠命令、上下文管理 |
| 08 | Observability & Logging | `20260416-08-observability-logging-spec.md` | P0 | 统一日志、Trace ID、日志查询 CLI、健康诊断 |
| 09 | Error Handling & Recovery | `20260416-09-error-handling-recovery-spec.md` | P0 | 4 级错误分类、熔断器、优雅降级、人工介入 |
| 10 | Report Generation | `20260416-10-report-generation-spec.md` | P0 | 7 种报告类型、模板引擎、多渠道交付 |
| 11 | Notification & Integration | `20260416-11-notification-integration-spec.md` | P1 | 飞书/邮件/Webhook 适配器、通知路由、去重限流 |
| 12 | Cost & Budget Tracking | `20260416-12-cost-budget-spec.md` | P1 | 6 Provider 定价（含 mimo）、预算软硬停机、费用预测 |
| 13 | Session Lifecycle | `20260416-13-session-lifecycle-spec.md` | P1 | 会话创建/暂停/恢复、分支映射、序列化 |
| 14 | Event System | `20260416-14-event-system-spec.md` | P1 | 发布-订阅事件总线、工作流触发、死信队列 |
| 15 | Knowledge Base | `20260416-15-knowledge-base-spec.md` | P2 | 项目上下文、代码库摘要、语义检索 |
| 16 | Daemon & Health | `20260416-16-daemon-health-spec.md` | P1 | Persistent Daemon、心跳检查、看门狗、自动恢复 |
| 17 | Sandbox Security | `20260416-17-sandbox-security-spec.md` | P0 | 5 层安全、路径白名单、资源限制、审计日志 |
| 18 | Installation | `20260416-18-installation-onboarding-spec.md` | P1 | 交互式安装、环境检查、配置引导 |
| 19 | Feishu Integration | `20260416-19-feishu-integration-spec.md` | P2 | Webhook 服务器、卡片交互、审批通道 |
| 20 | LLM Provider & Routing | `20260417-20-llm-router-spec.md` | P0 | 多 Provider 管理、阶段级路由、熔断降级 |
| 21 | Eval Framework | `20260417-21-eval-framework-spec.md` | P0 | 评估维度、标准任务集、Smoke Test |

> 注：模块编号 01-15 为核心模块，16-19 为辅助模块。模块 20-21 为 v1.0 新增核心模块。另有一份流程规范 `20260417-spec-plan-execute-spec.md` 不在模块编号体系内。

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
   │  (#01)     │ │  Coord (#03)│ │ (#13)     │
   └─────┬──────┘ └─────┬──────┘ └─────┬──────┘
         │              │              │
         └──────────────┼──────────────┘
                        ▼
               ┌─────────────────┐
               │  Core Services  │
               │                 │
               │  #02 Tools      │
               │  #04 Memory     │
               │  #05 Session    │
               │  #06 Skills     │
               │  #15 Knowledge  │
               │  #17 Security   │
               └───────┬─────────┘
                       │
              ┌────────┼────────┐
              ▼        ▼        ▼
        ┌────────┐ ┌────────┐ ┌────────┐
        │ #08 Obs│ │ #09 Err│ │ #12 Cost│
        │ #10 Rep│ │ #14 Ev │ │ #11 Not │
        │ #16 Dmn│ │        │ │ #18 Inst│
        │ #19 Fei│ │        │ │         │
        └────────┘ └────────┘ └────────┘
```

---

## 5. Agent 架构

### 5.1 v1.0: 3-Agent 架构（按上下文耦合度分组）

v1.0 采用 3 个 Agent 的设计，分组原则：**按上下文耦合度 + 审查独立性分组**。编码和调试必须共享上下文，审查必须独立于编码（不同模型、新鲜视角、避免自我认同偏差）。

| Agent | 包含阶段 | 推荐模型 | 职责 | 上下文量级 |
|-------|---------|---------|------|-----------|
| **Builder** | Plan 解析 → 编码 → 调试 → 单元测试 | deepseek-v3.2（编码）<br>deepseek-r1-0528（调试） | 读取 plan、拆分任务、编写代码、运行测试、修复错误 | 重 (~50-60K tokens) |
| **Reviewer** | 代码审查 + 质量验证 | qwen-max 或 claude | 独立审查 Builder 产出，检查代码质量、安全、性能 | 中 (~10-15K tokens) |
| **Deployer** | 部署 + 验证 | deepseek-v3.2 | 执行部署脚本、运行 smoke test、验证上线结果 | 轻 (~3-5K tokens) |

核心设计原则：
- **Reviewer 必须使用不同于 Builder 的 LLM**（同一模型审自己的代码几乎无价值）
- **Agent 间通过结构化数据交接**（不是 LLM 摘要，不会丢信息）
- **每个 Agent 内部管理自己的上下文窗口**（滑动窗口 + 工具结果压缩）

#### 5.1.1 Agent 间结构化交接协议

Agent 间传递确定性数据（git diff、pytest 输出、覆盖率数字），而非 LLM 生成的摘要。数据模型见模块 03 spec。

#### 5.1.1.1 Ownership Contract：handoff 与 skill-as-tool 必须区分

Agent 协作必须区分两种不同语义：

1. `phase_handoff`
当前阶段结束，控制权正式转移给下一个 owner。`current_agent` 与 `current_phase` 更新，下一轮执行默认由新的 owner 接管。

2. `skill-as-tool`
当前 owner 调用一个受限能力来辅助决策或执行，但控制权不转移。返回值进入当前 agent 的上下文，继续由当前 owner 决定下一步。

在 v1.0 的 3-Agent 架构里：
- Builder → Reviewer = `phase_handoff`
- Reviewer → Deployer = `phase_handoff`
- Builder 内调用 investigate / browse / codex 类能力 = `skill-as-tool`

#### 5.1.1.2 Runtime NextStep 协议

运行时统一使用 `NextStep` 协议（type: `final_output` | `tool_call` | `phase_handoff` | `retry_same` | `retry_different` | `replan` | `interruption` | `abort`），详见模块 01 spec。

#### 5.1.2 Builder 内部上下文管理

Builder 是最重的 Agent，内部采用滑动窗口 + 压缩策略：

```
策略: 滑动窗口 + 工具结果压缩

1. 固定保留: Plan 始终在 system prompt 中（不被截断）
2. 完整保留: 最近 3 轮对话 + 当前正在编辑的文件
3. 压缩旧结果:
   - read_file 结果 → "已读取 file_a.py (200行, Python)"
   - run_command 结果 → "pytest: 15 passed, 2 failed (test_auth.py:34, test_db.py:78)"
4. 截断策略: 优先截断最旧的对话轮次 → 压缩 tool results → 降级 system prompt
```

##### v1.0 Context Window 精确管理

Builder Agent 的上下文窗口是 v1.0 最关键的工程约束（单次请求 ~60K tokens），需要精确管理：

```
Token 分区（以 128K context window 为例）:
┌──────────────────────────────────────────────┐
│ System Prompt（固定区）          ~8K tokens   │
│ ├── 角色定义 + 行为规则          ~2K          │
│ ├── Plan 全文（始终保留）        ~4K          │
│ └── 活跃技能（当前任务相关）     ~2K          │
├──────────────────────────────────────────────┤
│ 历史对话（滑动窗口区）          ~40K tokens   │
│ ├── 最近 3 轮完整对话            保留原文     │
│ ├── 更早的对话                   压缩摘要     │
│ └── 历史 Reflection              最近 3 条    │
├──────────────────────────────────────────────┤
│ 工具结果（可压缩区）            ~20K tokens   │
│ ├── 当前编辑文件                 完整保留     │
│ ├── 最近一次 tool 结果           完整保留     │
│ └── 更早 tool 结果               压缩摘要     │
├──────────────────────────────────────────────┤
│ 当前用户消息                    ~5K tokens    │
├──────────────────────────────────────────────┤
│ 预留输出空间                    ~15K tokens   │
└──────────────────────────────────────────────┘
```

Builder Agent 的上下文窗口是 v1.0 最关键的工程约束（单次请求 ~60K tokens），需要精确管理。Token 计数用 tiktoken（或 Provider 自带的 tokenizer），不估算。压缩规则是纯规则（match/case），不调用 LLM，零延迟。窗口管理在每次 LLM 调用前执行，不缓存。实现详见模块 01 spec。

##### 5.1.2.1 Context Boundary：三层上下文分层

上下文分层是 v1.0 避免 prompt 污染和恢复混乱的关键约束：
- **ModelVisibleContext**（模型可见）：history、retrieved_memory、current_task、handoff_payload — 唯一能进入 prompt 的层
- **RuntimeOnlyContext**（运行时）：config、tool_registry、skill_registry、logger、budget_tracker、workspace_handle、secrets — 只供代码与工具层使用，不直接发给模型
- **PersistedRunState**（持久化）：run_state、snapshots、session_refs — 用于恢复、审计、回放，不等价于对话历史

详见模块 01 spec。

#### 5.1.3 自动门控

门控是纯规则判断（exit code、数值阈值），不需要 LLM，执行快且确定性高：

| 门控 | 位置 | 规则 | 失败处理 |
|------|------|------|---------|
| **门控1: 构建质量** | Builder → Reviewer | lint 通过 + type check 通过 + 测试通过 | Builder 自动修复，最多重试 3 次 |
| **门控2: 审查质量** | Reviewer → Deployer | blocking_issues 为空 + coverage ≥ 阈值 | 打回 Builder 修复 |
| **门控3: 部署验证** | Deployer → Done | smoke test 通过 | 自动回滚 + 通知 |

#### 5.1.4 演进路线（3 → N Agent）

3-Agent 是起点，按数据驱动拆分：

| 触发条件 | 动作 |
|---------|------|
| Plan 解析占 Builder 上下文 >30% | 拆出 **Planner Agent** |
| Debug 轮次经常 >5 轮导致上下文溢出 | 拆出 **Debugger Agent** |
| 上线后需要持续监控和异常响应 | 加 **Monitor Agent** |
| 前后端可并行开发 | 引入并行 Builder 实例 |

架构预留：
- Agent 基类设计通用（新 Agent 继承后只需配置模型和工具）
- 结构化交接协议可扩展（新字段向后兼容）
- LLM 路由表是配置文件不是硬编码

### 5.2 远期目标: 8 个专用 Agent + 1 个通用 Agent

> 以下为远期参考设计（v2.0+），v1.0 不实现。

设置专用 Agent 而非单一 Agent 的原因：
1. **并行执行**：多个独立任务可同时推进（如前端和后端同时开发）
2. **上下文隔离**：每个 Agent 有独立的上下文窗口，避免上下文膨胀和信息丢失
3. **角色专业化**：每个 Agent 只能调用所在 Phase 内的技能，行为更可预测
4. **模型优化**：不同 Agent 可使用最适合其任务的模型（编码用 DeepSeek，审查用 Claude）

| Agent 角色 | 所属 Phase | 可用技能 | 推荐模型 | 最大实例 |
|-----------|-----------|---------|---------|---------|
| **Analyst** | Phase 1 需求分析 | brainstorming, writing-plans | qwen3.6-plus | 1 |
| **Planner** | Phase 2 计划制定 | writing-plans, brainstorming | qwen3-max | 1 |
| **Engineer** | Phase 3 编码实现 | test-driven-development, subagent-driven-development | deepseek-v3.2 | 3 |
| **Debugger** | Phase 4 调试排错 | /investigate, /debug | deepseek-r1-0528 | 2 |
| **Reviewer** | Phase 5 代码审查 | requesting-code-review, /review | glm-5.1 / claude-sonnet | 2 |
| **QA** | Phase 6 质量验证 | /qa, /cso | glm-5.1 / claude-sonnet | 2 |
| **Release** | Phase 7 发布上线 | /ship, finishing-a-branch | deepseek-v3.2 | 1 |
| **Monitor** | Phase 8 上线监控 | /health, /retro | qwen3.5-plus | 1 |
| **General** | 无（通用） | 任意技能 | 可配置 | 1 |

### 5.3 远期: 通用 Agent

> 以下为远期参考设计（v2.0+）。v1.0 中 General Agent 的职责由 Builder Agent 兼任。

通用 Agent 的特点：
- 可调用所有 37 个技能，不受 Phase 限制
- 处理对话模式中的自由形态请求
- 处理跨 Phase 的复合任务
- 自主模式中的兜底执行器

### 5.4 远期: Agent 间通信

> 以下为远期参考设计（v2.0+）。v1.0 使用结构化交接协议（见 5.1.1），不使用消息总线。

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

### 6.0 v1.0: 简化流水线（Plan → Build → Review → Deploy）

v1.0 不使用 8-Phase 模型，而是 3-Agent 串行流水线 + 自动门控：

```
                    ┌──────────────────────────────────────────────────────────┐
                    │                    Orchestrator                          │
                    │                                                          │
  Plan (输入) ─────→│  Builder ──→ Gate1 ──→ Reviewer ──→ Gate2 ──→ Deployer  │──→ Done
                    │  (编码+测试)  (lint/   (审查)       (test/   (部署+验证)  │
                    │              type)                  coverage)            │
                    │                                                          │
                    │  失败回路:                                                │
                    │  Gate1 fail → Builder 重试 (max 3)                       │
                    │  Gate2 fail → Builder 修复 → Gate1 → Reviewer            │
                    │  Gate3 fail → 自动回滚 + 通知                             │
                    └──────────────────────────────────────────────────────────┘
```

#### v1.0 阶段定义

| 阶段 | Agent | LLM | 输入 | 输出 | 门控 |
|------|-------|-----|------|------|------|
| Plan 解析 | Builder | deepseek-r1-0528 | Plan 文件 | 任务列表 (结构化) | 无 |
| 编码实现 | Builder | deepseek-v3.2 | 任务列表 | 代码 + 测试 | Gate1: lint ✅ type ✅ |
| 调试修复 | Builder | deepseek-r1-0528 | 失败测试 | 修复代码 | Gate1: 测试通过 |
| 代码审查 | Reviewer | qwen3.6-plus | BuilderOutput | 审查报告 | Gate2: 无阻塞问题 + coverage ≥ 阈值 |
| 部署 | Deployer | deepseek-v3.2 | ReviewerOutput | 部署结果 | Gate3: smoke test ✅ |

#### v1.0 Adaptive Execution（替代线性 Phase）

Builder 内部采用自适应执行循环，而非死板的线性步骤：解析 Plan → 逐个任务执行 → 门控检查 → 失败则 reflect() 分析根因 → 决定重试/重规划/终止。详见模块 01 spec。

#### v1.0 Reflection 机制

Builder 在 gate 失败时调用 `reflect()`，用 reasoner 模型做结构化根因分析。设计参考 Reflexion（verbal reflection）+ SWE-Agent（完整环境观察）+ Aider（确定性工具反馈）。

**核心设计原则：好的观察 > 好的反思——把 lint output、test output、git diff 等确定性信号完整喂给 LLM，而非让它猜。**

##### Reflection 输出 Schema

`Reflection` 模型包含字段：`error_category`（syntax/logic/dependency/design/plan/environment）、`root_cause`、`learnings`、`action`（retry_same/retry_different/replan/abort）、`retry_hint`、`confidence`。详见模块 01 spec。

##### Reflect Prompt 策略

核心原则：喂完整的环境观察（git diff、lint/test 完整输出、当前文件上下文、历史反思），不要摘要。用 reasoner 模型（deepseek-r1-0528），不用 chat 模型。详见模块 01 spec。

##### Stuck Detection（转圈检测）

Agent 最常见的失败模式是陷入死循环。检测规则：(1) 连续 3 次相同 error_category + 相似 root_cause；(2) 连续 3 次 action=retry_same 但问题未解决；(3) confidence 持续下降。脱困策略：第 1 次 stuck → 换方案，第 2 次 → 重规划，第 3 次 → 放弃交给人。详见模块 01 spec。

##### Reflection 在执行循环中的集成

Reflection 在 gate 失败后触发，Stuck detection 优先于 reflection 的 action 判断。详见模块 01 spec。

##### 与技能自进化的衔接

```
单次 Session 内:
  reflect() → Reflection → learnings 注入 context → 指导当前任务重试

跨 Session 持久化:
  Session 结束后 → 扫描所有 Reflection 记录
  ├── 高频 error_category → 触发 SkillGenerate（生成新技能）
  │   例: 连续 5 个 Session 都出现 dependency 错误
  │   → 生成 "Python 依赖管理规范" 技能
  ├── 高频 retry_hint → 提炼为技能条目
  │   例: retry_hint 多次包含 "应该用 pytest.fixture"
  │   → 追加到 "Python 测试规范" 技能
  └── 成功的 retry_different 模式 → 记录为偏好
      例: 方案 A 失败 → 方案 B 成功（共 8 次）
      → 将方案 B 的模式沉淀为技能建议
```

#### v1.0 Adaptive Planning（动态重规划）

Builder 在执行过程中可以中途修正计划，而非死板走完预定步骤。重规划根据已完成结果和当前失败信息重新规划剩余任务。

重规划触发条件：
- Gate 失败且 `reflect()` 判断根因不在当前任务而在计划本身
- 执行中发现新依赖或拀制点（如 API 不存在、库版本不兼容）
- 任务间依赖关系变化（前序任务产出改变了后续任务的输入）

#### v2.0 Speculative Execution（探索性执行，远期需求）

对于不确定性高的任务，并行尝试多种方案取最优：

```
Speculative Execution (best-of-N):
├── 触发条件：任务的 uncertainty_score > 阈值
├── 并行生成 N 个候选方案（N=2~3）
├── 每个方案独立跑门控（lint/type/test）
├── 按门控得分 + 代码质量评分选取最优
└── 依赖: Multi-Agent 并行 + Worktree 隔离（v2.0 基础设施）
```

### 6.1 远期: 8 个 Phase

> 以下为远期参考设计（v2.0+）。

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

1. 生成结构化交接物（Handoff Contract）
  从 Phase N 的 output.json + gate 结果 + artifacts 提取确定性数据

2. 保存交接物
  追加到 session context.json，并保留 output.json 作为真相源

3. 创建 Phase N+1 目录
   scenarios/{scenario}/phase-N+1/

4. 构建系统提示
   ├── Phase N+1 角色定义
  ├── 前序结构化交接物（从 context.json 读取）
   └── Phase N+1 可用技能列表

5. 执行 Phase N+1
   对话写入 phase chat.jsonl

三层信息保证：
├── 完整层：所有原始对话在 chat.jsonl（永不丢失）
├── 交接层：context.json 中的 handoff contract 供下游 Phase 快速理解
└── 结构层：output.json 供后续 Phase 结构化使用
```

补充约束：
- 下游 Phase 不得只依赖自由文本摘要开始执行
- `planner -> engineer`、`engineer -> reviewer`、`reviewer -> deployer` 的交接必须包含结构化 payload
- 摘要可以存在，但只能作为辅助理解层，不能替代 handoff contract

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

#### 7.1.0 与 Runner 的集成关系

`ToolOrchestrator` 是 `Runner.resolve_next_step()` 的一个分支执行器。工具层必须满足三条运行时约束：(1) 工具结果写回 `RunState.tool_history`；(2) 审批型工具返回 `interruption` 而非直接异常中止；(3) 工具失败必须被结构化记录，让 runtime 决定 retry/replan/abort。详见模块 02 spec。

#### 7.1.1 Code Understanding 深度集成（v1.0）

超越 grep/glob 的纯文本搜索，提供 AST 级别的代码理解能力：

```
Code Understanding 工具链:
├── tree-sitter 集成
│   ├── AST 解析（函数/类/方法提取）
│   ├── 符号导航（go-to-definition 级别）
│   └── 作用域分析（变量引用、import 关系）
├── 依赖图分析
│   ├── 模块间 import 关系图
│   └── 变更影响范围评估（改了 A 文件，哪些文件可能受影响）
└── 实现策略
    ├── v1.0: tree-sitter （纯本地，零依赖，支持 Python/JS/TS/Go/Rust）
    └── v2.0: LSP 集成（类型系统 + 重构支持）
```

#### 7.1.2 Tool-Use 学习（v1.0）

Agent 记录工具调用的成功/失败模式，逐步优化工具选择策略：

```
Tool-Use Learning:
├── 记录层
│   ├── 每次工具调用记录: tool_name, args, success, duration, error_type
│   └── 存储在 memory/tool_stats.jsonl
├── 统计层
│   ├── 每个工具的成功率、平均耗时、常见错误
│   └── 工具组合模式（哪些工具常连续使用）
└── 优化层
    ├── 失败率高的工具调用模式 → 自动生成警告注入 system prompt
    └── 高效的工具链 → 提炼为技能建议（与技能自进化协同）
```

#### 7.1.3 LLM Hallucination 防护（v1.0）

Agent 的工具调用可能基于 LLM 幻觉（伪造文件路径、不存在的命令、错误参数）。v1.0 在工具执行器中加入校验层，包括路径验证、命令黑名单、链式命令检测、ReDoS 防护。详见模块 02 spec。

```
工具调用链（更新）:
  LLM → IntentResolver → RiskGate → HallucinationGuard → Executor → ResultFormatter
                                      ^^^^^^^^^^^^^^^^^
                                      新增: 幻觉检测层

RejectedCall 处理:
├── 返回结构化错误信息给 LLM（包含 hint）
├── LLM 根据 hint 修正后重试
├── 连续 3 次 rejected → 触发 Reflection
└── 所有 rejection 记录到 tool_stats.jsonl（供 Tool-Use Learning 分析）
```

#### 7.1.4 Tool Approval / Interruption / Resume

高风险工具调用不应被建模成”执行失败”，而应被建模成”当前 run 暂停”。`Interruption` 和 `ToolExecutionRecord` 数据模型详见模块 02 spec。

生命周期：
1. `Runner` 收到 `tool_call`
2. `ToolOrchestrator` 调用 `RiskGate`
3. 若需审批，返回 `Interruption`
4. `RunState.pending_interruptions` 写入该中断
5. 外部系统批准/拒绝后，从原 `RunState` 恢复执行

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
│   ├── deepseek-v3.2          # 最新基础模型（2025-12）
│   ├── deepseek-r1-0528       # 最新推理模型（2026-01）
│   └── deepseek-v4            # 编码旗舰（即将发布，1T MoE 多模态）
│   [上一代: deepseek-chat, deepseek-reasoner]
│
├── Qwen (通义千问)
│   ├── qwen3.6-plus           # 最新旗舰，代码增强（2026-03）
│   ├── qwen3.5-plus           # 多模态，速度快（2026-02）
│   ├── qwen3-max              # 最大规模文本旗舰
│   └── qwen3-max-thinking     # 旗舰推理模型
│   [上一代: qwen-turbo, qwen-plus, qwen-max]
│
├── Kimi (月之暗面)
│   ├── kimi-k2.5              # 最新旗舰，视觉编码（2026-01）
│   ├── kimi-k2                # 上一代（2025-07，32B/1T）
│   └── kimi-claw              # 浏览器 AI Agent（2026-02）
│   [上一代: moonshot-v1-8k/32k/128k]
│
├── GLM (智谱)
│   ├── glm-5.1                # 最新旗舰，编程+8h持续工作（2026-03）
│   ├── glm-5                  # 新一代旗舰（2025-07）
│   └── glm-4.5-flash          # 免费版
│   [上一代: glm-4]
│
├── MiniMax
│   ├── minimax-m2.7           # 最新旗舰，自进化能力（2026-03）
│   └── minimax-m1             # MoE 推理模型（2025-06）
│
└── Xiaomi (小米)
    ├── mimo-v2-pro            # 最新旗舰（2026-03，1T+/42B）
    ├── mimo-v2-omni           # 全模态 Agent（2026-03）
    └── mimo-v2-flash          # 轻量版（2025-12，309B/15B）
    [上一代: mimo-v2]

自动降级:
├── 首选模型不可用 → 按 fallback 顺序切换
├── 全部 Provider 不可用 → 队列等待 + 定期重试
└── 熔断器: 连续失败 5 次触发熔断，5 分钟后尝试恢复
```

### 7.3.1 Token Budget Manager（v2.0 需求）

> **v1.0 策略**：Builder 滑动窗口 + 工具结果压缩，不做精确 token 预算分配。
> **v2.0 目标**：引入 Token Budget Manager，对单次 LLM 请求进行精细化 token 分配。

```
单次 LLM 请求的 token 分配:
├── System Prompt:       15%  (角色定义 + 技能指令)
├── Context/History:     50%  (对话历史 + 摘要)
├── Tool Definitions:    15%  (工具 schema)
├── User Message:        10%  (当前输入)
└── Reserved for Output: 10%

超出时的截断策略 (按优先级):
1. 截断最旧的对话轮次
2. 压缩 tool results（只保留摘要）
3. 降级 system prompt（移除非必要技能）
```

### 7.4 事件系统

#### v1.x — 轻量 Hook 系统

> v1.x 采用同步 hooks，无持久化、无死信队列，满足基本扩展需求。

内置 hook 点：`run.start`/`run.end`、`phase.start`/`phase.end`、`model.start`/`model.end`、`tool.start`/`tool.end`、`handoff`、`gate.pass`/`gate.fail`、`reflection`、`resume`、`budget.warn`/`budget.over`。`HookManager` 实现详见模块 14 spec。

v1.x tracing 的最小粒度应覆盖：run、turn、model call、tool call、handoff、gate failure、interruption / resume。Hook 与 tracing 都是 runtime 的观察面，不应侵入业务执行逻辑。

#### 7.4.1 Continuation：恢复优先依赖自有 RunState

系统允许多种 continuation 来源，但 `RunState` 始终是第一真相源。`ContinuationState` 模型包含 session_id、snapshot_id、provider_name、provider_token、daemon_thread_id。详见模块 05 spec。

#### v2.0 — 完整事件总线（远期需求）

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

### 7.5 Streaming 架构（v1.0）

现代 Agent 交互必须 streaming 输出，用户不会等 30 秒看一个完整回复。v1.0 的 streaming 需要处理 **文本输出** 和 **工具调用** 交织的场景。

```
Streaming 数据流:

  LLM Provider (SSE)  →  StreamProcessor  →  Renderer
  ┌───────────────┐      ┌──────────────┐     ┌──────────────────┐
  │ text chunk    │─────→│ 文本 → 直接  │────→│ CLI: 逐字输出     │
  │ tool_call     │─────→│ 工具 → 拦截  │     │ 飞书: 分段推送    │
  │ tool_call     │      │  ↓ 执行工具  │     │ WebSocket: chunk  │
  │ text chunk    │      │  ↓ 结果回注  │     └──────────────────┘
  └───────────────┘      └──────────────┘
```

`StreamProcessor` 处理 LLM streaming 输出：文本 chunk 直接输出，tool_call chunk 拦截执行后结果回注。详见模块 02 spec。

```
v1.0 Streaming 渲染（CLI）:
├── 文本 → sys.stdout.write() 逐字符输出
├── 工具调用开始 → 打印 "🔧 调用 read_file(path=...)" 高亮行
├── 工具执行中 → spinner 动画
├── 工具结果 → 折叠显示（超过 10 行则折叠，可展开）
└── 完成 → 打印 token 用量 + 耗时

v1.0 Provider 对接:
├── DeepSeek: SSE (text/event-stream)，兼容 OpenAI 格式
├── Qwen: SSE，兼容 OpenAI 格式
└── 统一适配: 所有 Provider 输出转换为内部 Chunk 格式

关键约束:
├── 不使用 WebSocket（v1.0 无 Web UI）
├── CLI 模式下 streaming 直接写 stdout
├── 飞书模式下 (v1.2) 按段落缓冲后推送（避免过于碎片化）
└── tool call 期间挂起 streaming（串行，不并发）
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

### 8.3 回滚与 Checkpoint 策略（v1.0）

Agent 执行过程中可能产生破坏性变更，需要系统性的回滚能力。v1.0 基于 Git 实现，不引入额外依赖。

```
Checkpoint 层级:

┌─────────────────────────────────────────────────────────────┐
│ Level 3: Session 级                                         │
│   Session 开始时 → git tag sloth/session/{session_id}/start │
│   可回滚整个 Session 的所有变更                               │
├─────────────────────────────────────────────────────────────┤
│ Level 2: 阶段级                                              │
│   每个 Agent 开始前 → git tag sloth/stage/{stage}/start     │
│   Gate 失败时可回滚到阶段起点                                 │
├─────────────────────────────────────────────────────────────┤
│ Level 1: 任务级                                              │
│   Builder 每完成一个 task → git commit (自动)                 │
│   reflect() 判断需要回退时可 revert 到上一个 task commit      │
└─────────────────────────────────────────────────────────────┘
```

`CheckpointManager` 基于 Git 实现 3 级 checkpoint（Session/Phase/Task）和回滚。详见模块 13 spec。

```
回滚触发规则:

├── 任务级回滚（Level 1）
│   ├── reflect() action == "retry_different" → revert 上一个 task commit
│   └── 手动: sloth rollback --last-task
│
├── 阶段级回滚（Level 2）
│   ├── Gate 失败且 Builder 重试 3 次仍失败 → 回滚到阶段起点
│   ├── Reviewer blocking_issues 涉及架构性问题 → 回滚到 Builder 起点
│   └── Deployer smoke test 失败 → 回滚到 deploy 起点
│
└── Session 级回滚（Level 3）
    ├── 用户主动: sloth rollback --session
    └── 预算耗尽且 graceful shutdown 失败 → 自动回滚到 Session 起点

Git tag 清理:
├── Session 成功完成 → 删除该 Session 的所有中间 tag，保留 start/end
├── Session 失败 → 保留所有 tag（用于事后分析）
└── 定期清理: 超过 30 天的 tag 自动删除
```

---

## 9. 目录结构

### 9.0 v1.0 精简目录

```
src/sloth_agent/
├── __main__.py                    # 入口（typer app: sloth run）
│
├── cli/
│   ├── __init__.py
│   └── app.py                     # CLI 子命令 (run/status)
│
├── core/
│   ├── __init__.py
│   ├── config.py                  # 配置模型 (pydantic)
│   ├── orchestrator.py            # 流水线编排（Builder→Gate→Reviewer→Gate→Deployer）
│   └── gates.py                   # 自动门控（lint/type/test/coverage/smoke）
│
├── agents/
│   ├── __init__.py
│   ├── base.py                    # Agent 基类（上下文管理、LLM 调用）
│   ├── builder.py                 # Builder Agent（编码+调试+测试）
│   ├── reviewer.py                # Reviewer Agent（代码审查+质量验证）
│   └── deployer.py                # Deployer Agent（部署+验证）
│
├── tools/
│   ├── __init__.py
│   ├── registry.py                # 工具注册
│   ├── executor.py                # 工具执行器（风险检查 + 执行）
│   └── builtin/
│       ├── file_ops.py            # read/write/edit
│       ├── shell.py               # run_command
│       ├── git_ops.py             # git 操作
│       └── search.py              # glob/grep
│
├── memory/
│   ├── __init__.py
│   └── store.py                   # 文件系统存储（jsonl）
│
├── providers/
│   ├── __init__.py
│   └── llm_router.py             # 阶段级 LLM 路由
│
├── models/
│   ├── __init__.py
│   ├── handoff.py                 # BuilderOutput / ReviewerOutput 交接协议
│   └── plan.py                    # Plan 解析模型
│
└── security/
    ├── __init__.py
    └── path_validator.py          # 路径白名单校验
```

v1.0 不包含: agents/ 下的 8 个专用 Agent、multiagent/、context/、observability/、errors/（完整版）、reports/、integration/、cost/、session/、events/、daemon/。这些在 v2.0+ 按需引入。

### 9.1 远期完整目录

> 以下为远期参考设计（v2.0+）。

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

### 11.0 v1.0 阶段级 LLM 路由配置

v1.0 的核心配置增量——按 Agent 和阶段配置不同的 LLM：

```yaml
# configs/agent.yaml (v1.0 新增部分)

# 阶段级 LLM 路由
agents:
  builder:
    stages:
      plan_parsing:
        provider: "deepseek"
        model: "deepseek-r1-0528"     # 推理强，理解复杂 plan
      coding:
        provider: "deepseek"
        model: "deepseek-v3.2"        # 代码生成质量好 + 便宜
      debugging:
        provider: "deepseek"
        model: "deepseek-r1-0528"     # 需要分析错误根因
    context:
      max_tokens: 60000               # Builder 上下文上限
      keep_recent_turns: 3            # 保留最近 3 轮完整对话
      compress_old_results: true      # 旧工具结果压缩
      plan_in_system_prompt: true     # Plan 始终固定在 system prompt

  reviewer:
    stages:
      review:
        provider: "qwen"
        model: "qwen3.6-plus"         # 必须不同于 coding 的 provider
    context:
      max_tokens: 20000

  deployer:
    stages:
      deploy:
        provider: "deepseek"
        model: "deepseek-v3.2"
    context:
      max_tokens: 8000

# 自动门控阈值
gates:
  build_quality:                       # Gate1: Builder → Reviewer
    lint: true                         # lint 必须通过
    type_check: true                   # type check 必须通过
    tests_pass: true                   # 单元测试必须通过
    max_retry: 3                       # Builder 最多重试 3 次
  review_quality:                      # Gate2: Reviewer → Deployer
    no_blocking_issues: true           # 无阻塞问题
    min_coverage: 0.80                 # 覆盖率 ≥ 80%
  deploy_verify:                       # Gate3: Deployer → Done
    smoke_test: true                   # smoke test 必须通过
    auto_rollback: true                # 失败自动回滚
```

### 11.1 完整配置模型

> 以下包含 v1.0 及远期的完整配置。

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

## 11.5 v1.0: 评估框架（Eval）

没有评估就没有改进基线。v1.0 内置轻量级 eval 框架，用于衡量 Agent 执行质量并指导后续优化。

### 评估维度

| 维度 | 指标 | 采集方式 | 目标 |
|------|------|---------|------|
| **成功率** | 任务完成率（Plan 中的任务 vs 实际完成） | 门控通过/失败记录 | ≥ 80% |
| **质量** | lint 通过率、type check 通过率、test coverage | 门控输出 | lint 100%, coverage ≥ 80% |
| **效率** | 总 token 消耗、总执行时间、重试次数 | Agent 执行日志 | 逐版本下降 |
| **审查独立性** | Reviewer 发现的 blocking issues 数量 | ReviewerOutput | > 0 表示 Reviewer 有价值 |
| **自修复率** | Builder 自动修复成功率（门控失败后重试通过） | 门控+重试记录 | ≥ 60% |

### 标准任务集（Eval Suite）

定义 10-20 个可重复执行的标准任务，每次架构变更后跑一遍：

```yaml
eval_tasks:
  - name: "create-crud-api"
    plan: "evals/plans/crud-api.md"
    expected: { files_created: 4, tests_pass: true, coverage_min: 0.80 }

  - name: "fix-type-error"
    plan: "evals/plans/fix-type-error.md"
    expected: { type_check: true, tests_pass: true, retries_max: 2 }

  - name: "add-unit-tests"
    plan: "evals/plans/add-tests.md"
    expected: { coverage_delta: 0.15, tests_pass: true }

  - name: "refactor-module"
    plan: "evals/plans/refactor.md"
    expected: { tests_pass: true, no_new_lint_errors: true }
```

### 评估产出

每次 eval 运行后生成报告，存储在 `memory/evals/` 下：

```
memory/evals/
├── {date}-{eval_id}/
│   ├── summary.json        # 总分 + 各维度得分
│   ├── tasks/
│   │   ├── create-crud-api.json   # 单任务详细结果
│   │   └── ...
│   └── comparison.json     # 与上次 eval 的对比（回归检测）
```

### v1.0 执行方式

```bash
sloth eval                  # 跑全量 eval suite
sloth eval --task fix-type-error  # 跑单个任务
sloth eval --compare        # 对比最近两次 eval 结果
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
| **模块边界清晰** | 19 个功能模块各有明确的职责，通过事件总线通信而非直接调用 |
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

规格编号与 §4.1 模块编号一一对应。

| # | 规格 | 文件 | 状态 |
|---|------|------|------|
| 00 | 总体架构 | `00000000-00-architecture-overview.md` | 本文件 |
| 01 | Phase-Role Architecture + Workflow Steps | `20260416-01-phase-role-architecture-spec.md` | 待审批 |
| 02 | Tools Definition + Invocation | `20260416-02-tools-invocation-spec.md` | 待审批 |
| 03 | Multi-Agent Coordination | `20260416-03-multi-agent-coordination-spec.md` | 待审批 |
| 04 | Memory Management | `20260416-04-memory-management-spec.md` | 待审批 |
| 05 | Session Management | `20260416-05-session-management-spec.md` | 待审批 |
| 06 | Skill Management + Evolution | `20260416-06-skill-management-spec.md` | 待审批 |
| 07 | Chat Mode | `20260416-07-chat-mode-spec.md` | 待审批 |
| 08 | Observability & Logging | `20260416-08-observability-logging-spec.md` | 已记录 |
| 09 | Error Handling & Recovery | `20260416-09-error-handling-recovery-spec.md` | 已记录 |
| 10 | Report Generation | `20260416-10-report-generation-spec.md` | 已记录 |
| 11 | Notification & Integration | `20260416-11-notification-integration-spec.md` | 已记录 |
| 12 | Cost & Budget | `20260416-12-cost-budget-spec.md` | 已记录 |
| 13 | Session Lifecycle | `20260416-13-session-lifecycle-spec.md` | 已记录 |
| 14 | Event System | `20260416-14-event-system-spec.md` | 已记录 |
| 15 | Knowledge Base | `20260416-15-knowledge-base-spec.md` | 已记录 |
| 16 | Daemon & Health | `20260416-16-daemon-health-spec.md` | 已记录 |
| 17 | Sandbox Security | `20260416-17-sandbox-security-spec.md` | 已记录 |
| 18 | Installation + Global Setup | `20260416-18-installation-onboarding-spec.md` | 已记录 |
| 19 | Feishu Integration | `20260416-19-feishu-integration-spec.md` | 待审批 |
| 20 | LLM Provider & Routing | `20260417-20-llm-router-spec.md` | 待审批 |
| 21 | Eval Framework | `20260417-21-eval-framework-spec.md` | 待审批 |
| — | Architecture v2（归档） | `archive/20260416-architecture-v2.md` | 已合并归档 |

---

## 14. 版本路线图

### 14.0 命名调整

原计划中的版本号偏高，实际产品成熟度需要更诚实的映射。调整如下：

| 原版本 | 新版本 | 原因 |
|--------|--------|------|
| v1.0 | **v0.1.0** | 最小可用原型，3-Agent 串行流水线刚跑通 |
| v1.1 | **v0.2.0** | 在 v0.1.0 基础上加成本管控和容错，仍非成熟产品 |
| v1.2 | **v0.3.0** | 可观测性和错误恢复补齐，产品开始可用 |
| v2.0 | **v0.5~v1.0** | 8-Agent + 昼夜循环 + 知识库，逐步达到市场竞争力 |

### 14.1 v0.1.0 — 最小可用原型（当前版本）

> 目标：证明 "Plan → 全自主开发 → 部署" 的核心链路能跑通
> 定位：技术验证品，离可用还有很大距离
> 状态：**已实现**

**核心能力**：
- 3-Agent 串行流水线：Builder → Reviewer → Deployer
- 自动门控：lint / type-check / test / coverage / smoke-test
- 结构化交接协议：BuilderOutput / ReviewerOutput
- 阶段级 LLM 路由：DeepSeek（编码）/ Qwen（审查）
- 文件系统存储：jsonl 格式，无数据库依赖
- SKILL.md 加载与注入（Claude Code 兼容格式）
- 三层上下文边界：ModelVisible / RuntimeOnly / PersistedRunState
- Git 三级 checkpoint：Session / Stage / Task
- 基础 CLI：`sloth run` 输入 Plan 后跑完整流水线
- 最小 eval 框架：smoke test + 标准任务集

**关键约束**：
- 仅 2 个 LLM Provider（DeepSeek + Qwen）
- 无 fallback / 熔断，Provider 挂了直接报错
- 无成本追踪，不知道花了多少钱
- 无可观测性，出了问题只能看终端输出
- 无错误恢复，失败后需要手动处理
- 无 Chat Mode，只能跑自主流水线

**已实现 spec**：
- 模块 #01 Phase-Role Architecture（v0.1.0 子集）→ `20260416-01-phase-role-architecture-spec.md`
- 模块 #02 Tools Invocation（v0.1.0 子集）→ `20260416-02-tools-invocation-spec.md`
- 模块 #04 Memory Management（v0.1.0 子集）→ `20260416-04-memory-management-spec.md`
- 模块 #06 Skill Management（v0.1.0 子集）→ `20260416-06-skill-management-spec.md`
- 模块 #20 LLM Provider & Routing（v0.1.0 子集）→ `20260417-20-llm-router-spec.md`
- 模块 #21 Eval Framework（v0.1.0 子集）→ `20260417-21-eval-framework-spec.md`

**测试覆盖**：189 tests pass

---

### 14.2 v0.2.0 — 成本管控与容错

> 目标：让 v0.1.0 能用在真实环境中，不被天价账单吓到，不因 Provider 抖动而崩溃
> 定位：勉强能在自己项目上试用
> 状态：**规划完成，待实现**

**核心能力**：
- Cost Tracking：CallRecord 数据模型、16 模型定价表、文件系统存储
- Budget 检查：软限额（80% 警告）+ 硬限额（100% 阻断）
- BudgetAwareLLMRouter：预算不足时自动降级到便宜模型
- CircuitBreaker 熔断器：closed → open → half_open 三态机
- ProviderCircuitManager：多 Provider 独立熔断管理
- LLMRouter fallback 链：首选 Provider 熔断时自动切换备选
- Chat Mode 增强：SessionManager、工具执行集成、自主模式控制
- 新增 slash commands：`/skill`、`/start autonomous`、`/stop`、`/status`
- Builder 上下文窗口优化：token-based 截断、summary 压缩
- Adaptive Execution：gate 失败 / context 不足 / plan 偏离时自动重规划

**预期新增 spec 引用**：
- 模块 #07 Chat Mode → `20260416-07-chat-mode-spec.md`
- 模块 #12 Cost & Budget → `20260416-12-cost-budget-spec.md`
- 模块 #09 Error Handling（CircuitBreaker 部分）→ `20260416-09-error-handling-recovery-spec.md` §4

**实现计划**：`20260417-v1-1-implementation-plan.md`（Task V1-1 ~ V1-5）

---

### 14.3 v0.3.0 — 可观测性与错误恢复

> 目标：出了问题能知道为什么，能自动恢复而不是手动处理
> 定位：可以作为日常开发工具使用
> 状态：**规划中**

**核心能力**：
- LogManager 统一日志：5 层日志分层（app / tool-calls / security / metrics / conversations）
- TraceContext Trace ID：`sloth-{session_id}-{phase_id}-{suffix}-{seq}` 全链路追踪
- LogQuerier 日志查询 CLI：按 level / agent / phase / trace 过滤
- 基于日志的健康诊断：错误风暴检测、心跳检查、Phase 停滞检测
- RetryHandler 重试处理器：指数退避 + 随机抖动 + 可配置重试策略
- ScenarioRecovery 场景恢复：gate 连续失败 / 超时 / 预算超支 / 上下文丢失 / 全 Provider 不可用
- GracefulDegradation 优雅降级：资源受限时只执行核心动作
- HumanInterventionManager 人工介入：escalation 通知 + 建议动作 + 处理追踪
- Feishu 通知（webhook 推送）：执行结果、预算警告、错误上报
- Checkpoint 增强：自动 checkpoint 触发条件（phase.enter / phase.exit / error.critical）

**预期新增 spec 引用**：
- 模块 #08 Observability & Logging → `20260416-08-observability-logging-spec.md`
- 模块 #09 Error Handling & Recovery（全文）→ `20260416-09-error-handling-recovery-spec.md`
- 模块 #11 Notification & Integration → `20260416-11-notification-integration-spec.md`
- 模块 #19 Feishu Integration → `20260416-19-feishu-integration-spec.md`
- 模块 #13 Session Lifecycle（checkpoint 增强）→ `20260416-13-session-lifecycle-spec.md`

---

### 14.4 v0.5 — 多 Agent 与知识库

> 目标：从 3-Agent 扩展到更丰富的角色分工，引入知识库和语义检索
> 定位：开始具备市场竞争力，能对标部分海外产品
> 状态：**远期规划**

**核心能力**：
- 按需求拆分 Agent：Planner / Debugger / QA 从 Builder 中独立
- Multi-Agent 并行协调：Worktree 隔离、冲突检测、结果合并
- 消息总线（SQLite 后端）：Agent 间异步通信、依赖就绪通知
- 完整事件系统：pub-sub 事件总线、工作流触发规则、死信队列、事件回放
- 知识库：项目上下文、代码库摘要、架构文档摄入
- 语义检索（ChromaDB）：向量索引、跨 Session 知识聚合
- Token Budget Manager：精细化 token 分配（System 15% / History 50% / Tools 15% / User 10% / Output 10%）
- Speculative Execution：best-of-N 探索性执行（不确定性高的任务并行尝试多种方案）
- SQLite 索引层：MemoryStore 查询性能优化

**预期新增 spec 引用**：
- 模块 #03 Multi-Agent Coordination → `20260416-03-multi-agent-coordination-spec.md`
- 模块 #04 Memory Management（完整）→ `20260416-04-memory-management-spec.md`
- 模块 #05 Session Management → `20260416-05-session-management-spec.md`
- 模块 #14 Event System → `20260416-14-event-system-spec.md`
- 模块 #15 Knowledge Base → `20260416-15-knowledge-base-spec.md`
- 模块 #10 Report Generation → `20260416-10-report-generation-spec.md`

---

### 14.5 v0.8 — 昼夜循环与生产级稳定性

> 目标：支持 Daemon 常驻运行，夜间自动分析 + 日间自主执行，达到生产可用
> 定位：与 Claude Code / Codex 等国际产品形成差异化竞争
> 状态：**远期规划**

**核心能力**：
- Daemon 常驻进程：后台常驻、心跳检查、看门狗监控、自动恢复
- 昼夜双模：夜间半自主（需求分析 → 计划 → 推送飞书审批）、日间全自主执行
- 飞书卡片交互：审批通道、执行结果推送、实时状态查看
- 完整 5 层安全：沙箱隔离 + 资源限制 + 权限控制 + 审计日志 + 异常检测
- Plugin 扩展机制：自定义工具、MCP 插件、自定义技能
- 全链路可观测性：结构化日志 + Trace + 指标 + 健康看板
- 报告生成引擎：日报 / Phase 报告 / 异常报告、多渠道交付
- LSP 集成：类型系统 + 重构支持（超越 tree-sitter AST）

**预期新增 spec 引用**：
- 模块 #16 Daemon & Health → `20260416-16-daemon-health-spec.md`
- 模块 #17 Sandbox Security → `20260416-17-sandbox-security-spec.md`
- 模块 #18 Installation → `20260416-18-installation-onboarding-spec.md`
- 模块 #01 Phase-Role Architecture（完整 8 阶段）→ `20260416-01-phase-role-architecture-spec.md`

---

### 14.6 v1.0 — 完整 Phase-Role 架构

> 目标：8 专职 Agent + 1 通用 Agent、8 阶段、37 技能、8 场景编排，全面对标国际一流
> 定位：有竞争力的产品，能作为团队主力开发工具
> 状态：**远期愿景**

**核心能力**：
- 8 专职 Agent（Analyst / Planner / Engineer / Debugger / Reviewer / QA / Release / Monitor）+ 1 通用 Agent
- 8 阶段完整编排（需求分析 → 计划制定 → 编码实现 → 调试排错 → 代码审查 → 质量验证 → 发布上线 → 上线监控）
- 37 技能完整生态（自动进化 + 用户自定义）
- 8 场景编排（standard / hotfix / review-only / feature / night-analysis / day-execute / deploy / monitor）
- 完整的 19 模块架构全部落地
- Plugin 工具生态、全链路可观测性、生产级稳定性和性能

**预期覆盖全部 spec**：
- 所有模块 #01 ~ #21 完整实现
- 流程规范 `20260417-spec-plan-execute-spec.md`

---

### 14.7 版本对比总览

| 维度 | v0.1.0 | v0.2.0 | v0.3.0 | v0.5 | v0.8 | v1.0 |
|------|------|------|------|------|------|------|
| Agent 数量 | 3 | 3 | 3-5 | 5-7 | 8+1 | 8+1 |
| 核心场景 | Plan→Build→Deploy | +Chat + 自主模式 | + 自动恢复 | + 并行 + 知识库 | + 昼夜循环 | 全场景 |
| 成本管控 | ❌ | ✅ 定价 + 预算 | ✅ | ✅ | ✅ | ✅ |
| Provider 容错 | ❌ | ✅ fallback + 熔断 | ✅ | ✅ | ✅ | ✅ |
| 可观测性 | ❌ | ❌ | ✅ 5 层日志 + Trace | ✅ | ✅ 健康看板 | ✅ |
| 错误恢复 | ❌ | 部分（重规划） | ✅ 全场景恢复 | ✅ | ✅ | ✅ |
| 通知集成 | ❌ | ❌ | ✅ Feishu webhook | ✅ | ✅ 卡片交互 | ✅ |
| 多 Agent 并行 | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| 知识库 | ❌ | ❌ | ❌ | ✅ ChromaDB | ✅ | ✅ |
| Daemon 常驻 | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| 完整 Phase-Role | ❌ | ❌ | ❌ | ❌ | 部分 | ✅ |
| 目标用户 | 技术验证 | 个人试用 | 日常工具 | 团队可用 | 差异化竞争 | 主力工具 |

---

## 15. 关键设计决策

| 决策 | v1.0 选择 | 远期选择 | 原因 |
|------|----------|---------|------|
| Agent 数量 | **3 Agent**（Builder/Reviewer/Deployer） | 8 专用 + 1 通用 | v1.0 按上下文耦合度分组，远期按需求驱动拆分 |
| Agent 分组原则 | 按上下文耦合度 + 审查独立性 | 按 Phase 绑定 | 编码+调试共享上下文，审查必须独立模型 |
| Agent 间交接 | **结构化数据**（git diff/pytest/coverage） | 消息总线 + 摘要 | 结构化数据不丢信息，摘要是有损压缩 |
| LLM 路由 | **阶段级配置**（不同阶段不同模型） | Agent 级配置 | 审查用不同模型避免自我认同偏差 |
| 上下文管理 | **滑动窗口 + 工具结果压缩** | — | Builder 最重 (~60K tokens)，必须主动管理 |
| 门控机制 | **纯规则自动门控**（exit code/数值） | 人工审批 + 规则门控 | v1.0 全自主，不需要人工确认 |
| 核心场景 | **Plan → 全自主开发到部署** | 昼夜双模 + 对话模式 | v1.0 聚焦一个场景做到极致 |
| 存储引擎 | **纯文件系统** | FS + SQLite + ChromaDB | v1.0 不需要索引和向量检索 |
| 事件系统 | **无**（Agent 串行调用） | Pub-Sub 事件总线 | v1.0 是 3 Agent 串行流水线，不需要事件解耦 |
| 运行时内核 | **单 Runner + RunState** | 单 Runner + 更丰富的 owner/continuation | 避免控制流散落在多个组件中 |
| 恢复真相源 | **RunState / checkpoint** | RunState + session + provider 优化 | provider continuation 不能成为唯一真相源 |
| 会话格式 | jsonl（每行一条 JSON） | jsonl | 流式写入、不丢失、易追加 |
| 技能格式 | Claude Code SKILL.md | SKILL.md | 自然兼容、开源生态可复用 |
| CLI 框架 | typer | typer | 与现有 pydantic 自然集成 |
| 安全策略 | 路径白名单 + 命令黑名单 | 5 层递进 | v1.0 最小安全，远期完整安全 |
| 模型选择 | 2 Provider（DeepSeek + Qwen） | 6 中国 Provider + 自动降级 | v1.0 先跑通，v1.1 加 fallback |
| 演进策略 | **需求驱动拆分**（数据说话） | 设计驱动 | 先跑 3 Agent → 发现瓶颈 → 按需拆 |

---

*规格版本: v2.0.0*
*创建日期: 2026-04-16*
