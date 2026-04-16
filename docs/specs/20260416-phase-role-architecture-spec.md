# Sloth Agent Phase-Role-Architecture 设计规格

> 版本: v1.0.0
> 日期: 2026-04-16
> 参考: Superpowers (14 skills) + gstack (23 skills) = 37 skills

---

## 1. 架构概览

```
┌──────────────────────────────────────────────────────────────┐
│                       SLOTH AGENT 架构                         │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Scenario (场景)                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Phase 1 ──▶ Phase 2 ──▶ Phase 3 ──▶ ...              │  │
│  │   │              │              │                      │  │
│  │   ▼              ▼              ▼                      │  │
│  │ Agent:         Agent:         Agent:                   │  │
│  │  Analyst        Planner        Engineer                │  │
│  │ Skills:        Skills:        Skills:                  │  │
│  │  - A1           - B1           - C1                    │  │
│  │  - A2           - B2           - C2                    │  │
│  │ LLM:           LLM:           LLM:                     │  │
│  │  GLM-4          Claude 3.5     DeepSeek                │  │
│  │ Memory:        Memory:        Memory:                  │  │
│  │  scenario/phase1/  scenario/phase2/  scenario/phase3/  │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  Phase Pre/Post 约束：只有满足约束才能串联成有效 Scenario       │
└──────────────────────────────────────────────────────────────┘
```

### 1.1 Runtime 语义补充

Phase-Role-Architecture 是业务编排层，不是底层执行循环。

系统运行时遵循以下约束：

1. 顶层只有一个 `Runner` 执行循环
2. `current_phase` 与 `current_agent` 只是 `RunState` 的当前所有权指针
3. Phase 切换 = `phase_handoff`，代表控制权转移
4. Skill 调用 = `skill-as-tool`，默认不转移控制权
5. gate failure / approval / resume 仍属于同一个 run，而不是新任务

换言之，Phase 用来定义“谁负责什么”，Runner 用来定义“系统怎么继续跑”。

---

## 2. Phase 定义

### 2.1 Phase 结构

```python
@dataclass
class Phase:
    """工作流阶段"""
    id: str                    # "phase-1", "phase-2"
    name: str                  # "需求分析", "计划制定"
    agent_id: str              # 负责人 Agent ID
    
    # 前置 Phase (或关系)
    pre_phases: list[str]      # 满足任意一个即可进入
    # 后置 Phase (或关系)
    post_phases: list[str]     # 完成后可流向的后置 Phase
    
    # 输入输出
    input_schema: dict         # 需要的输入数据类型
    output_schema: dict        # 产生的输出数据类型
    
    # 技能集合
    skills: list[str]          # 该 Phase 可用技能
    
    # LLM 配置
    llm_config: LLMConfig      # 该 Phase 使用的 LLM
    
    # 验证门控
    gates: list[Gate]          # 通过后才能进入后置 Phase
    
    # 场景
    scenarios: list[str]       # 属于哪些 Scenario
```

### 2.1.1 Phase Ownership Contract

每个 Phase 除了输入输出和技能集合，还必须回答一个运行时问题：

**当前 Phase 是否拥有下一轮执行权？何时把执行权交给后续 Phase？**

因此，Phase 的运行时合同补充如下：

```python
@dataclass
class PhaseOwnershipContract:
    phase_id: str
    owner_agent_id: str
    handoff_on: list[str]          # 哪些条件满足后触发 phase_handoff
    retains_control_for_skills: bool = True
    requires_structured_output: bool = True
```

默认规则：

- Phase 内技能调用不转移控制权
- 只有进入后续 Phase 时才触发 `phase_handoff`
- handoff 必须携带结构化输出合同，不能只传自由文本摘要

### 2.2 完整 Phase 定义

#### Phase 1: 需求分析

| 字段 | 值 |
|------|----|
| id | `phase-1` |
| name | 需求分析 |
| agent_id | `analyst` |
| pre_phases | `[]` (入口) |
| post_phases | `["phase-2"]` |
| input | 需求描述 |
| output | 问题陈述 |
| skills | `brainstorming`, `office-hours`, `design-shotgun`, `design-consultation` |
| llm | GLM-4 |
| gates | `问题陈述已生成` |
| scenarios | `["standard", "requirement-only"]` |

#### Phase 2: 计划制定

