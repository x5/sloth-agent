# Project TODO

> 最后更新: 20260418 — v0.3 Phase Execution Pipeline + Skill Management + Chat UX 规划完成
> 对齐规范: `docs/specs/00000000-00-architecture-overview.md`
> 当前目标: v0.3 Phase Execution Pipeline（打通 Builder→Reviewer→Deployer 调用链）+ Skill Management + Chat Mode V1.1/V1.2 增强
> 版本映射: 原 v1.0→v0.1, 原 v1.1→v0.2, 原 v1.2→v0.3, 原 v2.0→v0.5~v1.0
> 执行规则: 先确认 spec，再确认 implementation plan；`TODO.md` 默认只维护高优先级任务，且每一项必须与对应 plan 任务一一映射；执行时总是先选当前最高优先级任务

---

## 执行约束

- `TODO.md` 是 implementation plan 的执行视图，不是独立计划源
- 每个 TODO 项都必须能映射到某个已确认 plan 的唯一任务
- 默认仅提升高优先级任务进入活跃区
- 开始执行前，必须先回看对应 plan 任务的详细说明、测试和验证要求

## 活跃任务

### P0: Sloth Agent 介绍文章 HTML

> Spec: `docs/specs/20260416-sloth-agent-intro-article-spec.md`
> Plan: `docs/plans/20260416-sloth-agent-intro-article-implementation-plan.md`
> 规则: 以下 TODO 项与 implementation plan 中的 A1-A5 一一对应

- [x] **Task A1 [P0]: Draft narrative structure and message architecture**
- [x] **Task A2 [P0]: Design the visual system for the article page**
- [x] **Task A3 [P0]: Write article content into the HTML page**
- [x] **Task A4 [P0]: Final polish and validation**
- [x] **Task A5 [P0]: Add original visual elements to reduce text heaviness**

### P0: v0.1 自主流水线实现

> Arch: `docs/specs/00000000-00-architecture-overview.md` §3.1, §5.1, §7.1, §7.2, §9.0
> Spec: 各模块以独立 spec 文件为准，见每项标注；架构总览提供 v0.1 流水线概览
> 范围: 3-Agent 串行流水线（Builder → Reviewer → Deployer）
> 关键约束: 单一 `Runner` 内核 + 结构化交接 + 自动门控 + 文件系统状态
> 模块映射: 模块 01 (§25 运行时内核定义) 包含 Runner/RunState/NextStep 完整语义

依赖链: `1 → 2 → 3 → 4 → 5 → 6 → 7 → 8`

- [x] **Task 1: Runtime Kernel & RunState**
  > Arch: `00000000-00-architecture-overview.md` §3.1.1
  > Spec: `20260416-01-phase-role-architecture-spec.md` §25（运行时内核定义）
  > Plan: `20260416-01-phase-role-architecture-implementation-plan.md` §Task 19（追溯记录）
  - [x] 在 `src/sloth_agent/core/` 中引入统一运行时骨架：`Runner`、`RunState`、`NextStep`
  - [x] 明确 `Product Orchestrator` 与 `Runner` 的边界，避免多套执行循环
  - [x] 统一 `final_output / tool_call / phase_handoff / retry / interruption / abort` 语义
  - [x] 补充对应单元测试，覆盖状态推进与恢复入口

- [x] **Task 2: Tool Runtime 基础能力** ← Task 1
  > Arch: `00000000-00-architecture-overview.md` §7.1
  > Spec: `20260416-02-tools-invocation-spec.md`（模块 #2）
  > Plan: `20260416-02-tools-invocation-implementation-plan.md`（已合并 v10 tool runtime plan）
  - [x] 统一 `ToolRegistry` / `ToolOrchestrator` 接口，纳入 `Runner.resolve()` 分支
  - [x] 优先落地 v0.1 核心工具：`read`、`write`、`edit`、`run_command`、`glob`、`grep`
  - [x] 接入 `HallucinationGuard`、路径白名单、命令黑名单
  - [x] 为工具调用记录审计信息与结构化结果，便于后续 gate / tracing / replay

