# Sloth Agent 工作流与流程规范

> 版本: v0.2.0
> 日期: 2026-04-15
> 参考: Superpowers Framework (github.com/obra/superpowers), OpenClaw, Hermes Agent

---

## 0. 开发流程规范：Spec → Plan → Todo → Execute

> **核心原则：先想清楚，再动手。不写 spec 不写 plan 不写代码。**
> **强制规则：Spec 必须先确认，Plan 必须后确认，TODO 必须与 Plan 一一对应，执行时只能从 TODO 中选择最高优先级任务。**

### 0.1 三步流程

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  1. Spec    │───▶│  2. Plan    │───▶│  3. Todo    │───▶│  4. Execute │
│  需求与方案  │    │  实现计划    │    │  任务记录    │    │  TDD 执行   │
│  docs/specs │    │  docs/plans │    │  TODO.md    │    │  代码+测试   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

| 步骤 | 文件位置 | 内容 | 谁写 | 审批 |
|------|---------|------|------|------|
| 1. Spec | `docs/specs/YYYYMMDD-feature-spec.md` | 需求分析、架构设计、模块定义、接口约定 | Agent 起草，Human 确认 | Human 审批 |
| 2. Plan | `docs/plans/YYYYMMDD-feature-implementation-plan.md` | 任务拆解、优先级、文件路径、测试用例、验证命令 | Agent 基于 Spec 生成 | Human 审批 |
| 3. Todo | `TODO.md` | 来自 Plan 的高优先级任务清单，逐项映射 | Agent 自动记录 | — |
| 4. Execute | 代码+测试 | 仅按 TODO 当前最高优先级任务执行 | Agent | 自动验证 |

### 0.1 强制约束

1. **先 Spec，后 Plan**：任何功能开发、需求开发、架构变更，都必须先有 spec；spec 未确认前，禁止写 implementation plan 或开始实现。
2. **Plan 必须带优先级**：implementation plan 中的任务必须带明确优先级（至少 P0 / P1 / P2，或等价排序）。
3. **TODO 与 Plan 一一对应**：`TODO.md` 中每一项都必须能映射到 implementation plan 中的某一项任务，不能凭空新增执行项。
4. **TODO 默认只记录高优先级任务**：若无特别说明，`TODO.md` 只提升和维护 implementation plan 中当前高优先级任务。
5. **执行只看 TODO 最高优先级项**：开始实现时，必须先从 `TODO.md` 选择当前最高优先级任务，再回到对应 implementation plan 查看该任务的详细执行要求。
6. **未建映射不得执行**：如果 plan 与 `TODO.md` 尚未建立一一对应关系，必须先补文档映射，再开始编码。

### 0.2 Spec 规格

**包含内容：**
- 需求描述（要解决什么问题）
- 架构设计（模块关系、数据流、接口定义）
- 不写具体代码，只写"做什么"和"为什么"

**触发时机：** 用户提出新功能需求时

**审批：** 用户确认 spec 后，才能进入下一步；未确认前不得进入 implementation plan

### 0.3 Plan 计划

**包含内容：**
- 任务拆解（每个任务 2-5 分钟）
- 任务优先级（P0 / P1 / P2 或明确顺序）
- 具体文件路径、代码片段
- 测试用例设计
- 验证命令
- 遵循 TDD、DRY、YAGNI

**触发时机：** Spec 审批通过后

**审批：** 用户确认 plan 后，才能更新 `TODO.md` 并开始执行

**强制要求：**
- implementation plan 中每个可执行任务必须具备唯一任务名或编号
- 这些任务名/编号必须被 `TODO.md` 引用，用于建立一一对应关系

### 0.4 Todo 记录

**触发时机：** Plan 审批通过后

**内容：**
- 将 implementation plan 中的任务同步到 `TODO.md`
- 默认只记录当前高优先级任务
- 每个 TODO 项必须能回溯到 plan 中的唯一任务
- 标注依赖关系和优先级

**记录规则：**
- `TODO.md` 不是独立计划文件，而是 implementation plan 的执行视图
- 若 plan 优先级发生变化，必须先更新 plan，再同步更新 `TODO.md`
- 若 TODO 项无法对应到 plan，则该项无效，不得执行

