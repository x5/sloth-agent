# Sloth Agent Phase-Role-Architecture 设计规格

> 版本: v2.0.0 (草案)
> 日期: 2026-04-16
> 参考: Superpowers (14 skills) + gstack (23 skills) = 37 skills
> v0.1.0 实现状态: §25 运行时内核定义 (Runner/RunState/NextStep) 已实现
>   - 实现文件: `src/sloth_agent/core/runner.py`, `src/sloth_agent/core/builder.py`
>   - 实现文件: `src/sloth_agent/core/reflector.py`, `src/sloth_agent/core/context_window.py`
>   - 测试覆盖: `tests/core/test_runner.py`, `tests/core/test_builder.py`
>   - 测试覆盖: `tests/core/test_context_window.py`, `tests/core/test_context_boundary.py`

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

## 11. 工作流步骤与钩子

每个 Phase 步骤必须有可执行、可验证的钩子（hooks）保障。

### 11.1 设计原则

| 原则 | 说明 |
|------|------|
| **Evidence over claims** | 每个步骤必须有可验证的证据 |
| **Atomic commits** | 每个微任务单独提交 |
| **TDD Iron Law** | 没有失败测试就不能写生产代码 |
| **Hard Gates** | 关键步骤前必须通过审查 |

### 11.2 步骤 1: Brainstorming（构思）

**目标**: 在写任何代码前，充分理解需求并设计解决方案

| 阶段动作 | 工具/命令 | 产出 |
|---------|----------|------|
| 探索上下文 | `Read`, `Glob`, `Grep` | 项目结构理解 |
| 收集需求 | `WebFetch` (外部参考) | 竞品/文档分析 |
| 记录问题 | `Write` (临时笔记) | 问题清单 |
| 提出方案 | LLM (Claude/GLM) | 2-3 个方案及权衡 |
| 撰写设计 | `Write` | `docs/specs/YYYYMMDD-*-design-spec.md` |
| 自我检查 | `grep -E "TBD\|TODO\|未完成"` | 无占位符验证 |

**Hooks**:
```yaml
pre_brainstorming:
  - check_workspace_exists: 验证工作区存在

post_brainstorming:
  - validate_design_spec: 验证设计文档格式
  - check_no_code_in_design: 确保设计文档无代码
```

### 11.3 步骤 2: Writing Plans（写计划）

**目标**: 将设计分解为 2-5 分钟的微任务

| 阶段动作 | 工具/命令 | 产出 |
|---------|----------|------|
| 分解任务 | LLM (Claude) | 微任务列表 |
| 创建任务 | `TaskCreate` | 任务 ID |
| 验证覆盖 | `grep` + `Read` | Spec 覆盖检查 |
| 扫描占位符 | `grep -E "TBD\|TODO"` | 占位符检查 |
| 撰写计划 | `Write` | `docs/plans/YYYYMMDD-*-implementation-plan.md` |

**Hooks**:
```yaml
pre_planning:
  - design_approved: 设计必须已审批

post_planning:
  - validate_plan_format: 验证计划格式
  - validate_task_breakdown: 验证任务分解粒度
  - update_todo_md: 更新 TODO.md
```

### 11.4 步骤 3: Implementing（执行）

**目标**: TDD 驱动，每个任务遵循 RED-GREEN-REFACTOR

| 阶段动作 | 工具/命令 | 产出 |
|---------|----------|------|
| 编写测试 (RED) | `Write` | `tests/test_xxx.py` |
| 运行测试 | `Bash: pytest` | 测试失败输出 |
| 验证失败原因 | `Read` (测试输出) | 确认失败正确 |
| 写实现 (GREEN) | `Write`/`Edit` | `src/xxx.py` |
| 运行测试 | `Bash: pytest` | 测试通过输出 |
| 重构 (REFACTOR) | `Edit` | 优化代码 |
| Lint 检查 | `Bash: ruff` | 代码风格 |
| Type 检查 | `Bash: mypy` | 类型正确 |
| 提交代码 | `Bash: git commit` | 提交记录 |