- [x] **Task 3: Builder Agent Runtime** ← Task 2
  > Arch: `00000000-00-architecture-overview.md` §5.1
  > Spec: `20260416-01-phase-role-architecture-spec.md`（模块 #1，Builder 定义）
  > Plan: `20260416-01-phase-role-architecture-implementation-plan.md` §Task 8/9/10
  - [x] 将 Plan 解析、编码、调试、单元测试收敛到 Builder phase
  - [x] 实现 `ContextWindowManager`，区分 system、历史、工具结果、输出预留
  - [x] 接入 Reflection / Stuck Detection / 自动重试入口
  - [x] 产出结构化 `BuilderOutput`，作为 Builder → Reviewer 的唯一交接物

- [x] **Task 4: Gate 机制与 Phase Handoff** ← Task 3
  > Arch: `00000000-00-architecture-overview.md` §5.1.3, §5.1.1
  > Spec: `20260416-01-phase-role-architecture-spec.md`（模块 #1，Gate + Handoff 定义）
  > Plan: `20260416-01-phase-role-architecture-implementation-plan.md` §Task 18
  - [x] 实现 Gate1 / Gate2 / Gate3 的纯规则判断，不依赖 LLM
  - [x] 固化 `phase_handoff` 与 `skill-as-tool` 的不同语义
  - [x] 对齐 `BuilderOutput` / `ReviewerOutput` 数据结构
  - [x] 打通 gate failure → retry / rollback / interrupt 的运行时流转

- [x] **Task 5: Reviewer Agent Runtime** ← Task 4
  > Arch: `00000000-00-architecture-overview.md` §5.1
  > Spec: `20260416-01-phase-role-architecture-spec.md`（模块 #1，Reviewer 定义）
  > Plan: `20260416-01-phase-role-architecture-implementation-plan.md` §Task 15
  - [x] 实现 Reviewer phase，要求使用不同于 Builder 的模型路由
  - [x] 聚焦代码审查、质量验证、安全/性能 blocking issues 识别
  - [x] 生成结构化 `ReviewerOutput`，支持 Reviewer → Deployer handoff
  - [x] 补充 reviewer 审查有效性的测试与最小评估用例

- [x] **Task 6: Deployer Agent Runtime** ← Task 5
  > Arch: `00000000-00-architecture-overview.md` §5.1
  > Spec: `20260416-01-phase-role-architecture-spec.md`（模块 #1，Deployer 定义）
  > Plan: `20260416-01-phase-role-architecture-implementation-plan.md` §Task 16
  - [x] 实现部署执行与 smoke test 验证链路
  - [x] 支持 Gate3 失败后的自动回滚与通知钩子
  - [x] 明确部署产物、部署日志、验证结果的落盘格式
  - [x] 补充 end-to-end 部署阶段测试

- [x] **Task 7: FS Memory / Checkpoint / Skill Loading** ← Task 6
  > Arch: `00000000-00-architecture-overview.md` §7.2
  > Spec: `20260416-04-memory-management-spec.md`（模块 #4）+ `20260416-06-skill-management-spec.md`（模块 #6）
  > Plan: `20260416-04-memory-management-implementation-plan.md` + `20260416-06-skill-management-implementation-plan.md` + `20260416-13-session-lifecycle-implementation-plan.md`
  - [x] 将运行状态、阶段产物、工具记录、gate 结果统一写入文件系统
  - [x] 建立 checkpoint 保存/恢复机制，作为回滚与 resume 基础
  - [x] 打通 `SKILL.md` 加载与按需注入机制
  - [x] 约束模型可见上下文、运行时上下文、持久化状态三层边界

- [x] **Task 8: CLI 集成与 v0.1 验证闭环** ← Task 7
  > Arch: `00000000-00-architecture-overview.md` §9.0, §11.0
  > Spec: `20260416-18-installation-onboarding-spec.md`（模块 #18）
  > Plan: `20260417-20-llm-router-implementation-plan.md` + `20260416-18-installation-onboarding-implementation-plan.md` + `20260417-21-eval-framework-implementation-plan.md`
  - [x] 打通 `sloth run` 主路径，输入 Plan 后可跑完整流水线
  - [x] 配置 v0.1 阶段级模型路由（Builder / Reviewer / Deployer）
  - [x] 增加最小 eval / smoke 场景，验证成功率、质量门控、自修复链路
  - [x] 跑通一条真实示例并更新 README / 使用文档
  - [x] 实现全局安装脚本 `scripts/install.sh`（macOS/Linux/WSL2）
  - [x] 实现全局安装脚本 `scripts/install.ps1`（Windows PowerShell）
  - [x] 采用 Claude Code 安装模型：自检 → 克隆 → venv → CLI shim → PATH → 验证 → smoke test