| 字段 | 值 |
|------|----|
| id | `phase-2` |
| name | 计划制定 |
| agent_id | `planner` |
| pre_phases | `["phase-1"]` |
| post_phases | `["phase-3"]` |
| input | 问题陈述 |
| output | 可执行计划 (SPEC + PLAN) |
| skills | `writing-plans`, `autoplan`, `plan-ceo-review`, `plan-eng-review`, `plan-design-review`, `plan-devex-review` |
| llm | Claude 3.5 |
| gates | `SPEC 已生成`, `PLAN 已生成` |
| scenarios | `["standard", "requirement-only"]` |

#### Phase 3: 编码实现

| 字段 | 值 |
|------|----|
| id | `phase-3` |
| name | 编码实现 |
| agent_id | `engineer` |
| pre_phases | `["phase-2"]` |
| post_phases | `["phase-4", "phase-5"]` |
| input | 可执行计划 |
| output | 代码 + 测试 |
| skills | `test-driven-development`, `subagent-driven-development`, `using-git-worktrees`, `executing-plans`, `dispatching-parallel-agents` |
| llm | DeepSeek |
| gates | `TDD 循环通过`, `测试覆盖率 >= 80%` |
| scenarios | `["standard", "frontend-only", "backend-only"]` |

#### Phase 4: 调试排错

| 字段 | 值 |
|------|----|
| id | `phase-4` |
| name | 调试排错 |
| agent_id | `debugger` |
| pre_phases | `["phase-3", "phase-4"]` |
| post_phases | `["phase-5"]` |
| input | 错误信息 |
| output | 已修复代码 |
| skills | `systematic-debugging`, `browse`, `investigate`, `freeze`, `guard` |
| llm | Claude 3.5 |
| gates | `测试通过`, `无新错误` |
| scenarios | `["standard", "backend-only", "bug-fix", "debug-only"]` |

#### Phase 5: 代码审查

| 字段 | 值 |
|------|----|
| id | `phase-5` |
| name | 代码审查 |
| agent_id | `reviewer` |
| pre_phases | `["phase-3", "phase-4"]` |
| post_phases | `["phase-6"]` |
| input | 代码 + 测试 |
| output | 审查报告 |
| skills | `requesting-code-review`, `verification-before-completion`, `review`, `codex`, `receiving-code-review` |
| llm | Claude 3.5 |
| gates | `审查通过`, `verification 完成` |
| scenarios | `["standard", "frontend-only", "backend-only", "bug-fix", "review-only"]` |

#### Phase 6: 质量验证

| 字段 | 值 |
|------|----|
| id | `phase-6` |
| name | 质量验证 |
| agent_id | `qa-engineer` |
| pre_phases | `["phase-5"]` |
| post_phases | `["phase-7"]` |
| input | 审查通过的代码 |
| output | 质量验证报告 |
| skills | `qa`, `qa-only`, `cso`, `plan-design-review`, `browse`, `health` |
| llm | Claude 3.5 |
| gates | `QA 通过`, `安全审计通过` |
| scenarios | `["standard", "frontend-only", "backend-only", "review-only"]` |

#### Phase 7: 发布上线

| 字段 | 值 |
|------|----|
| id | `phase-7` |
| name | 发布上线 |
| agent_id | `release-engineer` |
| pre_phases | `["phase-5", "phase-6"]` |
| post_phases | `["phase-8"]` |
| input | 质量验证通过的代码 |
| output | 已发布产物 |
| skills | `finishing-a-development-branch`, `ship`, `land-and-deploy`, `document-release`, `setup-deploy` |
| llm | Claude 3.5 |
| gates | `部署成功`, `CI 通过` |
| scenarios | `["standard", "frontend-only", "backend-only", "bug-fix", "ship-only"]` |

#### Phase 8: 上线监控

| 字段 | 值 |
|------|----|
| id | `phase-8` |
| name | 上线监控 |
| agent_id | `sre` |
| pre_phases | `["phase-7"]` |
| post_phases | `[]` (出口) |
| input | 已发布产物 |
| output | 监控报告 + 日报 |
| skills | `canary`, `benchmark`, `retro`, `learn` |
| llm | MiniMax |
| gates | `监控正常`, `日报已生成` |
| scenarios | `["standard", "ship-only"]` |

---

## 3. Agent 定义

### 3.1 Agent 结构

```python
@dataclass
class Agent:
    """执行 Phase 的 Agent"""
    id: str                    # "analyst", "planner"
    name: str                  # "需求分析师", "计划制定者"
    skills: list[str]          # 技能列表
    llm_config: LLMConfig      # LLM 配置
    description: str           # 角色描述
```