**TDD Enforcer 规则**:
```python
THE_IRON_LAW = "没有失败的测试，就不能写任何生产代码"

class TDDEnforcer:
    def enforce_red(self, task):
        """RED: 必须先写失败测试"""
        test_file = self.write_test(task)
        result = run_pytest(test_file)
        if result.passed:
            raise TDDViolationError("测试必须失败!")
        return result

    def enforce_green(self, task):
        """GREEN: 写最小实现"""
        if not self.has_failing_test(task):
            raise TDDViolationError("没有失败测试!")
        impl_file = self.write_implementation(task)
        result = run_pytest(impl_file)
        if not result.passed:
            raise TDDViolationError("实现未能让测试通过!")
        return result
```

**Hooks**:
```yaml
pre_implementing:
  - task_approved: 任务必须已分解并审批
  - test_exists: 验证测试文件存在

post_implementing:
  - all_tests_pass: 所有测试必须通过
  - lint_clean: ruff 0 errors
  - type_clean: mypy 0 errors
  - coverage_threshold: >= 80%
  - git_commit: 自动提交
```

### 11.5 步骤 4: Verifying（验证）

**目标**: 证据优于声明，4 步验证门控

| 阶段动作 | 工具/命令 | 产出 |
|---------|----------|------|
| Identify | 确定验证命令 | 验证命令列表 |
| Run | `Bash` | 完整输出 |
| Read | `Read` | 检查退出码和输出 |
| Verify | 分析结果 | pass/fail |

**验证门控清单**:

```yaml
verify_tests:
  command: "pytest --tb=short -v"
  check:
    - exit_code: 0
    - failures: 0
    - output_contains: "X passed"

verify_build:
  command: "cargo build 2>&1"  # Rust 项目
  check:
    - exit_code: 0

verify_coverage:
  command: "pytest --cov=src --cov-report=term"
  check:
    - coverage_percent: ">= 80"

verify_lint:
  command: "ruff check src/"
  check:
    - exit_code: 0

verify_types:
  command: "mypy src/"
  check:
    - exit_code: 0
```

**Red Flags（立即停止）**:
- 使用 "应该"、"可能"、"似乎" 等词
- 在验证前表达满足感（"完成了！"）
- 没有验证就 commit/push/PR
- 依赖部分验证

### 11.6 步骤 5: Code Review（代码审查）

**目标**: Spec 合规性检查优先于代码质量

| 阶段动作 | 工具/命令 | 产出 |
|---------|----------|------|
| Spec 合规检查 | `Read` + `Grep` | 合规性报告 |
| 代码质量检查 | `Bash: ruff`, `mypy` | 质量报告 |
| 安全性检查 | `Bash: ruff check --select=security` | 安全问题 |
| 性能检查 | `Bash: cargo bench` (Rust) | 性能报告 |
| 生成报告 | `Write` | Review 报告 |

**Review 报告格式**:

```markdown
## 代码审查报告

### Spec 合规性
- [ ] 符合项
- [ ] 不符合项

### 严重程度
- **Critical**: 必须修复
- **Major**: 应该修复
- **Minor**: 可以考虑

### 代码质量
- Lint: X errors
- Type: X errors
- Coverage: X%

### 安全性
- X issues found
```

### 11.7 步骤 6: Finishing（完成开发）

**目标**: 最终验证并提供合并选项

| 阶段动作 | 工具/命令 | 产出 |
|---------|----------|------|
| 最终验证 | `Bash: pytest` | 全部测试通过 |
| Lint/Format | `Bash: ruff format` | 代码格式 |
| 展示选项 | LLM | Merge/PR 选项 |
| 执行合并 | `Bash: git merge` | 合并结果 |

### 11.8 调试工具链

**目标**: 四阶段调试法，系统化根因分析