### 0.5 适用范围

- 新功能开发
- 架构变更
- 复杂 bug 修复
- 需求重构或多步骤增强

**不适用于：**
- 单行修复（typo、格式）
- 文档补充（已有结构的 README 更新）

### 0.6 Execute 执行选择规则

开始执行任何任务前，按以下顺序检查：

1. 是否已有已确认 spec
2. 是否已有已确认 implementation plan
3. `TODO.md` 是否已与 plan 建立一一对应
4. 当前准备执行的是否为 `TODO.md` 中最高优先级任务
5. 是否已回看该任务在 implementation plan 中的详细说明

只要以上任一项不满足，就先补文档，不进入代码实现。

---

## 1. 概述

Sloth Agent 采用 Superpowers 框架的严谨流程思想，确保每一步执行都有严格的规范和验证。

### 1.1 核心原则（继承自 Superpowers）

| 原则 | 说明 | 应用 |
|------|------|------|
| **TDD** | 测试先行 | 写代码前必须先写测试 |
| **Systematic over ad-hoc** | 系统化优于随机 | 按流程执行，不走捷径 |
| **Complexity reduction** | 简洁为主 | YAGNI，不过度设计 |
| **Evidence over claims** | 证据优于声明 | 必须实际验证，不凭感觉 |

### 1.2 8 阶段强制流程

**Sloth Agent 采用 37 技能路由表（Superpowers 14 + gstack 23 = 37），分 8 个阶段：**

| 阶段 | 阶段名称 | Superpowers | gstack | 时段 |
| :--- | :--- | :--- | :--- | :--- |
| 阶段一 | 需求分析 | brainstorming | /office-hours | 晚上 |
| 阶段二 | 计划制定 | writing-plans | /autoplan | 晚上 |
| 阶段三 | 编码实现 | TDD, subagent, git-worktrees | | 白天 |
| 阶段四 | 调试排错 | systematic-debugging | /browse, /investigate | 白天 |
| 阶段五 | 代码审查 | requesting-code-review | /review, /codex | 白天 |
| 阶段六 | 质量验证 | | /qa, /cso, /plan-design-review | 白天 |
| 阶段七 | 发布上线 | finishing-a-development-branch | /ship, /land-and-deploy | 白天 |
| 阶段八 | 上线监控 | | /canary | 白天 |

**昼夜分工：**
- **晚上 (22:00)**：阶段一 → 阶段二，生成次日 SPEC + PLAN
- **白天 (09:00-22:00)**：阶段三 → 阶段八，自主执行编码到发布全流程

---

## 2. 详细流程定义

### 2.1 Step 1: Brainstorming（构思）

**触发时机**: 收到新任务或新项目规格时

**流程**:
```
1. 探索项目上下文（查看文件、文档、git历史）
2. 通过提问理解需求（一次只问一个问题）
3. 提出 2-3 个方案并分析权衡
4. 分段呈现设计方案（每段 200-300 字）
5. 用户审批后写入设计文档
6. 自我检查：占位符、矛盾、歧义
```

**硬性规则 (HARD-GATE)**:
> **在用户批准设计之前，禁止写任何代码、架子代码或实现动作**

**设计文档命名**:
```
docs/specs/YYYYMMDD-feature-description-design-spec.md
```

**输出**:
- 设计文档（审批后）
- 明确的问题和方案

---

### 2.2 Step 2: Writing Plans（写计划）

**触发时机**: 设计文档审批通过后

**流程**:
```
1. 将工作分解为 2-5 分钟的小任务
2. 每个任务包含：
   - 具体要修改的文件路径
   - 需要写的测试
   - 需要检查的文档
   - 验证步骤
3. 遵循 DRY, YAGNI, TDD 原则
4. 频繁提交（每任务一提交）
```

**计划文档命名**:
```
docs/plans/YYYYMMDD-feature-implementation-plan.md
```

**必须包含的头部**:
```markdown
# [功能名称] 实现计划

**目标**: [一句话描述]
**架构**: [2-3 句话]
**技术栈**: [关键技术]
```