### P1: v0.2 扩展实现

> Arch: `00000000-00-architecture-overview.md` §5, §7.3
> Plan: `20260417-v1-1-implementation-plan.md`（原 v1.1 计划，重命名为 v0.2）
> 依赖链: `V0.2-1 → V0.2-1.5 → V0.2-1.6 → V0.2-2 → V0.2-3 → V0.2-4 → V0.2-5`
> 范围: 成本管控 + Provider 容错 + Chat 增强 + 上下文优化 + 自适应执行

- [x] **Task V0.2-1: Cost Tracking 基础** ← v0.1 Task 8
  > Arch: `00000000-00-architecture-overview.md` §7.3
  > Spec: `20260416-12-cost-budget-spec.md`
  > Plan: `20260417-v1-1-implementation-plan.md` §Task V1-1
  - [x] 实现 `CostTracker` 数据模型与文件系统存储
  - [x] 内置定价表覆盖 spec 中 16 个模型
  - [x] `BudgetAwareLLMRouter` 软/硬限额检查
  - [x] 在 ToolRuntime 的 LLM 调用路径中接入 `record_call()`

- [x] **Task V0.2-1.5: ConfigManager + config.json 统一配置** ← v0.1 Task 8
  > Arch: `00000000-00-architecture-overview.md` §9.0
  > Spec: `20260416-18-installation-onboarding-spec.md` §6.5（模块 #18）
  > Plan: `20260416-18-installation-onboarding-implementation-plan.md` §Task 3/4/5
  - [x] 实现 `ConfigManager`：三级配置合并（user → project → local）
  - [x] 定义配置数据类：`SlothConfig`、`LLMConfig`、`ProviderConfig` 等
  - [x] 创建 `configs/config.json.example` 模板
  - [x] 实现 `sloth config` CLI 命令（查看/设置/验证/env 列出缺失 Key）
  - [x] `ConfigManager.get_api_key()` 从环境变量解析实际 Key
  - [x] 安装脚本同步生成全局 `config.json`

- [x] **Task V0.2-1.6: `sloth config init --interactive` 交互式向导** ← Task V0.2-1.5
  > Arch: `00000000-00-architecture-overview.md` §9.0
  > Spec: `20260416-18-installation-onboarding-spec.md` §6.5.7（模块 #18）
  > Plan: `20260416-18-installation-onboarding-implementation-plan.md` §Task 7
  - [x] 安装 `prompt_toolkit>=3.0` 依赖
  - [x] 实现交互式向导：作用域 → Provider → API Key → 工作空间 → 确认 → 写入 → 验证
  - [x] API Key 隐藏输入（password 模式）
  - [x] 配置写入后自动 `sloth config validate` 验证
  - [x] 编写交互向导测试（模拟输入流）

- [x] **Task V0.2-2: Provider Fallback / 熔断降级** ← Task V0.2-1.6
  > Arch: `00000000-00-architecture-overview.md` §7.3
  > Spec: `20260416-07-chat-mode-spec.md` + `20260416-09-error-handling-recovery-spec.md` §4
  > Plan: `20260417-v1-1-implementation-plan.md` §Task V1-2
  - [x] `CircuitBreaker` 三态机 (closed/open/half_open)
  - [x] `ProviderCircuitManager` 多 provider 熔断管理
  - [x] LLMRouter 集成 fallback 链
  - [x] 全部 provider 不可用时降级到 MockProvider

- [x] **Task V0.2-3: Chat Mode 增强（REPL + streaming）** ← Task V0.2-2
  > Arch: `00000000-00-architecture-overview.md` §5 设计原则
  > Spec: `20260416-07-chat-mode-spec.md`
  > Plan: `20260417-v1-1-implementation-plan.md` §Task V1-3
  - [x] `SessionManager` 创建/加载/保存 chat session
  - [x] 对话历史持久化 + 上下文截断策略
  - [x] REPL 集成 tool call 执行 + 用户确认（增强版 REPL）
  - [x] v0.2 新增 slash commands: `/skill`, `/start autonomous`, `/stop`, `/status`
  - [x] `AutonomousController` 自主模式控制