| 阶段 | 工具 | 产出 |
|------|------|------|
| Root Cause | `Read` (日志), `Bash` (reproduce) | 错误复现 |
| Pattern Analysis | `Grep` (working examples) | 差异分析 |
| Hypothesis | `Bash` (minimal test) | 假设验证 |
| Implementation | `Edit` + `Bash: pytest` | 修复验证 |

### 11.9 工作流自动化脚本

```bash
# run.py (主入口)
python run.py --phase night    # Night: SPEC -> PLAN -> 审批
python run.py --phase day      # Day: 执行 PLAN -> Report
```

### 11.10 工作流调用链

```
Night Phase (22:00):
  1. Read SPECs -> LLM(Planning) -> Write PLAN -> Human Approval -> Update TODO.md
  2. Skill Audit -> Skill Evolution (if needed)

Day Phase (09:00-18:00):
  1. Read TODO.md -> For each P0 task:
     - Brainstorming (if new)
     - Planning (if new)
     - Implementing (TDD cycle)
     - Verifying (4-step gate)
     - Code Review
  2. Update TODO.md
  3. Hourly Heartbeat

Report Phase:
  1. Generate daily report
  2. Update TODO.md completion
  3. Trigger Skill Evolution if errors
```

---

---

## 12. 开发流程规范：Spec → Plan → Todo → Execute（从跨模块规范迁入）

> **核心原则：先想清楚，再动手。不写 spec 不写 plan 不写代码。**
> **强制规则：Spec 必须先确认，Plan 必须后确认，TODO 必须与 Plan 一一对应，执行时只能从 TODO 中选择最高优先级任务。**

### 12.1 三步流程

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

### 12.2 强制约束

1. **先 Spec，后 Plan**：任何功能开发、需求开发、架构变更，都必须先有 spec；spec 未确认前，禁止写 implementation plan 或开始实现。
2. **Plan 必须带优先级**：implementation plan 中的任务必须带明确优先级（至少 P0 / P1 / P2，或等价排序）。
3. **TODO 与 Plan 一一对应**：`TODO.md` 中每一项都必须能映射到 implementation plan 中的某一项任务，不能凭空新增执行项。
4. **TODO 默认只记录高优先级任务**：若无特别说明，`TODO.md` 只提升和维护 implementation plan 中当前高优先级任务。
5. **执行只看 TODO 最高优先级项**：开始实现时，必须先从 `TODO.md` 选择当前最高优先级任务，再回到对应 implementation plan 查看该任务的详细执行要求。
6. **未建映射不得执行**：如果 plan 与 `TODO.md` 尚未建立一一对应关系，必须先补文档映射，再开始编码。

### 12.3 Spec 规格

**包含内容：**
- 需求描述（要解决什么问题）
- 架构设计（模块关系、数据流、接口定义）
- 不写具体代码，只写"做什么"和"为什么"

**触发时机：** 用户提出新功能需求时

**审批：** 用户确认 spec 后，才能进入下一步；未确认前不得进入 implementation plan

### 12.4 Plan 计划

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

### 12.5 Todo 记录

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

### 12.6 适用范围

- 新功能开发
- 架构变更
- 复杂 bug 修复
- 需求重构或多步骤增强

**不适用于：**
- 单行修复（typo、格式）
- 文档补充（已有结构的 README 更新）

### 12.7 Execute 执行选择规则

开始执行任何任务前，按以下顺序检查：

1. 是否已有已确认 spec
2. 是否已有已确认 implementation plan
3. `TODO.md` 是否已与 plan 建立一一对应
4. 当前准备执行的是否为 `TODO.md` 中最高优先级任务
5. 是否已回看该任务在 implementation plan 中的详细说明

只要以上任一项不满足，就先补文档，不进入代码实现。

---

## 13. 详细流程定义（从跨模块规范迁入）

### 13.1 核心原则（继承自 Superpowers）