### 3.1.1 Agent 的两种协作方式

在 Phase-Role-Architecture 中，Agent 协作必须区分两种语义：

#### 1. Phase handoff

适用场景：

- 从 `planner` 进入 `engineer`
- 从 `engineer` 进入 `reviewer`
- 从 `reviewer` 进入 `qa-engineer`

语义：

- 控制权转移
- `current_phase` 和 `current_agent` 更新
- 下一个 turn 默认由新 owner 负责

#### 2. Skill-as-tool

适用场景：

- `engineer` 在编码阶段触发 `codex` 做 second opinion
- `debugger` 调用 `investigate` 或 `browse`
- `reviewer` 调用 `verification-before-completion`

语义：

- 当前 phase owner 不变
- 调用结果作为受限能力输出回流到当前 phase
- 不创建新的 phase，不接管下一轮执行权

这一区分是必要的，否则系统会把所有 skill 调用误建模成 agent takeover，导致上下文和控制权混乱。

### 3.2 Agent 列表

| Agent ID | 名称 | 技能 | LLM | 负责 Phase |
|----------|------|------|-----|-----------|
| `analyst` | 需求分析师 | brainstorming, office-hours, design-shotgun, design-consultation | GLM-4 | Phase 1 |
| `planner` | 计划制定者 | writing-plans, autoplan, plan-ceo-review, plan-eng-review | Claude 3.5 | Phase 2 |
| `engineer` | 工程师 | TDD, subagent-driven-development, git-worktrees | DeepSeek | Phase 3 |
| `debugger` | 调试员 | systematic-debugging, browse, investigate, freeze | Claude 3.5 | Phase 4 |
| `reviewer` | 审查员 | requesting-code-review, verification-before-completion, review, codex | Claude 3.5 | Phase 5 |
| `qa-engineer` | QA 工程师 | qa, qa-only, cso, plan-design-review | Claude 3.5 | Phase 6 |
| `release-engineer` | 发布工程师 | finishing-a-development-branch, ship, land-and-deploy | Claude 3.5 | Phase 7 |
| `sre` | SRE | canary, benchmark, retro, learn | MiniMax | Phase 8 |

---

## 4. Skill 定义

### 4.1 Skill 结构

```python
@dataclass
class Skill:
    """技能定义"""
    id: str                    # "brainstorming"
    name: str                  # "Brainstorming"
    source: str                # "superpowers" | "gstack"
    trigger: str               # "auto" | "manual"
    description: str           # 技能描述
    input_schema: dict         # 输入类型
    output_schema: dict        # 输出类型
```

### 4.2 37 个 Skill 总表

#### Superpowers (14 个)

| ID | 名称 | 触发方式 |
|----|------|---------|
| `brainstorming` | Brainstorming | auto+manual |
| `writing-plans` | Writing Plans | auto+manual |
| `test-driven-development` | TDD | auto+manual |
| `subagent-driven-development` | Subagent 驱动开发 | auto+manual |
| `using-git-worktrees` | Git Worktrees | auto+manual |
| `systematic-debugging` | 系统调试 | auto+manual |
| `requesting-code-review` | 代码审查请求 | auto+manual |
| `verification-before-completion` | 完成前验证 | auto+manual |
| `finishing-a-development-branch` | 分支收尾 | auto+manual |
| `receiving-code-review` | 接收审查反馈 | auto+manual |
| `executing-plans` | 执行计划 | auto+manual |
| `dispatching-parallel-agents` | 并行子代理 | auto+manual |
| `writing-skills` | 技能创建 | auto+manual |
| `using-superpowers` | Superpowers 入门 | auto+manual |

#### gstack (23 个)

| ID | 名称 | 触发方式 |
|----|------|---------|
| `office-hours` | YC Office Hours | manual |
| `autoplan` | 自动审查管道 | manual |
| `browse` | 浏览器自动化 | manual |
| `investigate` | 系统调试 | manual |
| `review` | 代码审查 | manual |
| `codex` | Codex 第二意见 | manual |
| `qa` | QA 测试 | manual |
| `qa-only` | QA 报告 | manual |
| `cso` | 安全审计 | manual |
| `plan-ceo-review` | CEO 审查 | manual |
| `plan-eng-review` | 工程审查 | manual |
| `plan-design-review` | 设计审查 | manual |
| `plan-devex-review` | DX 审查 | manual |
| `design-consultation` | 设计咨询 | manual |
| `design-shotgun` | 设计探索 | manual |
| `design-html` | 设计实现 | manual |
| `design-review` | 设计审查 | manual |
| `devex-review` | DX 测试 | manual |
| `ship` | 发布 | manual |
| `land-and-deploy` | 部署 | manual |
| `canary` | Canary 监控 | manual |
| `benchmark` | 性能基准 | manual |
| `retro` | 回顾 | manual |
| `learn` | 学习管理 | manual |
| `document-release` | 发布文档 | manual |
| `setup-deploy` | 部署配置 | manual |

