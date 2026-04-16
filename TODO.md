# Project TODO

> 最后更新: 20260416
> 对齐规范: `docs/specs/00000000-architecture-overview.md`
> 当前目标: 先落地 v1.0 最小可用产品，再进入 v1.1 / v2.0 扩展
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

### P0: v1.0 自主流水线实现

> Spec: `docs/specs/00000000-architecture-overview.md`
> 范围: 3-Agent 串行流水线（Builder → Reviewer → Deployer）
> 关键约束: 单一 `Runner` 内核 + 结构化交接 + 自动门控 + 文件系统状态

依赖链: `1 → 2 → 3 → 4 → 5 → 6 → 7 → 8`

- [ ] **Task 1: Runtime Kernel & RunState**
  - [ ] 在 `src/sloth_agent/core/` 中引入统一运行时骨架：`Runner`、`RunState`、`NextStep`
  - [ ] 明确 `Product Orchestrator` 与 `Runner` 的边界，避免多套执行循环
  - [ ] 统一 `final_output / tool_call / phase_handoff / retry / interruption / abort` 语义
  - [ ] 补充对应单元测试，覆盖状态推进与恢复入口

- [ ] **Task 2: Tool Runtime 基础能力** ← Task 1
  - [ ] 统一 `ToolRegistry` / `ToolOrchestrator` 接口，纳入 `Runner.resolve()` 分支
  - [ ] 优先落地 v1.0 核心工具：`read`、`write`、`edit`、`run_command`、`glob`、`grep`
  - [ ] 接入 `HallucinationGuard`、路径白名单、命令黑名单
  - [ ] 为工具调用记录审计信息与结构化结果，便于后续 gate / tracing / replay

- [ ] **Task 3: Builder Agent Runtime** ← Task 2
  - [ ] 将 Plan 解析、编码、调试、单元测试收敛到 Builder phase
  - [ ] 实现 `ContextWindowManager`，区分 system、历史、工具结果、输出预留
  - [ ] 接入 Reflection / Stuck Detection / 自动重试入口
  - [ ] 产出结构化 `BuilderOutput`，作为 Builder → Reviewer 的唯一交接物

- [ ] **Task 4: Gate 机制与 Phase Handoff** ← Task 3
  - [ ] 实现 Gate1 / Gate2 / Gate3 的纯规则判断，不依赖 LLM
  - [ ] 固化 `phase_handoff` 与 `skill-as-tool` 的不同语义
  - [ ] 对齐 `BuilderOutput` / `ReviewerOutput` 数据结构
  - [ ] 打通 gate failure → retry / rollback / interrupt 的运行时流转

- [ ] **Task 5: Reviewer Agent Runtime** ← Task 4
  - [ ] 实现 Reviewer phase，要求使用不同于 Builder 的模型路由
  - [ ] 聚焦代码审查、质量验证、安全/性能 blocking issues 识别
  - [ ] 生成结构化 `ReviewerOutput`，支持 Reviewer → Deployer handoff
  - [ ] 补充 reviewer 审查有效性的测试与最小评估用例

- [ ] **Task 6: Deployer Agent Runtime** ← Task 5
  - [ ] 实现部署执行与 smoke test 验证链路
  - [ ] 支持 Gate3 失败后的自动回滚与通知钩子
  - [ ] 明确部署产物、部署日志、验证结果的落盘格式
  - [ ] 补充 end-to-end 部署阶段测试

- [ ] **Task 7: FS Memory / Checkpoint / Skill Loading** ← Task 6
  - [ ] 将运行状态、阶段产物、工具记录、gate 结果统一写入文件系统
  - [ ] 建立 checkpoint 保存/恢复机制，作为回滚与 resume 基础
  - [ ] 打通 `SKILL.md` 加载与按需注入机制
  - [ ] 约束模型可见上下文、运行时上下文、持久化状态三层边界