**自我检查清单**:
- [ ] Spec 覆盖验证
- [ ] 无占位符扫描（无 "TBD"、"TODO"、未完成细节）
- [ ] 所有任务类型一致性

---

### 2.3 Step 3: Implementing（执行）

**触发时机**: 计划审批通过后

**流程**:
```
每个任务执行：
1. 编写失败的测试
2. 运行测试确认失败
3. 编写最小实现代码
4. 运行测试确认通过
5. 提交
```

**TDD 强制规则 (The Iron Law)**:
> **没有失败的测试，就不能写任何生产代码**

---

### 2.4 Step 4: Verifying（验证）

**触发时机**: 每个任务完成后

**4 步验证门控**:
```
1. Identify   - 确定什么命令能证明你的声明
2. Run       - 完全重新运行
3. Read      - 检查完整输出和退出码
4. Verify    - 如果失败：说明实际状态
               如果成功：说明状态并附上证据
```

**验证清单**:
- [ ] 测试：完整测试输出显示 0 失败
- [ ] 构建：退出码为 0
- [ ] Bug修复：原始症状测试通过
- [ ] 回归测试：红-绿循环验证

**红灯警告 - 立即停止**:
- 使用 "应该"、"可能"、"似乎" 等词
- 在验证前表达满足感（"完成了！"）
- 没有验证就 commit/push/PR
- 依赖部分验证或 Agent 成功报告

---

### 2.5 Step 5: Requesting Code Review（代码审查）

**触发时机**: 验证通过后

**审查要点**:
```
1. Spec 合规性检查（首先）
   - 是否按 spec 实现？
   - 是否有遗漏的功能？

2. 代码质量检查（其次）
   - 代码风格
   - 安全性
   - 性能
```

**审查报告格式**:
```markdown
## 代码审查报告

### Spec 合规性
- [ ] 符合项
- [ ] 不符合项（按严重程度）

### 严重程度
- **Critical**: 必须修复
- **Major**: 应该修复
- **Minor**: 可以考虑
```

---

### 2.6 Step 6: Finishing Development（完成开发）

**触发时机**: 代码审查通过后

**流程**:
```
1. 验证所有测试通过
2. 运行 lint/format
3. 展示 merge/PR 选项
4. 执行最终合并决策
```

---

## 3. 系统化调试流程

### 3.1 何时触发

当执行中遇到错误或 bug 时，切换到此流程。

### 3.2 四阶段调试法

```
┌─────────────────────────────────────────────────────────────┐
│  Phase 1: Root Cause Investigation (根因调查)               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  - 仔细阅读错误信息                                          │
│  - 复现问题（确保一致）                                      │
│  - 检查最近的变更                                            │
│  - 收集跨组件边界的证据                                      │
│  - 沿调用栈回溯数据流                                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 2: Pattern Analysis (模式分析)                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  - 找到工作的示例                                            │
│  - 完全对比参考（不能略读）                                  │
│  - 识别所有差异                                              │
│  - 理解依赖关系                                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 3: Hypothesis and Testing (假设与测试)               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  - 形成单一具体的理论："我认为是 X 导致，因为 Y"             │
│  - 用最小的可能变更测试                                      │
│  - 验证后再继续                                              │
│  - 如果假设失败，形成新假设（不要叠加修复）                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 4: Implementation (实现)                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  - 首先创建失败的测试用例                                    │
│  - 实现一个针对根因的修复                                    │
│  - 验证修复有效                                              │
│  - 如果 3 个或更多修复都失败了 → 停止并质疑架构             │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 核心规则

> **没有根因调查，就不要修复（NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST）**

---

## 4. 文档命名规范（与 Superpowers 一致）

```
docs/
├── specs/           # 设计规格
│   └── YYYYMMDD-feature-design-spec.md
├── plans/          # 实现计划
│   └── YYYYMMDD-feature-implementation-plan.md
└── reports/        # 工作报告
    └── YYYYMMDD-daily-report.md
```

---

## 5. 代码结构要求

### 5.1 每个任务必须包含

| 元素 | 说明 |
|------|------|
| 测试文件 | `tests/test_xxx.py` |
| 实现文件 | `src/xxx.py` |
| 验证命令 | `pytest`, `ruff`, `mypy` |
| 提交信息 | 符合 Conventional Commits |

### 5.2 提交规范

```
<type>(<scope>): <subject>