---

## 5. Scenario 定义

### 5.1 Scenario 结构

```python
@dataclass
class Scenario:
    """场景定义"""
    id: str                    # "standard", "frontend-only"
    name: str                  # "标准开发", "前端开发"
    phases: list[str]          # Phase 序列
    description: str           # 场景描述
```

### 5.2 Scenario 列表

| ID | 名称 | Phase 序列 | 用途 |
|----|------|-----------|------|
| `standard` | 标准开发 | 1→2→3→4→5→6→7→8 | 端到端全流程 |
| `frontend-only` | 前端开发 | 3→5→6→7 | 只做前端 |
| `backend-only` | 后端开发 | 3→4→5→6→7 | 后端 + 调试 |
| `requirement-only` | 需求梳理 | 1→2 | 只做分析和计划 |
| `ship-only` | 纯发布 | 7→8 | 发布 + 监控 |
| `bug-fix` | 快速修复 | 4→5→7 | 调试→审查→发布 |
| `review-only` | 代码审查 | 5→6 | 审查 + 质量验证 |
| `debug-only` | Bug 排查 | 4 | 只调试 |

### 5.3 Scenario 有效性验证

```python
class ScenarioValidator:
    """验证 Scenario 是否有效"""
    
    def validate(self, scenario: Scenario) -> tuple[bool, list[str]]:
        """
        验证：
        1. 每个 Phase 的前置条件是否满足
        2. Phase 序列是否连贯
        3. 输入输出类型是否匹配
        """
        errors = []
        
        # 检查入口 Phase
        entry = scenario.phases[0]
        if self.phases[entry].pre_phases:
            errors.append(f"入口 Phase {entry} 不能有前置")
        
        # 检查连续性
        for i, phase_id in enumerate(scenario.phases[:-1]):
            phase = self.phases[phase_id]
            next_phase_id = scenario.phases[i + 1]
            if next_phase_id not in phase.post_phases:
                errors.append(f"{phase_id} 不能流向 {next_phase_id}")
        
        # 检查输入输出匹配
        for i, phase_id in enumerate(scenario.phases[:-1]):
            current = self.phases[phase_id]
            next_phase = self.phases[scenario.phases[i + 1]]
            if current.output_schema != next_phase.input_schema:
                errors.append(f"{phase_id} 的输出与 {scenario.phases[i+1]} 的输入不匹配")
        
        return len(errors) == 0, errors
```

### 5.4 Structured Handoff Contract

Scenario 验证不能只检查 schema 名字相等，还必须检查 phase 交接合同是否完整。

```python
@dataclass
class PhaseHandoffContract:
    from_phase: str
    to_phase: str
    decisions: list[str]            # 本 phase 做出的关键决策
    artifacts: list[str]            # 产物引用（文件、报告、diff、测试结果）
    open_questions: list[str]       # 留给后续 phase 的未决问题
    gate_snapshot: dict             # 当前 gate 通过/失败快照
    next_phase_payload: dict        # 下一 phase 必需结构化输入
```

最低要求：

- `planner -> engineer` 必须交付可执行计划、约束、开放问题
- `engineer -> reviewer` 必须交付代码变更、测试结果、已知风险
- `reviewer -> qa-engineer` 必须交付阻塞问题状态、验证建议、审查结论
- `release-engineer -> sre` 必须交付部署产物、版本标识、回滚信息、smoke 结果

这条规则直接替代“自由文本摘要即可”的弱交接方式。

### 5.5 Runtime State 映射

Phase-Role-Architecture 在运行时映射到统一 `RunState`：

```python
@dataclass
class PhaseRuntimeView:
    scenario_id: str
    current_phase: str
    current_agent: str
    completed_phases: list[str]
    pending_phases: list[str]
    latest_handoff: PhaseHandoffContract | None
```

