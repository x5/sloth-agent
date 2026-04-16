# Spec → Plan → TODO → Execute 执行流程规范

> 版本: v1.1.0
> 日期: 2026-04-17
> 状态: Canonical — 所有 v1.0+ 任务必须遵守此流程

---

## 0. 核心原则

`TODO.md` 是 implementation plan 的执行视图，不是独立计划源。
每一项任务在进入代码实现前，必须先经过 **Spec → Plan → TODO → Execute** 四阶段门控。

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  1. Spec    │───▶│  2. Plan    │───▶│  3. Todo    │───▶│  4. Execute │
│  需求与方案  │    │  实现计划    │    │  任务记录    │    │  TDD 执行   │
│  docs/specs │    │  docs/plans │    │  TODO.md    │    │  代码+测试   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

**强制约束：**
1. **先 Spec，后 Plan** — spec 未确认前，禁止写 plan 或代码
2. **Plan 必须带优先级** — 任务需带 P0 / P1 / P2 或明确排序
3. **TODO 与 Plan 一一对应** — TODO 每项必须能追溯到 plan 中唯一任务
4. **TODO 默认只记录高优先级任务** — 不是每个 plan 任务都进 TODO
5. **执行只看 TODO 最高优先级项** — 从 TODO 选任务，回 plan 看详情
6. **未建映射不得执行** — plan 与 TODO 未建立映射前，先补文档

---

## 1. 模块归属

所有功能模块必须在 `docs/specs/00000000-00-architecture-overview.md` §4.1 模块总览表中注册，拥有唯一编号（01-99）。

### 1.1 模块编号与 Spec 文件命名

| 元素 | 格式 | 示例 |
|------|------|------|
| 模块编号 | 01-99 | `01`, `02`, `06`, `16`, `18` |
| Spec 文件名 | `日期-编号-描述-spec.md` | `20260416-01-phase-role-architecture-spec.md` |
| Plan 文件名 | `日期-编号-描述-implementation-plan.md` | `20260417-v10-runtime-kernel-implementation-plan.md` |
| 文件位置 | `docs/specs/` 和 `docs/plans/` | — |

> 注意：v10 相关 plan 文件名中的 `v10` 替代了编号，因为它们对应多个模块的 v1.0 实现，编号不足以表达版本语义。

### 1.2 跨模块归属规则

**谁驱动谁负责**（谁驱动谁拥有）：
- 若某个功能/规范被识别为跨多个模块，归入 **驱动该功能的模块**
- 示例：工作流步骤、调试流程、质量门控 → 归 Module 01（Phase-Role Architecture），因为它是流程定义模块
- 示例：工具定义、权限 → 归 Module 02（Tools），因为它是工具定义层
- 示例：Skill 进化 → 归 Module 06（Skill Management）
- 示例：全局安装、多项目 → 归 Module 18（Installation）
- 示例：Watchdog 心跳、Git Hooks → 归 Module 16（Daemon & Health）

跨模块内容不再独立成文件，直接合并到属主模块的 spec 中。

---

## 2. 阶段定义

### 阶段 1: Spec 确认

对每个 TODO task，在 `docs/specs/` 中寻找对应功能模块的 spec 文件。

**判断规则：**
1. 从 `00000000-00-architecture-overview.md` 的 §4.1 模块总览表中查找该 task 所属的模块及编号
2. 检查 `docs/specs/` 下是否存在该模块的 spec 文件（文件名模式：`YYYYMMDD-编号-描述-spec.md`）
3. 若不存在 → 创建该模块的 spec 文件，先在架构总览中注册模块编号，再编写 spec
4. 若已存在 → 确认 spec 内容覆盖当前 task 的范围，必要时补充

**Spec 文件必须包含：**
- 模块职责与边界
- 核心数据结构（Pydantic model / dataclass）
- 对外接口（函数签名、输入输出）
- 与其他模块的依赖关系
- 约束条件（安全、性能、兼容性）

### 阶段 2: Plan 确认

对每个已有 spec 的模块，在 `docs/plans/` 中寻找对应的 implementation plan 文件。

**判断规则：**
1. 检查 `docs/plans/` 下是否存在对应模块的 plan 文件（文件名模式：`YYYYMMDD-描述-implementation-plan.md`）
2. 若不存在 → 创建 plan 文件，基于 spec 内容展开为可执行步骤
3. 若已存在 → 确认 plan 覆盖 spec 的所有范围，且与 TODO task 一一映射

**Plan 文件必须包含：**
- 任务分解（每个步骤对应具体文件/函数/类），带优先级
- 依赖关系图（哪些步骤必须先做）
- 测试策略（单元测试、集成测试用例）
- 验收标准（怎么算完成）
- 对应 TODO.md 的任务编号映射

### 阶段 3: TODO 记录

**触发时机：** Plan 审批通过后

**记录规则：**
- TODO.md 不是独立计划文件，而是 implementation plan 的执行视图
- 默认只记录当前高优先级任务（P0 或最高优先级）
- 每个 TODO 项必须能回溯到 plan 中的唯一任务
- TODO 项必须包含以下标识：
  - 优先级标签 `[P0]` / `[P1]` / `[P2]`
  - 对应 Spec 文件路径
  - 对应 Plan 文件路径
  - 对应架构总览中的模块编号