- [x] **Task V0.2-4: Builder 上下文窗口管理优化** ← Task V0.2-3
  > Arch: `00000000-00-architecture-overview.md` §5.1.2
  > Spec: `20260416-01-phase-role-architecture-spec.md`
  > Plan: `20260417-v1-1-implementation-plan.md` §Task V1-4
  - [x] ContextWindowManager 改进为 token-based 截断
  - [x] 增加 summary 压缩: 早期对话生成摘要
  - [x] Token 计数器 (tiktoken 或简化估算)

- [x] **Task V0.2-5: Adaptive Execution（自适应重规划）** ← Task V0.2-4
  > Arch: `00000000-00-architecture-overview.md` §6.0
  > Spec: `20260416-01-phase-role-architecture-spec.md`
  > Plan: `20260417-v1-1-implementation-plan.md` §Task V1-5
  - [x] `AdaptiveTrigger` 检测 gate 失败/context 不足/plan 偏离
  - [x] `Replanner` 接收当前状态 → 生成 updated plan
  - [x] Runner 集成 adaptive trigger 检测

### 其他活跃任务

> 以下任务已随 Task 1-8 实现完毕，标记为完成

- [x] **[P0]** Tools 与运行时内核对齐，禁止游离在 Runner 之外 → 随 Task 2 完成
- [x] **[P0]** 结构化 Agent 交接协议落地（BuilderOutput / ReviewerOutput）→ 随 Task 4 完成
- [x] **[P1]** 阶段级模型路由配置（Builder / Reviewer / Deployer）→ 随 Task 8（LLMRouter）完成
- [x] **[P1]** 文件系统记忆与 checkpoint 统一格式 → 随 Task 7 完成

## 近期 Backlog

- [ ] **[P0][v0.3]** Phase Execution Pipeline（Builder→Reviewer→Deployer 打通）@agent @20260418
  > Arch: `00000000-00-architecture-overview.md` §3.1, §5.1
  > Spec: `20260416-01-phase-role-architecture-spec.md` §25
  > Plan: `20260416-01-phase-role-architecture-implementation-plan.md` §Task PE-1~PE-5
  > 范围: Runner Agent Dispatch + Gate Wiring + Builder LLM + CLI Pipeline + E2E Tests
  > 现状: Runner.run() 循环 + resolve 8 分支 + Gate1/2/3 已实现，但 think() 为 NotImplementedError，Agent 未接入循环

- [ ] **[P0][v0.3]** Skill 管理机制完善（内置 skill + 路由 + 注入 + 验证）@agent @20260418
  > Arch: `00000000-00-architecture-overview.md` §6.0
  > Spec: `20260416-06-skill-management-spec.md`
  > Plan: `20260416-06-skill-management-implementation-plan.md` §Task S1~S5
  > 范围: SkillValidator + SkillRouter + 5 内置 skill + SkillInjector + SkillRegistry
  > 依赖: v0.2 已完成 SkillManager 基础加载能力

### V0.3 Chat Mode V1.1/V1.2 增强

> Spec: `20260416-07-chat-mode-spec.md`
> 依赖链: `Phase Pipeline (P0) → Chat-2 → Chat-4 → Chat-5`
>           `Skill Mgmt (P0) → Chat-3`
>           `Chat-1 独立，无依赖`

- [ ] **[P0][v0.3]** Chat-2: AutonomousController 接真实流水线 ← Phase Pipeline
  > Arch: §9.2 | Spec: `20260416-07-chat-mode-spec.md` §3.5
  > Plan: 待创建
  > 范围: 将 `_autonomous_executor` 从 sleep placeholder 替换为真实 Runner 调用，接入 `sloth run` 的完整流水线
  > 现状: executor 只循环 `time.sleep(0.5)`，无真实执行
  > 验收: `/start autonomous` 后能实际跑 Builder→Reviewer→Deployer 流水线，`/status` 显示真实进度

- [ ] **[P0][v0.3]** Chat-3: `/skill <name>` 真正执行 ← Skill Management
  > Arch: §6.0 | Spec: `20260416-07-chat-mode-spec.md` §3.5
  > Plan: 待创建
  > 范围: 将 `_execute_skill` 从打印 markdown 改为通过 SkillRegistry 加载 + 工具调用执行
  > 现状: 只 `console.print(Markdown(skill.content))`，无实际执行
  > 验收: `/skill review` 等命令能触发真实技能执行链路