它不是独立状态源，而是 `RunState` 的一个投影视图。系统真相源仍然是 runtime kernel 维护的 `RunState`。

---

## 6. Memory 设计

### 6.1 Memory 结构

```
memory/
├── scenarios/
│   ├── standard/
│   │   ├── phase-1/
│   │   │   ├── input.json
│   │   │   ├── output.json
│   │   │   └── artifacts/
│   │   ├── phase-2/
│   │   │   ├── input.json
│   │   │   ├── output.json
│   │   │   └── artifacts/
│   │   └── ...
│   ├── frontend-only/
│   │   └── ...
│   └── ...
└── global/
    └── skills-evolution/
```

### 6.2 Memory 分类

| 类型 | 路径 | 说明 |
|------|------|------|
| Phase Input | `memory/{scenario}/{phase}/input.json` | Phase 的输入数据 |
| Phase Output | `memory/{scenario}/{phase}/output.json` | Phase 的输出数据 |
| Phase Artifacts | `memory/{scenario}/{phase}/artifacts/` | Phase 产生的文件 |
| Skill Evolution | `memory/global/skills-evolution/` | 技能进化记录 |
| Scenario Report | `memory/{scenario}/report.md` | 场景执行报告 |

---

## 7. 执行引擎

### 7.1 执行流程

```python
class WorkflowEngine:
    """工作流引擎"""
    
    def execute(self, scenario_id: str, input_data: dict) -> ScenarioResult:
        """执行 Scenario"""
        
        scenario = self.scenarios[scenario_id]
        memory = MemoryStore(scenario_id)
        
        for phase_id in scenario.phases:
            phase = self.phases[phase_id]
            agent = self.agents[phase.agent_id]
            
            # 1. 加载输入
            input_data = memory.get_phase_input(phase_id)
            
            # 2. 执行 Phase
            result = agent.execute(phase, input_data)
            
            # 3. 验证门控
            for gate in phase.gates:
                if not gate.check(result):
                    self.handle_gate_failure(phase_id, gate, result)
                    break
            
            # 4. 存储输出
            memory.set_phase_output(phase_id, result)
            
            # 5. 记录日志
            self.log_phase_completion(phase_id, result)
        
        return ScenarioResult(scenario_id, memory)
```

### 7.1.1 与统一 Runner 的关系

上面的 `WorkflowEngine` 负责场景编排，但不应直接拥有底层执行循环。优化后的职责边界应为：

- `WorkflowEngine` 选择 Scenario、决定入口 Phase、维护业务级 phase 顺序
- `Runner` 执行单个 run loop，负责 tool call、handoff、retry、resume、interruptions
- `WorkflowEngine` 通过 `Runner.run(state)` 推进 phase，而不是直接调用 `agent.execute(...)`

推荐的调用关系：

```python
class WorkflowEngine:
    def execute(self, scenario_id: str, input_data: dict) -> ScenarioResult:
        state = self.run_state_store.create_from_scenario(scenario_id, input_data)

        while not state.is_finished:
            result = self.runner.run(state)
            state = result.state

            if state.pending_interruptions:
                return ScenarioResult.paused(state)

        return ScenarioResult.completed(state)
```

### 7.1.2 Gate failure 不再视为普通异常

在 Phase-Role-Architecture 中，gate failure 必须直接映射到 runtime `NextStep`：

- gate pass -> `phase_handoff` 或 `final_output`
- gate fail + 可微调 -> `retry_same`
- gate fail + 需换方案 -> `retry_different`
- gate fail + 计划失真 -> `replan`
- gate fail + 无法恢复 -> `abort`

这样，Phase 语义就能与 runtime 状态机对齐，而不是停留在文档级别的流程图。

### 7.2 Gate 验证

```python
@dataclass
class Gate:
    """验证门控"""
    name: str
    check_fn: Callable[[dict], bool]
    description: str

# 示例门控
GATES = {
    "TDD 循环通过": Gate(
        name="TDD 循环通过",
        check_fn=lambda r: r.get("tests_passed", False),
        description="所有测试必须通过"
    ),
    "测试覆盖率 >= 80%": Gate(
        name="测试覆盖率 >= 80%",
        check_fn=lambda r: r.get("coverage", 0) >= 80,
        description="测试覆盖率必须 >= 80%"
    ),
    "审查通过": Gate(
        name="审查通过",
        check_fn=lambda r: r.get("review_passed", False),
        description="代码审查必须通过"
    ),
}
```