feat: 添加新功能
fix: 修复 bug
docs: 文档变更
style: 代码格式
refactor: 重构
test: 测试
chore: 杂项
```

---

## 6. 质量门槛

| 指标 | 门槛 |
|------|------|
| 测试覆盖率 | ≥ 80% |
| Lint 检查 | 0 errors |
| Type 检查 | 0 errors |
| 测试通过率 | 100% |

---

## 7. 与 Superpowers 的差异

| 方面 | Superpowers | Sloth Agent |
|------|------------|-------------|
| 子 Agent | 支持多子 Agent | 单 Agent 优先 |
| Git Worktree | 必须使用 | 可选（按需） |
| 语言 | 多语言 | Rust + TypeScript 优先 |
| 执行时机 | 实时对话 | 日循环自动化 |
| 审批 | 每次交互审批 | 计划级审批 |

---

## 8. 参考来源

- [Superpowers Framework](https://github.com/obra/superpowers)
- 核心原则: Test-Driven Development, Systematic over ad-hoc, Complexity reduction, Evidence over claims

---

---

## 7. Skill 自动进化机制

### 7.1 触发机制（4 种）

| 触发类型 | 条件 | 优先级 |
|---------|------|--------|
| **Error-Driven** | 执行出错时 | P0 |
| **Experience-Accumulation** | 连续成功执行 10+ 次后 | P2 |
| **Periodic-Audit** | 每周一 09:00 自动审计 | P1 |
| **Knowledge-Gap** | 发现无对应 Skill 处理的任务类型 | P2 |

### 7.2 进化流程

```
┌─────────────────────────────────────────────────────────────┐
│  SkillEvolutionEngine                                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [触发] ──▶ [诊断] ──▶ [生成/修正] ──▶ [验证] ──▶ [存储]   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 1: 触发诊断 (Diagnosis)                              │
├─────────────────────────────────────────────────────────────┤
│  - Error-Driven: 分析错误类型和上下文                        │
│  - Experience: 统计成功模式，提取可复用流程                  │
│  - Audit: 对比 Skill 库与实际使用率                          │
│  - Gap: 发现新任务类型无对应 Skill                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 2: 生成/修正 (Generation/Revision)                   │
├─────────────────────────────────────────────────────────────┤
│  SkillGenerator:                                            │
│    - 根据错误上下文生成新 Skill                              │
│    - 输出: YAML 格式 Skill 定义                              │
│                                                              │
│  SkillReviser:                                             │
│    - 修正已有 Skill 的错误描述                               │
│    - 扩展 Skill 的适用范围                                  │
│    - 更新过时的示例或命令                                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 3: 验证 (Validation)                                 │
├─────────────────────────────────────────────────────────────┤
│  SkillValidator:                                            │
│    - frontmatter 完整性                                       │
│    - required_sections 存在                                 │
│    - 无占位符 (TBD/TODO/未完成)                              │
│    - 无重复 Skill 定义                                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 4: 存储 (Storage)                                    │
├─────────────────────────────────────────────────────────────┤
│  SkillRepository:                                           │
│    - 保存到 skills/ 目录                                    │
│    - 更新 skills/index.md                                   │
│    - 触发 SkillManager 重新加载                              │
└─────────────────────────────────────────────────────────────┘
```

### 7.3 Skill 结构定义

```yaml
---
name: skill-name
description: One-line description
trigger: error-driven|experience|periodic-audit|knowledge-gap
frequency: high|medium|low
last_revised: YYYYMMDD
version: x.y.z
---

# Trigger Context
- 错误类型:
- 错误消息:

# Resolution
## Steps
1. step 1
2. step 2

## Commands
- command 1
- command 2

## Validation
- 验证命令