- [ ] **Task 8: CLI 集成与 v1.0 验证闭环** ← Task 7
  - [ ] 打通 `sloth run` 主路径，输入 Plan 后可跑完整流水线
  - [ ] 配置 v1.0 阶段级模型路由（Builder / Reviewer / Deployer）
  - [ ] 增加最小 eval / smoke 场景，验证成功率、质量门控、自修复链路
  - [ ] 跑通一条真实示例并更新 README / 使用文档

### 其他活跃任务

- [ ] **[P0]** Tools 与运行时内核对齐，禁止游离在 Runner 之外 @agent @20260416
- [ ] **[P0]** 结构化 Agent 交接协议落地（BuilderOutput / ReviewerOutput）@agent @20260416
- [ ] **[P1]** 阶段级模型路由配置（Builder / Reviewer / Deployer）@agent @20260416
- [ ] **[P1]** 文件系统记忆与 checkpoint 统一格式 @agent @20260416

## 近期 Backlog

- [ ] **[P1][v1.1]** Chat Mode 基础（REPL + streaming）@agent @20260416
- [ ] **[P1][v1.1]** 多 Provider fallback / 熔断降级 @agent @20260416
- [ ] **[P1][v1.1]** Cost tracking 基础（定价 + 用量记录）@agent @20260416
- [ ] **[P1][v1.1]** Builder 上下文窗口管理优化 @agent @20260416
- [ ] **[P1][v1.1]** Adaptive Execution（自适应重规划）@agent @20260416

## 远期 Backlog

- [ ] **[P2][v1.2]** 基础 Observability（结构化日志 + Trace ID）@agent @20260416
- [ ] **[P2][v1.2]** Error Recovery（重试 + 基本恢复）@agent @20260416
- [ ] **[P2][v1.2]** Feishu 通知（webhook 推送执行结果）@agent @20260416
- [ ] **[P2][v1.2]** Checkpoint 保存与恢复增强 @agent @20260416
- [ ] **[P2][v2.0]** Phase-Role-Architecture（8 阶段 × 8+1 Agent × 37 技能）实现 @agent @20260416
- [ ] **[P2][v2.0]** Multi-Agent 并行协调 + Worktree 隔离 @agent @20260416
- [ ] **[P2][v2.0]** 事件总线（pub-sub + dead letter queue）@agent @20260416
- [ ] **[P2][v2.0]** 知识库 + 语义检索（SQLite / ChromaDB）@agent @20260416
- [ ] **[P2][v2.0]** Daemon 常驻 + Watchdog @agent @20260416

## 阻塞

- [ ] 当前缺少与 canonical architecture 对齐的 v1.0 implementation plan；在补齐 plan 并完成 TODO 一一映射前，不进入代码实现

## 已完成

- [x] **[P0]** 框架规范文档编写 @agent @20260415
- [x] **[P0]** Document Naming Convention 制定 @agent @20260415
- [x] **[P1]** Workflow Process Spec 定义 @agent @20260415
- [x] **[P1]** Tools Design Spec 定义 @agent @20260415
- [x] **[P0]** Phase-Role-Architecture Spec 编写 @agent @20260416
- [x] **[P0]** Phase-Role-Architecture Plan 编写 @agent @20260416
- [x] **[P0]** Architecture v2 内容并入 canonical overview，旧文档归档 @agent @20260416

---

## 任务标签说明

| 标签 | 说明 |
|------|------|
| `P0` | 最高优先级，当前迭代必须完成 |
| `P1` | 高优先级，当前迭代应该完成 |
| `P2` | 中优先级，当前迭代可以完成 |
| `[v1.1] / [v1.2] / [v2.0]` | 对应 roadmap 版本阶段 |
| `@owner` | 任务负责人（agent/human） |
| `@YYYYMMDD` | 创建或迁移日期 |
| `← Task N` | 依赖前置任务 N |

---

## 更新日志

| 日期 | 更新内容 |
|------|---------|
| 20260415 | 初始版本，创建框架基础任务 |
| 20260416 | 整合 Phase-Role-Architecture 任务链，建立依赖关系 |
| 20260416 | 按 canonical architecture 重排 TODO：v1.0 先做 3-Agent 自主流水线，Phase-Role-Architecture 下沉为 v2.0 远期任务 |