| 原则 | 说明 | 应用 |
|------|------|------|
| **TDD** | 测试先行 | 写代码前必须先写测试 |
| **Systematic over ad-hoc** | 系统化优于随机 | 按流程执行，不走捷径 |
| **Complexity reduction** | 简洁为主 | YAGNI，不过度设计 |
| **Evidence over claims** | 证据优于声明 | 必须实际验证，不凭感觉 |

### 13.2 8 阶段强制流程

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

### 13.3 Step 1: Brainstorming（构思）

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

### 13.4 Step 2: Writing Plans（写计划）

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

### 13.5 Step 3: Implementing（执行）

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

### 13.6 Step 4: Verifying（验证）

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

### 13.7 Step 5: Requesting Code Review（代码审查）

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

### 13.8 Step 6: Finishing Development（完成开发）

**触发时机**: 代码审查通过后

**流程**:
```
1. 验证所有测试通过
2. 运行 lint/format
3. 展示 merge/PR 选项
4. 执行最终合并决策
```

---

## 14. 系统化调试流程（从跨模块规范迁入）

### 14.1 何时触发

当执行中遇到错误或 bug 时，切换到此流程。

### 14.2 四阶段调试法

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

### 14.3 核心规则

> **没有根因调查，就不要修复（NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST）**

---

## 15. 文档命名规范（从跨模块规范迁入）

```
docs/
├── specs/           # 设计规格
│   └── YYYYMMDD-*-spec.md
├── plans/          # 实现计划
│   └── YYYYMMDD-*-implementation-plan.md
└── reports/        # 工作报告
    └── YYYYMMDD-daily-report.md
```

---

## 16. 代码结构要求（从跨模块规范迁入）

### 16.1 每个任务必须包含

| 元素 | 说明 |
|------|------|
| 测试文件 | `tests/test_xxx.py` |
| 实现文件 | `src/xxx.py` |
| 验证命令 | `pytest`, `ruff`, `mypy` |
| 提交信息 | 符合 Conventional Commits |

### 16.2 提交规范

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

## 17. 质量门槛（从跨模块规范迁入）

| 指标 | 门槛 |
|------|------|
| 测试覆盖率 | ≥ 80% |
| Lint 检查 | 0 errors |
| Type 检查 | 0 errors |
| 测试通过率 | 100% |

---

## 18. 与 Superpowers 的差异（从跨模块规范迁入）

| 方面 | Superpowers | Sloth Agent |
|------|------------|-------------|
| 子 Agent | 支持多子 Agent | 单 Agent 优先 |
| Git Worktree | 必须使用 | 可选（按需） |
| 语言 | 多语言 | Python 优先 |
| 执行时机 | 实时对话 | 日循环自动化 |
| 审批 | 每次交互审批 | 计划级审批 |

---

## 19. TODO.md 管理（从跨模块规范迁入）

### 19.1 TODO.md 位置

项目根目录: `TODO.md`

### 19.2 更新机制

| 时机 | 更新内容 | 来源 |
|------|---------|------|
| 每日开始 | 从 SPEC 自动生成当日任务 | `docs/specs/` |
| 每日结束 | 从日报更新完成状态 | `docs/reports/` |
| Plan 审批后 | 追加新任务 | `docs/plans/` |
| Skill 进化后 | 更新相关任务标记 | `docs/reports/` |

### 19.3 TODO.md 格式

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

### 19.4 TODO.md 与工作流集成

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

## 20. 工作流节点 LLM 分配（从跨模块规范迁入）

### 20.1 节点-LLM 映射策略

| 工作流节点 | 推荐 LLM | 原因 |
|-----------|---------|------|
| Brainstorming | GLM-4 / Qwen | 创意生成能力强 |
| Planning | Claude 3.5 / GPT-4 | 结构化思考强 |
| Implementing | DeepSeek / Claude 3.5 | 代码生成强 |
| Verifying | MiniMax / GLM | 快速推理 |
| Code Review | Claude 3.5 / GPT-4 | 深度分析 |
| Debugging | Claude 3.5 / DeepSeek | 逻辑推理强 |
| Skill Evolution | GPT-4 / Claude 3.5 | 创意与结构平衡 |