---

## 8. 配置文件

### 8.1 Phase 配置

```yaml
# configs/phases.yaml
phases:
  phase-1:
    name: 需求分析
    agent: analyst
    pre: []
    post: [phase-2]
    input: requirements
    output: problem_statement
    skills: [brainstorming, office-hours, design-shotgun, design-consultation]
    llm: glm-4
    gates: [问题陈述已生成]

  phase-2:
    name: 计划制定
    agent: planner
    pre: [phase-1]
    post: [phase-3]
    input: problem_statement
    output: executable_plan
    skills: [writing-plans, autoplan, plan-ceo-review, plan-eng-review]
    llm: claude-3-5-sonnet
    gates: [SPEC 已生成, PLAN 已生成]
```

### 8.2 Agent 配置

```yaml
# configs/agents.yaml
agents:
  analyst:
    name: 需求分析师
    llm: glm-4
    skills:
      - brainstorming
      - office-hours
      - design-shotgun
      - design-consultation

  planner:
    name: 计划制定者
    llm: claude-3-5-sonnet
    skills:
      - writing-plans
      - autoplan
      - plan-ceo-review
      - plan-eng-review
```

### 8.3 Scenario 配置

```yaml
# configs/scenarios.yaml
scenarios:
  standard:
    name: 标准开发
    phases: [phase-1, phase-2, phase-3, phase-4, phase-5, phase-6, phase-7, phase-8]

  frontend-only:
    name: 前端开发
    phases: [phase-3, phase-5, phase-6, phase-7]

  requirement-only:
    name: 需求梳理
    phases: [phase-1, phase-2]
```

---

## 9. 实现任务分解

### 任务 1: Phase 定义 (P0)

```
- [ ] 创建 Phase 数据模型
- [ ] 定义 8 个 Phase
- [ ] 实现 Phase 验证器
- [ ] 实现 Pre/Post 约束检查
- [ ] 单元测试
```

### 任务 2: Agent 定义 (P0)

```
- [ ] 创建 Agent 数据模型
- [ ] 定义 8 个 Agent
- [ ] 实现 Agent-Skill 映射
- [ ] 实现 Agent-LLM 路由
- [ ] 单元测试
```

### 任务 3: Skill 注册 (P1)

```
- [ ] 创建 Skill 数据模型
- [ ] 注册 37 个 Skill
- [ ] 实现 Skill 触发机制 (auto/manual)
- [ ] 单元测试
```

### 任务 4: Scenario 定义 (P0)

```
- [ ] 创建 Scenario 数据模型
- [ ] 定义 8 个 Scenario
- [ ] 实现 Scenario 验证器
- [ ] 实现 Scenario 执行器
- [ ] 单元测试
```

### 任务 5: Memory 系统 (P1)

```
- [ ] 实现 Scenario → Phase → Memory 结构
- [ ] 实现 Phase Input/Output 存储
- [ ] 实现 Artifacts 存储
- [ ] 单元测试
```

### 任务 6: Workflow Engine (P0)

```
- [ ] 实现 Phase 执行器
- [ ] 实现 Gate 验证系统
- [ ] 实现失败处理机制
- [ ] 实现日志记录
- [ ] 单元测试
```

### 任务 7: Gate 验证 (P1)

```
- [ ] 定义所有 Gate
- [ ] 实现 TDD Gate
- [ ] 实现覆盖率 Gate
- [ ] 实现审查 Gate
- [ ] 实现部署 Gate
- [ ] 单元测试
```

### 任务 8: 配置系统 (P2)

```
- [ ] 实现 YAML 配置加载
- [ ] 实现配置验证
- [ ] 实现热更新
- [ ] 单元测试
```

---

## 10. 验收标准

### 10.1 Phase 系统

- [ ] 8 个 Phase 定义完整
- [ ] Pre/Post 约束正确
- [ ] 输入输出类型匹配

### 10.2 Agent 系统

- [ ] 8 个 Agent 定义完整
- [ ] Skill 映射正确
- [ ] LLM 路由正确

### 10.3 Scenario 系统

- [ ] 8 个 Scenario 定义完整
- [ ] Scenario 验证器正确
- [ ] 非法 Scenario 被拒绝

### 10.4 Memory 系统

- [ ] 按 Scenario → Phase 分类
- [ ] Input/Output 正确存储
- [ ] Artifacts 正确存储

---

*规范版本: v1.0.0*
*创建日期: 2026-04-16*