**TODO 条目格式示例：**

```markdown
## v1.0 — 3-Agent 自主流水线

- [ ] **[P0]** Task 1: Runtime Kernel & RunState
  - Plan: `docs/plans/20260417-v10-runtime-kernel-implementation-plan.md`
  - Arch: §3.1.1 Runner / RunState / NextStep
  - Status: 进行中

- [ ] **[P1]** Task 2: Tool Runtime 基础能力
  - Spec: `docs/specs/20260416-02-tools-invocation-spec.md`
  - Plan: `docs/plans/20260417-v10-tool-runtime-implementation-plan.md`
  - Arch: §7.1 Tools System
  - Status: 待开始
```

### 阶段 4: 执行

严格按照 plan 文件中的步骤顺序执行，不跳过、不合并、不重新发明。

**执行规则：**
1. 从 TODO.md 选择当前最高优先级任务
2. 回到对应 plan 文件，查看该任务的详细实现步骤
3. 按 plan 步骤顺序逐项实现
4. 每完成一个步骤验证通过，再进入下一步
5. 不脱离 plan 自行扩展范围
6. 遇到 plan 不清晰的地方，回退修改 plan，而非绕过

**src/ 代码执行前置门控：**

在执行任何涉及 `src/` 代码的 TODO 前，必须满足：

1. **模块已注册** — 该功能模块必须已在架构总览 §4.1 中登记编号
2. **文档就绪** — 该模块必须有对应的 Spec 和 Plan 文档
   - 缺失文档 → 先编写，再编码
   - 未注册 → 先在架构总览中注册

满足上述两项条件后，方可进入代码实现。

---

## 3. 全局约束

| 约束 | 说明 |
|------|------|
| **无 Spec 不 Plan** | 没有 spec 文件的模块不允许创建 plan |
| **无 Plan 不实现** | 没有 plan 文件的模块不允许写代码 |
| **Plan 不跳步** | 实现必须按 plan 步骤顺序执行 |
| **TODO 一一映射** | TODO.md 每项任务必须能追溯到某个 plan 的唯一任务 |
| **Spec 是真相** | 实现与 spec 冲突时，修改 spec 而非绕过 spec |
| **模块必注册** | 所有功能模块必须在架构总览 §4.1 有唯一编号 |
| **代码必备案** | 所有 src/ 代码所属模块必须有 Spec + Plan 文档 |

---

## 4. 文档规范索引

| 模块编号 | 模块名称 | Spec 文件 |
|---------|---------|----------|
| 00 | 总体架构 | `00000000-00-architecture-overview.md` |
| 01 | Phase-Role Architecture + Workflow | `20260416-01-phase-role-architecture-spec.md` |
| 02 | Tools Definition + Invocation | `20260416-02-tools-invocation-spec.md` |
| 03 | Multi-Agent Coordination | `20260416-03-multi-agent-coordination-spec.md` |
| 04 | Memory Management | `20260416-04-memory-management-spec.md` |
| 05 | Session Management | `20260416-05-session-management-spec.md` |
| 06 | Skill Management + Evolution | `20260416-06-skill-management-spec.md` |
| 07 | Chat Mode | `20260416-07-chat-mode-spec.md` |
| 08 | Observability & Logging | `20260416-08-observability-logging-spec.md` |
| 09 | Error Handling & Recovery | `20260416-09-error-handling-recovery-spec.md` |
| 10 | Report Generation | `20260416-10-report-generation-spec.md` |
| 11 | Notification & Integration | `20260416-11-notification-integration-spec.md` |
| 12 | Cost & Budget | `20260416-12-cost-budget-spec.md` |
| 13 | Session Lifecycle | `20260416-13-session-lifecycle-spec.md` |
| 14 | Event System | `20260416-14-event-system-spec.md` |
| 15 | Knowledge Base | `20260416-15-knowledge-base-spec.md` |
| 16 | Daemon & Health | `20260416-16-daemon-health-spec.md` |
| 17 | Sandbox Security | `20260416-17-sandbox-security-spec.md` |
| 18 | Installation + Global Setup | `20260416-18-installation-onboarding-spec.md` |
| 19 | Feishu Integration | `20260416-19-feishu-integration-spec.md` |

---

## 5. 开发工作流

### 5.1 8 阶段流程

| 阶段 | 名称 | 核心技能 | 时段 |
| :--- | :--- | :--- | :--- |
| 一 | 需求分析 | brainstorming | 晚上 |
| 二 | 计划制定 | writing-plans | 晚上 |
| 三 | 编码实现 | TDD, subagent | 白天 |
| 四 | 调试排错 | systematic-debugging | 白天 |
| 五 | 代码审查 | requesting-code-review | 白天 |
| 六 | 质量验证 | QA, security audit | 白天 |
| 七 | 发布上线 | finishing-a-branch | 白天 |
| 八 | 上线监控 | canary monitoring | 白天 |

### 5.2 质量门槛

| 指标 | 门槛 |
|------|------|
| 测试覆盖率 | ≥ 80% |
| Lint 检查 | 0 errors |
| Type 检查 | 0 errors |
| 测试通过率 | 100% |

---

*版本: v1.1.0 | 创建: 2026-04-17 | 更新: 2026-04-17*