### 20.2 配置示例

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

### 20.3 动态 LLM 切换

```python
class LLMRouter:
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

## 21. NextStep 协议

为了让 reflection、gate、approval、phase transition 共用一套语义，运行时统一使用 `NextStep` 协议：

```python
class NextStep(BaseModel):
  type: Literal[
    "final_output",
    "tool_call",
    "phase_handoff",
    "retry_same",
    "retry_different",
    "replan",
    "interruption",
    "abort",
  ]
  output: str | None = None
  request: ToolRequest | None = None
  next_agent: str | None = None
  next_phase: str | None = None
  reason: str | None = None
```

## 22. Builder Agent 上下文管理

### 22.1 ContextWindowManager

Builder Agent 的上下文窗口是 v1.0 最关键的工程约束（单次请求 ~60K tokens），需要精确管理。Token 计数用 tiktoken（或 Provider 自带的 tokenizer），不估算。压缩规则是纯规则（match/case），不调用 LLM，零延迟。窗口管理在每次 LLM 调用前执行，不缓存。

```python
class ContextWindowManager:
    """精确管理 Agent 上下文窗口"""

    def __init__(self, max_tokens: int = 128_000, output_reserve: int = 15_000):
        self.max_tokens = max_tokens
        self.output_reserve = output_reserve
        self.available = max_tokens - output_reserve  # 实际可用 113K

    def build_messages(self, system: str, history: list, tools: list, user_msg: str) -> list:
        budget = self.available

        # 1. System prompt（固定，不可压缩）
        sys_tokens = count_tokens(system)
        budget -= sys_tokens

        # 2. 当前用户消息（固定）
        user_tokens = count_tokens(user_msg)
        budget -= user_tokens

        # 3. 工具结果（按时间倒序，最新的完整保留，旧的压缩）
        tool_messages, budget = self._fit_tool_results(tools, budget)

        # 4. 历史对话（从最新到最旧，填满剩余空间）
        history_messages = self._fit_history(history, budget)

        return [system] + history_messages + tool_messages + [user_msg]

    def _fit_tool_results(self, tools: list, budget: int) -> tuple[list, int]:
        """最新 1 条完整保留，其余压缩为单行摘要"""
        fitted = []
        for i, tool_result in enumerate(reversed(tools)):
            tokens = count_tokens(tool_result)
            if i == 0:  # 最新一条完整保留
                fitted.append(tool_result)
                budget -= tokens
            elif budget > 500:  # 旧结果压缩
                summary = self._compress_tool_result(tool_result)
                fitted.append(summary)
                budget -= count_tokens(summary)
        return fitted, budget

    @staticmethod
    def _compress_tool_result(result: ToolResult) -> str:
        """确定性压缩规则（不用 LLM）"""
        match result.tool_name:
            case "read_file":
                return f"[已读取 {result.path} ({result.line_count}行)]"
            case "run_command":
                exit_code = result.exit_code
                if exit_code == 0:
                    return f"[命令成功: {result.command}]"
                return f"[命令失败(exit={exit_code}): {result.stderr[:200]}]"
            case "grep" | "glob":
                return f"[搜索 {result.pattern}: {result.match_count} 个结果]"
            case _:
                return f"[{result.tool_name}: {result.summary[:100]}]"
```

### 22.2 Context Boundary：三层上下文分层

上下文分层是 v1.0 避免 prompt 污染和恢复混乱的关键约束：

```python
class ModelVisibleContext(BaseModel):
    """唯一能进入 prompt 的层"""
    history: list[MessageItem]
    retrieved_memory: list[str]
    current_task: str | None
    handoff_payload: dict | None