- [ ] **[P1][v0.3]** Chat-4: `/run <scenario>` + `/phase <id>` 命令实现 ← Chat-2
  > Arch: §3.4 | Spec: `20260416-07-chat-mode-spec.md` §3.4, §3.5
  > Plan: 待创建
  > 范围: 新增两个 slash command，支持从 chat 内触发工作流场景和单个 phase 执行
  > 验收: `/run standard` 启动场景，`/phase 1` 执行指定 phase

- [ ] **[P1][v0.3]** Chat-5: Phase 切换上下文衔接 ← Chat-4
  > Arch: §3.4 | Spec: `20260416-07-chat-mode-spec.md` §3.4 "Phase 切换时的上下文衔接"
  > Plan: 待创建
  > 范围: Phase 切换时生成对话摘要 → 切换 LLM → 注入 phase 系统提示 + 前序摘要 → 保存 phase 产物
  > 现状: 完全未实现
  > 验收: Phase 切换后上下文不断裂，前序摘要正确注入新 phase 系统提示

- [ ] **[P0][v0.3]** v0.2 遗漏修复：Cost Tracking 接入 LLM 调用路径 @agent @20260418
  > Arch: §7.3 | Spec: `20260416-12-cost-budget-spec.md`
  > Plan: `20260417-v1-1-implementation-plan.md` §Task V0.2-1
  > 范围: 在 `llm_providers.py` 调用链中接入 `CostTracker.record_call()`，确保每次 LLM 请求自动计费
  > 现状: CostTracker 模型+定价表+BudgetRouter 已实现，但 record_call() 仅在测试中调用，生产路径未接入
  > 验收: 任意 LLM 请求后能在 cost/ 目录下看到对应记录，CLI 可查询

- [ ] **[P0][v0.3]** v0.2 遗漏修复：AdaptiveTrigger 接入 Runner 循环 @agent @20260418
  > Arch: §6.0 | Spec: `20260416-01-phase-role-architecture-spec.md`
  > Plan: `20260417-v1-1-implementation-plan.md` §Task V0.2-5
  > 范围: Runner.run() 循环中主动检测 AdaptiveTrigger（gate 失败/上下文溢出/plan 偏离/卡顿），自动调用 Replanner 生成 updated plan
  > 现状: AdaptiveTrigger + Replanner 已实现且有测试，但 Runner.run() 不会主动调用它们
  > 验收: gate 失败 3 次后 Runner 自动触发 replan，而非无限 retry_same

- [ ] **[P1][v0.3]** CLI Cost 查询命令 @agent @20260418
  > Arch: §9.0 | Spec: `20260416-12-cost-budget-spec.md` §5
  > Plan: `20260417-v1-1-implementation-plan.md` §Task V0.2-1
  > 范围: `sloth cost` 子命令 — 查看今日/本周/本月花费、预算使用率、按 Provider 分解
  > 验收: `sloth cost` 可列出花费汇总，`sloth cost --today` 显示当日明细

- [ ] **[P1][v0.3]** Chat 消息持久化修复 ← None（独立，无依赖）@agent @20260418
  > Arch: §7.2 | Spec: `20260416-07-chat-mode-spec.md` §3.4
  > Plan: 待创建
  > 范围: REPL 循环中接入 `SessionManager.save_session()`，确保消息写入 `chat.jsonl`，退出时保存最终摘要
  > 现状: `add_message()` 只存内存，`save_session()` 从未调用，退出后对话丢失
  > 验收: 退出 chat 后 `.sloth/sessions/chat/<id>.jsonl` 存在且含完整对话记录，下次启动可加载

- [ ] **[P1][v0.3]** CLI Chat 友好化（面向非技术用户）← None（独立，无依赖）@agent @20260418
  > Arch: §5 | Spec: `20260416-07-chat-mode-spec.md` §3.6
  > Plan: `20260416-07-chat-mode-implement-plan.md` §Task 3-9
  > 范围: 启动欢迎 + 预设问题、自然语言帮助、中文优先、结构化输出、确认卡片、进度可视化
  > 验收: 6 项 UX 改进全部实现 + 16 tests pass + 不引入新依赖