# Examples
- example 1
- example 2
```

### 7.4 SkillValidator 验证规则

| 检查项 | 条件 | 不通过则 |
|--------|------|---------|
| frontmatter | 必须包含 name, trigger, version | 拒绝保存 |
| required_sections | 必须有 Trigger Context, Resolution | 拒绝保存 |
| 占位符 | 不能有 TBD/TODO/未完成 | 拒绝保存 |
| 重复检测 | 不能与已有 Skill 描述重复 | 拒绝保存 |

### 7.5 进化记录

每次 Skill 进化生成报告：
```
docs/reports/
└── YYYYMMDD-skill-evolution-report.md
```

---

## 8. 项目级 TODO.md 管理

### 8.1 TODO.md 位置

项目根目录: `TODO.md`

### 8.2 更新机制

| 时机 | 更新内容 | 来源 |
|------|---------|------|
| 每日开始 | 从 SPEC 自动生成当日任务 | `docs/specs/` |
| 每日结束 | 从日报更新完成状态 | `docs/reports/` |
| Plan 审批后 | 追加新任务 | `docs/plans/` |
| Skill 进化后 | 更新相关任务标记 | `docs/reports/` |

### 8.3 TODO.md 格式

```markdown
# Project TODO

> 最后更新: YYYYMMDD

## 活跃任务

- [ ] **[P0]** 任务描述 @owner @YYYYMMDD
- [ ] **[P1]** 任务描述 @owner @YYYYMMDD

## 进行中

- [x] **[P0]** 已完成任务 @owner @YYYYMMDD

## 阻塞

- [ ] **[P0]** 阻塞任务 - 阻塞原因 @owner @YYYYMMDD

## 已完成

- [x] **[P2]** 已完成任务 @owner @YYYYMMDD
```

### 8.4 TODO.md 与工作流集成

```
Night Phase:
  1. 读取 docs/specs/ 下所有未完成 SPEC
  2. 读取 docs/plans/ 下已审批 Plan
  3. 更新 TODO.md 活跃任务区

Day Phase:
  1. 执行任务时更新状态为 [进行中]
  2. 完成任务后移动到已完成区
  3. 遇到阻塞写入阻塞区并说明原因

Report Phase:
  1. 从 TODO.md 提取当日完成情况
  2. 生成工作报告
```

---

## 9. 工作流节点 LLM 分配

### 9.1 节点-LLM 映射策略

| 工作流节点 | 推荐 LLM | 原因 |
|-----------|---------|------|
| Brainstorming | GLM-4 / Qwen | 创意生成能力强 |
| Planning | Claude 3.5 / GPT-4 | 结构化思考强 |
| Implementing | DeepSeek / Claude 3.5 | 代码生成强 |
| Verifying | MiniMax / GLM | 快速推理 |
| Code Review | Claude 3.5 / GPT-4 | 深度分析 |
| Debugging | Claude 3.5 / DeepSeek | 逻辑推理强 |
| Skill Evolution | GPT-4 / Claude 3.5 | 创意与结构平衡 |

### 9.2 配置示例

```yaml
# configs/llm_providers.yaml
llm_providers:
  deepseek:
    model: deepseek-chat
    api_key: ${DEEPSEEK_API_KEY}
    base_url: https://api.deepseek.com

  glm:
    model: glm-4
    api_key: ${GLM_API_KEY}
    base_url: https://open.bigmodel.cn

  claude:
    model: claude-3-5-sonnet
    api_key: ${ANTHROPIC_API_KEY}
    base_url: https://api.anthropic.com

workflow_node_llm:
  brainstorming: glm
  planning: claude
  implementing: deepseek
  verifying: minimax
  code_review: claude
  debugging: claude
  skill_evolution: claude
```

### 9.3 动态 LLM 切换

```python
class LLM Router:
    """根据工作流节点动态选择 LLM"""
    
    def get_llm_for_node(self, node: WorkflowState) -> LLMProvider:
        config = self.config.workflow_node_llm
        llm_name = config.get(node.value, "default")
        return self.providers[llm_name]
    
    def execute_node(self, node: WorkflowState, prompt: str) -> str:
        llm = self.get_llm_for_node(node)
        return llm.complete(prompt)