@dataclass
class RuntimeOnlyContext:
    """只供代码与工具层使用，不直接发给模型"""
    config: Config
    tool_registry: ToolRegistry
    skill_registry: SkillRegistry
    logger: Logger
    budget_tracker: BudgetTracker
    workspace_handle: WorkspaceHandle
    secrets: SecretStore

@dataclass
class PersistedRunState:
    """用于恢复、审计、回放，不等价于对话历史"""
    run_state: RunState
    snapshots: list[str]
    session_refs: list[str]
```

规则：
- 只有 `ModelVisibleContext` 能进入 prompt
- `RuntimeOnlyContext` 只供代码与工具层使用，不直接发给模型
- `PersistedRunState` 用于恢复、审计、回放，不等价于对话历史

## 23. Reflection 机制

Builder 在 gate 失败时调用 `reflect()`，用 reasoner 模型做结构化根因分析。设计参考 Reflexion（verbal reflection）+ SWE-Agent（完整环境观察）+ Aider（确定性工具反馈）。

**核心设计原则：好的观察 > 好的反思——把 lint output、test output、git diff 等确定性信号完整喂给 LLM，而非让它猜。**

### 23.1 Reflection 输出 Schema

```python
class Reflection(BaseModel):
    """reflect() 的结构化输出，由 reasoner 模型生成"""

    error_category: Literal[
        "syntax",       # 语法错误（lint/type check 失败）
        "logic",        # 逻辑错误（测试失败、断言不通过）
        "dependency",   # 依赖问题（import 失败、版本冲突）
        "design",       # 设计问题（接口不匹配、架构不合理）
        "plan",         # 计划问题（任务拆分不当、缺少前置步骤）
        "environment",  # 环境问题（命令不存在、权限不足）
    ]
    root_cause: str              # 一句话根因
    learnings: list[str]         # 本次教训（注入后续 context）
    action: Literal[
        "retry_same",            # 同一方案微调后重试
        "retry_different",       # 换一种方案重试
        "replan",                # 根因在计划层面，触发 Adaptive Planning
        "abort",                 # 无法恢复，终止任务
    ]
    retry_hint: str | None       # action=retry 时，具体的修正建议
    confidence: float            # 0.0~1.0，对根因判断的信心
```

### 23.2 Reflect Prompt 策略

核心原则：喂完整的环境观察（git diff、lint/test 完整输出、当前文件上下文、历史反思），不要摘要。用 reasoner 模型（deepseek-r1-0528），不用 chat 模型。

```python
async def reflect(self, result: ExecutionResult, gate: GateResult) -> Reflection:
    prompt = f"""
    ## 任务
    {result.task.description}

    ## 你的代码变更
    ```diff
    {result.git_diff}
    ```

    ## Gate 检查结果
    - 通过: {gate.passed_checks}
    - 失败: {gate.failed_checks}

    ## 完整错误输出（不要摘要，原文粘贴）
    ```
    {gate.raw_output[:8000]}
    ```

    ## 当前文件上下文
    {result.relevant_file_contents[:4000]}

    ## 历史反思（避免重复同一错误）
    {context.previous_reflections[-3:]}

    请分析根因并决定下一步行动。
    """
    return await self.reasoner.generate(prompt, output_schema=Reflection)
```

### 23.3 Stuck Detection（转圈检测）

Agent 最常见的失败模式是陷入死循环——连续做相同的事并期待不同的结果。

```python
class StuckDetector:
    """检测 Agent 是否陷入重复循环"""

    window: list[Reflection]  # 最近 N 次反思记录

    def is_stuck(self) -> bool:
        if len(self.window) < 3:
            return False

        recent = self.window[-3:]

        # 规则 1：连续 3 次相同 error_category + 相似 root_cause
        if all(r.error_category == recent[0].error_category for r in recent):
            if self._similarity(recent) > 0.8:
                return True

        # 规则 2：连续 3 次 action=retry_same 但问题未解决
        if all(r.action == "retry_same" for r in recent):
            return True

        # 规则 3：confidence 持续下降（Agent 越来越没信心）
        if all(recent[i].confidence < recent[i-1].confidence
               for i in range(1, len(recent))):
            return True

        return False

    def get_unstuck_action(self) -> str:
        """强制脱困策略"""
        stuck_count = self._consecutive_stuck_count()
        if stuck_count == 1:
            return "retry_different"    # 第 1 次 stuck → 换方案
        elif stuck_count == 2:
            return "replan"             # 第 2 次 stuck → 重规划
        else:
            return "abort"              # 第 3 次 stuck → 放弃，交给人