- [ ] **[P1][v0.3]** `sloth uninstall` 卸载命令 @agent @20260418
  > Arch: §10 | Spec: `20260416-18-installation-onboarding-spec.md` §10.8
  > Plan: `20260416-18-installation-onboarding-implementation-plan.md` §Task 8
  > 范围: `sloth uninstall` — 删除 shim + ~/.sloth-agent/ + PATH 清理，支持 --dry-run / --full / --yes
  > 验收: 9 tests pass，dry-run 不删除文件，正常模式交互式确认，--full 连配置也删除

- [ ] **[P1][v0.3]** 基础 Observability（结构化日志 + Trace ID）@agent @20260416
  > Arch: §7.4 | Spec: `20260416-08-observability-logging-spec.md` | Plan: 待创建
  > 备注: v0.2 完成后可进入，为 Runner 接入 LogManager + TraceContext

## 远期 Backlog

- [ ] **[P2][v0.3]** Error Recovery（重试 + 基本恢复）@agent @20260416
  > Arch: — | Spec: `20260416-09-error-handling-recovery-spec.md` | Plan: 待创建
- [ ] **[P2][v0.3]** Feishu 通知（webhook 推送执行结果）@agent @20260416
  > Arch: — | Spec: `20260416-19-feishu-integration-spec.md` | Plan: 待创建
- [ ] **[P2][v0.3]** Checkpoint 保存与恢复增强 @agent @20260416
  > Arch: `00000000-00-architecture-overview.md` §8.3 | Spec: `20260416-04-memory-management-spec.md` | Plan: 待创建
- [ ] **[P2][v0.5]** 按需拆分 Agent（Planner / Debugger）@agent @20260416
  > Arch: §5.2, §6.1, §6.2 | Spec: `20260416-01-phase-role-architecture-spec.md` | Plan: 待创建
- [ ] **[P2][v0.5]** Multi-Agent 并行协调 + Worktree 隔离 @agent @20260416
  > Arch: §10.3 | Spec: `20260416-03-multi-agent-coordination-spec.md` | Plan: 待创建
- [ ] **[P2][v0.5]** 事件总线（pub-sub + dead letter queue）@agent @20260416
  > Arch: §7.4.1 v2.0 | Spec: `20260416-14-event-system-spec.md` | Plan: 待创建
- [ ] **[P2][v0.5]** 知识库 + 语义检索（SQLite / ChromaDB）@agent @20260416
  > Arch: §7.2 | Spec: `20260416-15-knowledge-base-spec.md` | Plan: 待创建
- [ ] **[P2][v0.8]** Daemon 常驻 + Watchdog @agent @20260416
  > Arch: — | Spec: `20260416-16-daemon-health-spec.md` | Plan: 待创建

## 阻塞

> 无阻塞。v0.1 流水线全部实现完成并发布。

### P0: v0.1 Plan 创建（已全部完成）

> 规则: 每个 Plan 必须引用 architecture-overview.md 对应章节，且包含具体文件路径/函数/测试
> 依赖链: `P1 → P2 → P3 → P4 → P5 → P6 → P7 → P8`

- [x] **P1: 创建 Runtime Kernel & RunState plan** → 已并入 `20260416-01-phase-role-architecture-implementation-plan.md` §Task 19
- [x] **P2: 创建 Tool Runtime plan** → 已并入 `20260416-02-tools-invocation-implementation-plan.md`
- [x] **P3: 创建 Builder Agent plan** → 已并入 `20260416-01-phase-role-architecture-implementation-plan.md` §Task 8/9/10
- [x] **P4: 创建 Gate & Handoff plan** → 已并入 `20260416-01-phase-role-architecture-implementation-plan.md` §Task 18
- [x] **P5: 创建 Reviewer Agent plan** → 已并入 `20260416-01-phase-role-architecture-implementation-plan.md` §Task 15
- [x] **P6: 创建 Deployer Agent plan** → 已并入 `20260416-01-phase-role-architecture-implementation-plan.md` §Task 16
- [x] **P7: 创建 Memory / Checkpoint / Skill plan** → `20260416-04-memory-management-implementation-plan.md` + `20260416-06-skill-management-implementation-plan.md` + `20260416-13-session-lifecycle-implementation-plan.md`
- [x] **P8: 创建 CLI 集成与验证 plan** → `20260417-20-llm-router-implementation-plan.md` + `20260416-18-installation-onboarding-implementation-plan.md` + `20260417-21-eval-framework-implementation-plan.md`