```

---

## 10. 全局安装与多项目架构

### 10.1 设计理念

Sloth Agent 作为**全局工具**安装，一次安装，所有项目通用（类似 OpenClaw/Hermes Agent）。

### 10.2 目录结构

```
~/.sloth-agent/                  # 全局安装目录（~/.sloth-agent/）
├── src/                        # 框架源码（全局一份）
├── configs/                    # 全局配置
│   ├── agent.yaml              # Agent 配置
│   └── llm_providers.yaml      # LLM 提供商配置
├── skills/                     # 全局 Skills 库（所有项目共享）
├── memory/                     # 全局记忆数据
├── checkpoints/                # 全局断点快照
├── logs/                       # 全局日志
└── run.py                      # 入口脚本

[项目目录]/
├── .sloth/                     # 项目配置（轻量）
│   ├── project.yaml            # 项目名、路径、SPEC/PLAN 目录
│   └── local_skills/          # 项目专属 Skills（可选）
├── docs/                       # 文档（项目内）
│   ├── specs/
│   ├── plans/
│   └── reports/
├── TODO.md                     # 项目任务
└── [项目源代码...]
```

### 10.3 项目初始化（sloth init）

```bash
sloth init --project ~/my-project
```

初始化后创建完整项目结构：

```
~/my-project/
├── .sloth/                     # Sloth Agent 项目配置
│   └── project.yaml
├── docs/                       # 文档（框架生成）
│   ├── specs/                  # 设计规格
│   ├── plans/                  # 实现计划
│   └── reports/                # 工作报告
├── src/                        # 源代码
│   └── (your code)
├── tests/                      # 测试代码
│   └── (your tests)
├── scripts/                    # 辅助脚本（如有）
├── README.md                   # 项目说明
├── LICENSE                     # 许可证（如有）
├── .gitignore                  # Git 忽略规则
├── pyproject.toml              # Python: uv 项目配置
│   # 或 Cargo.toml (Rust)
│   # 或 package.json (Node.js)
│   # 或 go.mod (Go)
└── TODO.md                     # 项目任务清单
```

### 10.4 安装方式

```bash
# 1. 克隆到全局目录
git clone git@github.com:x5/sloth-agent.git ~/.sloth-agent

# 2. 使用 uv 安装（与项目一致）
cd ~/.sloth-agent
uv venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e .

# 3. 添加到 PATH（可选，或使用绝对路径）
echo 'export PATH="$HOME/.sloth-agent:$PATH"' >> ~/.bashrc
```

### 10.4 项目初始化

```bash
# 为项目初始化 Sloth Agent 配置
sloth init --project ~/my-project

# 这会在 ~/my-project/.sloth/ 下创建 project.yaml
```

### 10.5 project.yaml 格式

```yaml
project:
  name: my-project
  path: /home/user/my-project
  docs_dir: docs                    # 文档目录（相对于项目根）
  spec_dir: docs/specs
  plan_dir: docs/plans
  report_dir: docs/reports

skills:
  global: ~/.sloth-agent/skills     # 全局 Skills
  local: .sloth/local_skills        # 项目专属 Skills

workflow:
  night_phase_time: "22:00"
  day_phase_time: "09:00"
  heartbeat_interval: 180          # 3 分钟

llm:
  default_provider: deepseek
  node_mapping:                    # 可选，覆盖全局配置
    brainstorming: glm
    planning: claude
```

### 10.6 使用方式

```bash
# 指定项目运行
sloth run --project ~/my-project --phase night
sloth run --project ~/my-project --phase day

# 查看状态
sloth status --project ~/my-project

# 查看帮助
sloth --help
```

### 10.7 与 OpenClaw/Hermes Agent 对比

| 特性 | OpenClaw | Hermes Agent | Sloth Agent |
|------|----------|--------------|-------------|
| 安装位置 | `~/.openclaw/` | `~/.hermes/` | `~/.sloth-agent/` |
| 安装方式 | `npm install -g` | Shell 脚本 | `git clone` + `uv pip install -e` |
| 项目配置 | `~/.openclaw/openclaw.json` | 无 | `[项目]/.sloth/project.yaml` |
| Skills 位置 | `~/.openclaw/skills/` | `~/.hermes/skills/` | `~/.sloth-agent/skills/` + `[项目]/.sloth/local_skills/` |
| 多项目支持 | 是 | 否 | 是 |

---

*规范版本: v0.2.0*
*创建日期: 2026-04-15*