```

### 23.4 Reflection 在执行循环中的集成

```python
async def build(self, plan: Plan, context: Context) -> BuilderOutput:
    tasks = self.parse_plan(plan)  # 用 reasoner 模型解析
    stuck_detector = StuckDetector()

    for task in tasks:
        while not task.done:
            result = await self.execute(task)        # 用 chat 模型编码
            gate = self.check_gate(result)           # 纯规则检查

            if gate.passed:
                task.done = True
                stuck_detector.reset()
                continue

            # Reflect
            reflection = await self.reflect(result, gate)
            context.update(reflection.learnings)
            stuck_detector.record(reflection)

            # Stuck detection 优先于 reflection 的 action
            if stuck_detector.is_stuck():
                forced_action = stuck_detector.get_unstuck_action()
                if forced_action == "abort":
                    raise BuildFailure(task, "stuck: 连续失败无法恢复")
                elif forced_action == "replan":
                    return await self.build_with_replan(plan, context)
                # forced_action == "retry_different" → 继续但强制换方案

            # 正常 reflection action
            if reflection.action == "replan":
                return await self.build_with_replan(plan, context)
            elif reflection.action == "abort":
                raise BuildFailure(task, reflection.root_cause)
            # retry_same / retry_different → 继续循环

            task.retries += 1
            if task.retries >= MAX_RETRIES:
                raise BuildFailure(task, f"exceeded {MAX_RETRIES} retries")
```

## 24. Adaptive Planning（动态重规划）

Builder 在执行过程中可以中途修正计划，而非死板走完预定步骤：

```python
async def build_with_replan(self, plan: Plan, context: Context) -> BuilderOutput:
    tasks = self.parse_plan(plan)
    completed = []

    while tasks:
        task = tasks[0]
        result = await self.execute(task)
        gate = self.check_gate(result)

        if gate.passed:
            completed.append(task)
            tasks.pop(0)
        else:
            # 动态重规划：根据已完成的结果和当前失败信息，重新规划剩余任务
            replan = await self.replan(
                original_plan=plan,
                completed=completed,
                failed_task=task,
                error=gate.errors
            )
            if replan.should_abort:
                raise BuildFailure(task, gate.errors)
            tasks = replan.new_tasks  # 替换剩余任务列表

    return self.collect_output()
```

重规划触发条件：
- Gate 失败且 `reflect()` 判断根因不在当前任务而在计划本身
- 执行中发现新依赖或拀制点（如 API 不存在、库版本不兼容）
- 任务间依赖关系变化（前序任务产出改变了后续任务的输入）

## 25. 运行时内核定义（v1.0 Runner / RunState / NextStep）

> 本节约定了 v1.0 运行时内核的完整语义，是模块 01 的运行时部分真相源。
> Arch 来源: `00000000-00-architecture-overview.md` §3.1.1, §5.1.1.1, §5.1.1.2

### 25.1 分层模型

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
- `ProductOrchestrator` 只负责模式入口、创建/恢复 `RunState`、调用 `Runner.run(...)`
- `Runner` 是唯一执行循环，推进同一个 run 直到完成、中断或终止
- `current_agent`、`current_phase` 只是 `RunState` 中的当前所有权指针
- gate failure、tool approval、resume 都发生在同一个 run 内

### 25.2 RunState 数据模型

```python
@dataclass
class RunState:
    """唯一运行时状态，所有真相源。"""
    run_id: str
    session_id: str | None = None
    current_agent: str | None = None       # "builder" / "reviewer" / "deployer"
    current_phase: str | None = None       # "plan_parsing" / "coding" / ...
    phase: Literal["initializing", "running", "paused", "completed", "aborted"]
    turn: int = 0
    tool_history: list[dict] = field(default_factory=list)
    pending_interruptions: list[dict] = field(default_factory=list)
    handoff_payload: dict | None = None
    model: str = "deepseek-v3.2"
    output: str | None = None
    errors: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @property
    def is_finished(self) -> bool:
        return self.phase in ("completed", "aborted")