## 已完成

- [x] **[P0]** 框架规范文档编写 @agent @20260415
- [x] **[P0]** Document Naming Convention 制定 @agent @20260415
- [x] **[P1]** Workflow Process Spec 定义 @agent @20260415
- [x] **[P1]** Tools Design Spec 定义 @agent @20260415
- [x] **[P0]** Phase-Role-Architecture Spec 编写 @agent @20260416
- [x] **[P0]** Phase-Role-Architecture Plan 编写 @agent @20260416
- [x] **[P0]** Architecture v2 内容并入 canonical overview，旧文档归档 @agent @20260416
- [x] **[P0]** v0.1 发布：3-Agent 流水线 189 tests pass，端到端 smoke 验证 @agent @20260417

---

## 任务标签说明

| 标签 | 说明 |
|------|------|
| `P0` | 最高优先级，当前迭代必须完成 |
| `P1` | 高优先级，当前迭代应该完成 |
| `P2` | 中优先级，当前迭代可以完成 |
| `[v0.1] / [v0.2] / [v0.3] / [v0.5] / [v0.8] / [v1.0]` | 对应 roadmap 版本阶段 |
| `@owner` | 任务负责人（agent/human） |
| `@YYYYMMDD` | 创建或迁移日期 |
| `← Task N` | 依赖前置任务 N |

---

## 更新日志

| 日期 | 更新内容 |
|------|---------|
| 20260415 | 初始版本，创建框架基础任务 |
| 20260416 | 整合 Phase-Role-Architecture 任务链，建立依赖关系 |
| 20260416 | 按 canonical architecture 重排 TODO：v0.1 先做 3-Agent 自主流水线，Phase-Role-Architecture 下沉为远期任务 |
| 20260417 | 创建 Spec → Plan → Execute 流程规范；补齐 v0.1 全部 8 个 implementation plan（Task 1-8） |
| 20260417 | 完成 Task 1-8，189 tests pass，3-Agent 流水线闭环 |
| 20260417 | 版本重命名：原 v1.0→v0.1, v1.1→v0.2, v1.2→v0.3, v2.0→v0.5~v1.0 |
| 20260417 | v0.2 规划完成：5 个 Task (V0.2-1~V0.2-5) 纳入活跃区 |
| 20260417 | 产品路线图更新：architecture-overview.md §14 建立 v0.1→v1.0 六版本完整路线图 |
| 20260418 | 引入 config.json 统一配置管理（模块 #18），安装脚本支持 API Key 模板 + 自动填充 |
| 20260418 | V0.2-1 Cost Tracking 完成：CostTracker、定价表、BudgetAwareLLMRouter、41 新测试（251 total） |
| 20260418 | V0.2-1.6 交互式配置向导标记完成（前次 session 实现） |
| 20260418 | V0.2-2 Provider Fallback 完成：CircuitBreaker、ProviderCircuitManager、LLMRouter 降级集成、33 新测试（284 total） |
| 20260418 | V0.2-3 Chat Mode 增强完成：SessionManager、AutonomousController、上下文截断、25 新测试（309 total） |
| 20260418 | V0.2-4 Builder 上下文窗口优化完成：TokenCounter、summary 压缩、21 新测试（330 total） |
| 20260418 | V0.2-5 Adaptive Execution 完成：AdaptiveTrigger、Replanner、16 新测试（346 total） |
| 20260418 | **v0.2 全部任务完成**：Cost Tracking + Provider Fallback + Chat Mode + Context Window + Adaptive Execution |
| 20260418 | v0.3 规划完成：Phase Execution Pipeline（PE-1~PE-5）+ Skill Management（S1~S5）纳入活跃 Backlog |
| 20260418 | v0.3 Chat Mode V1.1/V1.2 增强纳入活跃 Backlog：消息持久化 + Autonomous 接真实流水线 + /skill 执行 + /run + /phase + Phase 切换衔接 |
| 20260418 | v0.3 CLI Chat 友好化规划完成：欢迎屏/自然语言帮助/中文优先/结构化输出/确认卡片/进度可视化，spec + plan 已创建 |