```

### 25.3 Runner 内核

```python
class Runner:
    """唯一执行循环内核。"""

    def __init__(self, config: Config, tool_registry: ToolRegistry, llm_provider):
        self.config = config
        self.tool_registry = tool_registry
        self.llm_provider = llm_provider
        self.hooks = HookManager()

    def run(self, state: RunState) -> RunState:
        """主循环，直到 state.is_finished。"""
        self.hooks.emit("run.start", {"run_id": state.run_id})
        while not state.is_finished:
            state.turn += 1
            next_step = self.think(state)
            state = self.resolve(state, next_step)
            self.persist(state)
            self.hooks.emit("turn.end", {"turn": state.turn, "step": next_step.type})
        self.hooks.emit("run.end", {"run_id": state.run_id, "phase": state.phase})
        return state

    def think(self, state: RunState) -> NextStep:
        """调用 LLM 得到 next step。"""

    def resolve(self, state: RunState, next_step: NextStep) -> RunState:
        """根据 NextStep type 分发处理。"""
```

### 25.4 resolve() 分支逻辑

`resolve()` 必须处理 `NextStep` 的全部 8 种 type：

| type | 动作 | 更新字段 |
|------|------|---------|
| `final_output` | phase="completed", output=next_step.output | phase, output |
| `tool_call` | 调用 tool_registry，记录结果到 tool_history | tool_history |
| `phase_handoff` | 更新 current_agent/current_phase，重置 turn | current_agent, current_phase, handoff_payload, turn |
| `retry_same` | 继续循环 | (无特殊变更) |
| `retry_different` | 继续循环，记录 reason | errors |
| `replan` | 当前标记 abort（v1.1 实现完整重规划） | phase="aborted" |
| `interruption` | phase="paused", 记录 pending_interruptions | phase, pending_interruptions |
| `abort` | phase="aborted", 记录 error | phase, errors |

### 25.5 ProductOrchestrator 边界

```python
class ProductOrchestrator:
    """产品层入口，不负责执行循环。"""

    def __init__(self, config: Config):
        self.config = config
        self.tool_registry = ToolRegistry(config)

    def create_run_state(self, run_id: str, session_id: str | None = None) -> RunState:
        """创建初始 RunState。"""

    def resume_run_state(self, run_id: str, memory_dir: Path) -> RunState | None:
        """从文件系统恢复 RunState。"""
```

边界规则：
- `ProductOrchestrator` 不实现执行循环
- 它只负责组装初始状态、创建 Runner、调用 `Runner.run()`

### 25.6 HookManager

v1.x hook 点：`run.start`/`run.end`、`phase.start`/`phase.end`、`model.start`/`model.end`、`tool.start`/`tool.end`、`handoff`、`gate.pass`/`gate.fail`、`reflection`、`resume`、`budget.warn`/`budget.over`。

### 25.7 NextStep 协议（完整定义）

```python
class NextStep(BaseModel):
    type: Literal[
        "final_output",
        "tool_call",
        "phase_handoff",
        "retry_same",
        "retry_different",
        "replan",
        "interruption",
        "abort",
    ]
    output: str | None = None
    request: ToolRequest | None = None
    next_agent: str | None = None
    next_phase: str | None = None
    reason: str | None = None
```

---

*规范版本: v1.0.0*
*创建日期: 2026-04-16*
