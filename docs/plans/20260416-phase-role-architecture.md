# Phase-Role-Architecture Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the 8-phase, 8-agent, 37-skill workflow engine for Sloth Agent black-light factory.

**Architecture:** Data models (Phase, Agent, Skill, Scenario) → Registry → Workflow Engine → Gate validation → Memory store. Each Phase has 1 Agent, each Agent has N Skills, Scenarios are valid Phase sequences constrained by Pre/Post relationships.

**Tech Stack:** Python 3.10+, pydantic, pytest, pyyaml, sqlite3 (existing)

---

## Task 1: Core Data Models (Phase, Agent, Skill, Scenario, Gate)

**Files:**
- Create: `src/workflow/models.py`
- Create: `src/workflow/__init__.py`
- Test: `tests/workflow/test_models.py`

### Step 1: Write the failing test

```python
# tests/workflow/test_models.py

from sloth_agent.workflow.models import Phase, Agent, Skill, Scenario, Gate

def test_phase_creation():
    phase = Phase(
        id="phase-1",
        name="需求分析",
        agent_id="analyst",
        pre_phases=[],
        post_phases=["phase-2"],
        input_schema={"type": "requirements"},
        output_schema={"type": "problem_statement"},
        skills=["brainstorming", "office-hours"],
        llm_config={"provider": "glm", "model": "glm-4"},
        gates=["问题陈述已生成"],
        scenarios=["standard"],
    )
    assert phase.id == "phase-1"
    assert phase.agent_id == "analyst"
    assert phase.pre_phases == []
    assert len(phase.skills) == 2

def test_agent_creation():
    agent = Agent(
        id="analyst",
        name="需求分析师",
        skills=["brainstorming", "office-hours"],
        llm_config={"provider": "glm", "model": "glm-4"},
        description="负责需求分析和产品方向诊断",
    )
    assert agent.id == "analyst"
    assert len(agent.skills) == 2

def test_skill_creation():
    skill = Skill(
        id="brainstorming",
        name="Brainstorming",
        source="superpowers",
        trigger="auto",
        description="通过提问精炼需求",
        input_schema={"type": "requirements"},
        output_schema={"type": "problem_statement"},
    )
    assert skill.id == "brainstorming"
    assert skill.source == "superpowers"
    assert skill.trigger == "auto"

def test_scenario_creation():
    scenario = Scenario(
        id="standard",
        name="标准开发",
        phases=["phase-1", "phase-2", "phase-3"],
        description="端到端全流程",
    )
    assert scenario.id == "standard"
    assert len(scenario.phases) == 3

def test_gate_creation():
    gate = Gate(
        name="测试通过",
        check_fn=lambda r: r.get("passed", False),
        description="所有测试必须通过",
    )
    assert gate.check({"passed": True}) is True
    assert gate.check({"passed": False}) is False
```

### Step 2: Run test to verify it fails

```bash
uv run pytest tests/workflow/test_models.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'sloth_agent.workflow'"

### Step 3: Write minimal implementation

```python
# src/workflow/__init__.py

from sloth_agent.workflow.models import (
    Phase,
    Agent,
    Skill,
    Scenario,
    Gate,
)

__all__ = ["Phase", "Agent", "Skill", "Scenario", "Gate"]
```

```python
# src/workflow/models.py

"""Core data models for the Phase-Role-Architecture."""

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Gate:
    """验证门控"""
    name: str
    check_fn: Callable[[dict], bool]
    description: str = ""

    def check(self, result: dict) -> bool:
        """Check if the result passes this gate."""
        return self.check_fn(result)


@dataclass
class Phase:
    """工作流阶段"""
    id: str
    name: str
    agent_id: str
    pre_phases: list[str] = field(default_factory=list)
    post_phases: list[str] = field(default_factory=list)
    input_schema: dict = field(default_factory=dict)
    output_schema: dict = field(default_factory=dict)
    skills: list[str] = field(default_factory=list)
    llm_config: dict = field(default_factory=dict)
    gates: list[str] = field(default_factory=list)
    scenarios: list[str] = field(default_factory=list)


@dataclass
class Agent:
    """执行 Phase 的 Agent"""
    id: str
    name: str
    skills: list[str] = field(default_factory=list)
    llm_config: dict = field(default_factory=dict)
    description: str = ""


@dataclass
class Skill:
    """技能定义"""
    id: str
    name: str
    source: str  # "superpowers" | "gstack"
    trigger: str  # "auto" | "manual"
    description: str = ""
    input_schema: dict = field(default_factory=dict)
    output_schema: dict = field(default_factory=dict)


@dataclass
class Scenario:
    """场景定义"""
    id: str
    name: str
    phases: list[str] = field(default_factory=list)
    description: str = ""
```

### Step 4: Run test to verify it passes

```bash
uv run pytest tests/workflow/test_models.py -v
```

Expected: PASS (all 5 tests)

### Step 5: Commit

```bash
git add src/workflow/ tests/workflow/test_models.py
git commit -m "feat: add core data models (Phase, Agent, Skill, Scenario, Gate)"
```

---

## Task 2: Registry (PhaseRegistry, AgentRegistry, SkillRegistry, ScenarioRegistry)

**Files:**
- Create: `src/workflow/registry.py`
- Modify: `src/workflow/__init__.py` (add exports)
- Test: `tests/workflow/test_registry.py`

### Step 1: Write the failing test

```python
# tests/workflow/test_registry.py

from sloth_agent.workflow.registry import PhaseRegistry, SkillRegistry, ScenarioValidator

def test_phase_registry_get():
    reg = PhaseRegistry()
    phase = reg.get("phase-1")
    assert phase is not None
    assert phase.id == "phase-1"
    assert phase.name == "需求分析"

def test_phase_registry_get_all():
    reg = PhaseRegistry()
    phases = reg.get_all()
    assert len(phases) == 8

def test_phase_registry_get_by_scenario():
    reg = PhaseRegistry()
    phases = reg.get_by_scenario("standard")
    assert len(phases) == 8
    assert phases[0].id == "phase-1"

def test_skill_registry_get():
    reg = SkillRegistry()
    skill = reg.get("brainstorming")
    assert skill is not None
    assert skill.source == "superpowers"
    assert skill.trigger == "auto"

def test_skill_registry_get_by_source():
    reg = SkillRegistry()
    superpowers = reg.get_by_source("superpowers")
    gstack = reg.get_by_source("gstack")
    assert len(superpowers) == 14
    assert len(gstack) == 23

def test_scenario_validator_valid():
    reg = PhaseRegistry()
    validator = ScenarioValidator(reg)
    valid, errors = validator.validate_scenario("standard")
    assert valid is True
    assert errors == []

def test_scenario_validator_invalid_flow():
    reg = PhaseRegistry()
    validator = ScenarioValidator(reg)
    # phase-1 can only flow to phase-2
    valid, errors = validator.validate_sequence(["phase-1", "phase-3"])
    assert valid is False
    assert len(errors) > 0

def test_scenario_validator_entry_phase():
    reg = PhaseRegistry()
    validator = ScenarioValidator(reg)
    # phase-2 has pre_phases, cannot be entry
    valid, errors = validator.validate_sequence(["phase-2", "phase-3"])
    assert valid is False

def test_scenario_validator_io_mismatch():
    reg = PhaseRegistry()
    validator = ScenarioValidator(reg)
    valid, errors = validator.validate_sequence(["phase-1", "phase-2"])
    assert valid is True
```

### Step 2: Run test to verify it fails

```bash
uv run pytest tests/workflow/test_registry.py -v
```

Expected: FAIL with "ImportError: cannot import name 'PhaseRegistry'"

### Step 3: Write minimal implementation

```python
# src/workflow/registry.py

"""Registry for Phases, Agents, Skills, and Scenarios."""

from sloth_agent.workflow.models import Phase, Agent, Skill, Scenario, Gate

# =============================================================================
# Phase Registry
# =============================================================================

_ALL_PHASES: list[Phase] = [
    Phase(
        id="phase-1",
        name="需求分析",
        agent_id="analyst",
        pre_phases=[],
        post_phases=["phase-2"],
        input_schema={"type": "requirements"},
        output_schema={"type": "problem_statement"},
        skills=["brainstorming", "office-hours", "design-shotgun", "design-consultation"],
        llm_config={"provider": "glm", "model": "glm-4"},
        gates=["问题陈述已生成"],
        scenarios=["standard", "requirement-only"],
    ),
    Phase(
        id="phase-2",
        name="计划制定",
        agent_id="planner",
        pre_phases=["phase-1"],
        post_phases=["phase-3"],
        input_schema={"type": "problem_statement"},
        output_schema={"type": "executable_plan"},
        skills=["writing-plans", "autoplan", "plan-ceo-review", "plan-eng-review", "plan-design-review", "plan-devex-review"],
        llm_config={"provider": "claude", "model": "claude-3-5-sonnet"},
        gates=["SPEC 已生成", "PLAN 已生成"],
        scenarios=["standard", "requirement-only"],
    ),
    Phase(
        id="phase-3",
        name="编码实现",
        agent_id="engineer",
        pre_phases=["phase-2"],
        post_phases=["phase-4", "phase-5"],
        input_schema={"type": "executable_plan"},
        output_schema={"type": "code_and_tests"},
        skills=["test-driven-development", "subagent-driven-development", "using-git-worktrees", "executing-plans", "dispatching-parallel-agents"],
        llm_config={"provider": "deepseek", "model": "deepseek-chat"},
        gates=["TDD 循环通过", "测试覆盖率 >= 80%"],
        scenarios=["standard", "frontend-only", "backend-only"],
    ),
    Phase(
        id="phase-4",
        name="调试排错",
        agent_id="debugger",
        pre_phases=["phase-3", "phase-4"],
        post_phases=["phase-5"],
        input_schema={"type": "error_info"},
        output_schema={"type": "fixed_code"},
        skills=["systematic-debugging", "browse", "investigate", "freeze", "guard"],
        llm_config={"provider": "claude", "model": "claude-3-5-sonnet"},
        gates=["测试通过", "无新错误"],
        scenarios=["standard", "backend-only", "bug-fix", "debug-only"],
    ),
    Phase(
        id="phase-5",
        name="代码审查",
        agent_id="reviewer",
        pre_phases=["phase-3", "phase-4"],
        post_phases=["phase-6"],
        input_schema={"type": "code_and_tests"},
        output_schema={"type": "review_report"},
        skills=["requesting-code-review", "verification-before-completion", "review", "codex", "receiving-code-review"],
        llm_config={"provider": "claude", "model": "claude-3-5-sonnet"},
        gates=["审查通过", "verification 完成"],
        scenarios=["standard", "frontend-only", "backend-only", "bug-fix", "review-only"],
    ),
    Phase(
        id="phase-6",
        name="质量验证",
        agent_id="qa-engineer",
        pre_phases=["phase-5"],
        post_phases=["phase-7"],
        input_schema={"type": "reviewed_code"},
        output_schema={"type": "qa_report"},
        skills=["qa", "qa-only", "cso", "plan-design-review", "browse", "health"],
        llm_config={"provider": "claude", "model": "claude-3-5-sonnet"},
        gates=["QA 通过", "安全审计通过"],
        scenarios=["standard", "frontend-only", "backend-only", "review-only"],
    ),
    Phase(
        id="phase-7",
        name="发布上线",
        agent_id="release-engineer",
        pre_phases=["phase-5", "phase-6"],
        post_phases=["phase-8"],
        input_schema={"type": "qa_passed_code"},
        output_schema={"type": "deployed_artifact"},
        skills=["finishing-a-development-branch", "ship", "land-and-deploy", "document-release", "setup-deploy"],
        llm_config={"provider": "claude", "model": "claude-3-5-sonnet"},
        gates=["部署成功", "CI 通过"],
        scenarios=["standard", "frontend-only", "backend-only", "bug-fix", "ship-only"],
    ),
    Phase(
        id="phase-8",
        name="上线监控",
        agent_id="sre",
        pre_phases=["phase-7"],
        post_phases=[],
        input_schema={"type": "deployed_artifact"},
        output_schema={"type": "monitor_report"},
        skills=["canary", "benchmark", "retro", "learn"],
        llm_config={"provider": "minimax", "model": "MiniMax-Text-01"},
        gates=["监控正常", "日报已生成"],
        scenarios=["standard", "ship-only"],
    ),
]

_PHASE_BY_ID: dict[str, Phase] = {p.id: p for p in _ALL_PHASES}

# =============================================================================
# Agent Registry
# =============================================================================

_ALL_AGENTS: list[Agent] = [
    Agent(id="analyst", name="需求分析师", skills=["brainstorming", "office-hours", "design-shotgun", "design-consultation"], llm_config={"provider": "glm", "model": "glm-4"}, description="负责需求分析和产品方向诊断"),
    Agent(id="planner", name="计划制定者", skills=["writing-plans", "autoplan", "plan-ceo-review", "plan-eng-review"], llm_config={"provider": "claude", "model": "claude-3-5-sonnet"}, description="负责计划制定和方案审查"),
    Agent(id="engineer", name="工程师", skills=["test-driven-development", "subagent-driven-development", "using-git-worktrees"], llm_config={"provider": "deepseek", "model": "deepseek-chat"}, description="负责编码实现"),
    Agent(id="debugger", name="调试员", skills=["systematic-debugging", "browse", "investigate", "freeze"], llm_config={"provider": "claude", "model": "claude-3-5-sonnet"}, description="负责调试排错"),
    Agent(id="reviewer", name="审查员", skills=["requesting-code-review", "verification-before-completion", "review", "codex"], llm_config={"provider": "claude", "model": "claude-3-5-sonnet"}, description="负责代码审查"),
    Agent(id="qa-engineer", name="QA 工程师", skills=["qa", "qa-only", "cso", "plan-design-review"], llm_config={"provider": "claude", "model": "claude-3-5-sonnet"}, description="负责质量验证"),
    Agent(id="release-engineer", name="发布工程师", skills=["finishing-a-development-branch", "ship", "land-and-deploy"], llm_config={"provider": "claude", "model": "claude-3-5-sonnet"}, description="负责发布上线"),
    Agent(id="sre", name="SRE", skills=["canary", "benchmark", "retro", "learn"], llm_config={"provider": "minimax", "model": "MiniMax-Text-01"}, description="负责上线监控"),
]

_AGENT_BY_ID: dict[str, Agent] = {a.id: a for a in _ALL_AGENTS}

# =============================================================================
# Skill Registry
# =============================================================================

_SUPERPOWERS_SKILLS = [
    Skill("brainstorming", "Brainstorming", "superpowers", "auto+manual", "通过提问精炼需求"),
    Skill("writing-plans", "Writing Plans", "superpowers", "auto+manual", "将工作分解为微任务"),
    Skill("test-driven-development", "TDD", "superpowers", "auto+manual", "RED-GREEN-REFACTOR 循环"),
    Skill("subagent-driven-development", "Subagent 驱动开发", "superpowers", "auto+manual", "子代理逐任务开发"),
    Skill("using-git-worktrees", "Git Worktrees", "superpowers", "auto+manual", "隔离工作空间"),
    Skill("systematic-debugging", "系统调试", "superpowers", "auto+manual", "四阶段根因分析"),
    Skill("requesting-code-review", "代码审查请求", "superpowers", "auto+manual", "独立 reviewer 通道"),
    Skill("verification-before-completion", "完成前验证", "superpowers", "auto+manual", "完成前收集证据"),
    Skill("finishing-a-development-branch", "分支收尾", "superpowers", "auto+manual", "合并/PR 决策"),
    Skill("receiving-code-review", "接收审查反馈", "superpowers", "auto+manual", "响应审查反馈"),
    Skill("executing-plans", "执行计划", "superpowers", "auto+manual", "批量执行计划"),
    Skill("dispatching-parallel-agents", "并行子代理", "superpowers", "auto+manual", "并发子代理工作流"),
    Skill("writing-skills", "技能创建", "superpowers", "auto+manual", "创建/修改技能"),
    Skill("using-superpowers", "Superpowers 入门", "superpowers", "auto+manual", "技能系统介绍"),
]

_GSTACK_SKILLS = [
    Skill("office-hours", "YC Office Hours", "gstack", "manual", "6 个强制问题诊断产品方向"),
    Skill("autoplan", "自动审查管道", "gstack", "manual", "CEO → 设计 → 工程三阶段自动审查"),
    Skill("browse", "浏览器自动化", "gstack", "manual", "真实 Chromium 浏览器"),
    Skill("investigate", "系统调试", "gstack", "manual", "浏览器级系统调试"),
    Skill("review", "代码审查", "gstack", "manual", "发现通过 CI 但生产会炸的 bug"),
    Skill("codex", "Codex 第二意见", "gstack", "manual", "跨模型第二意见"),
    Skill("qa", "QA 测试", "gstack", "manual", "真实浏览器端到端测试"),
    Skill("qa-only", "QA 报告", "gstack", "manual", "报告模式（不修改代码）"),
    Skill("cso", "安全审计", "gstack", "manual", "OWASP Top 10 + STRIDE"),
    Skill("plan-ceo-review", "CEO 审查", "gstack", "manual", "重新思考问题，4 种模式"),
    Skill("plan-eng-review", "工程审查", "gstack", "manual", "锁定架构、数据流、边界条件"),
    Skill("plan-design-review", "设计审查", "gstack", "manual", "80 项设计审计"),
    Skill("plan-devex-review", "DX 审查", "gstack", "manual", "交互式 DX 审查"),
    Skill("design-consultation", "设计咨询", "gstack", "manual", "从零构建设计系统"),
    Skill("design-shotgun", "设计探索", "gstack", "manual", "生成 4-6 个 AI 方案变体"),
    Skill("design-html", "设计实现", "gstack", "manual", "生成生产级 HTML/CSS"),
    Skill("design-review", "设计审查", "gstack", "manual", "审计 + 修复"),
    Skill("devex-review", "DX 测试", "gstack", "manual", "实时审计 onboarding 流程"),
    Skill("ship", "发布", "gstack", "manual", "测试 + 覆盖率 + PR"),
    Skill("land-and-deploy", "部署", "gstack", "manual", "CI + 部署验证"),
    Skill("canary", "Canary 监控", "gstack", "manual", "控制台错误 + 性能回归监控"),
    Skill("benchmark", "性能基准", "gstack", "manual", "页面加载基准测试"),
    Skill("retro", "回顾", "gstack", "manual", "每周团队回顾"),
    Skill("learn", "学习管理", "gstack", "manual", "管理学习记录"),
    Skill("document-release", "发布文档", "gstack", "manual", "自动更新文档"),
    Skill("setup-deploy", "部署配置", "gstack", "manual", "一键配置部署"),
]

_ALL_SKILLS: list[Skill] = _SUPERPOWERS_SKILLS + _GSTACK_SKILLS
_SKILL_BY_ID: dict[str, Skill] = {s.id: s for s in _ALL_SKILLS}

# =============================================================================
# Scenario Definitions
# =============================================================================

_SCENARIOS: dict[str, list[str]] = {
    "standard": ["phase-1", "phase-2", "phase-3", "phase-4", "phase-5", "phase-6", "phase-7", "phase-8"],
    "frontend-only": ["phase-3", "phase-5", "phase-6", "phase-7"],
    "backend-only": ["phase-3", "phase-4", "phase-5", "phase-6", "phase-7"],
    "requirement-only": ["phase-1", "phase-2"],
    "ship-only": ["phase-7", "phase-8"],
    "bug-fix": ["phase-4", "phase-5", "phase-7"],
    "review-only": ["phase-5", "phase-6"],
    "debug-only": ["phase-4"],
}

# =============================================================================
# Gate Definitions
# =============================================================================

_ALL_GATES: dict[str, Gate] = {
    "TDD 循环通过": Gate("TDD 循环通过", lambda r: r.get("tests_passed", False), "所有测试必须通过"),
    "测试覆盖率 >= 80%": Gate("测试覆盖率 >= 80%", lambda r: r.get("coverage", 0) >= 80, "测试覆盖率必须 >= 80%"),
    "测试通过": Gate("测试通过", lambda r: r.get("tests_passed", False), "所有测试必须通过"),
    "无新错误": Gate("无新错误", lambda r: not r.get("new_errors", False), "不应产生新错误"),
    "审查通过": Gate("审查通过", lambda r: r.get("review_passed", False), "代码审查必须通过"),
    "verification 完成": Gate("verification 完成", lambda r: r.get("verification_done", False), "verification 必须完成"),
    "QA 通过": Gate("QA 通过", lambda r: r.get("qa_passed", False), "QA 测试必须通过"),
    "安全审计通过": Gate("安全审计通过", lambda r: r.get("security_passed", False), "安全审计必须通过"),
    "部署成功": Gate("部署成功", lambda r: r.get("deployed", False), "部署必须成功"),
    "CI 通过": Gate("CI 通过", lambda r: r.get("ci_passed", False), "CI 必须通过"),
    "监控正常": Gate("监控正常", lambda r: r.get("monitoring_ok", False), "监控必须正常"),
    "日报已生成": Gate("日报已生成", lambda r: r.get("report_generated", False), "日报必须生成"),
    "问题陈述已生成": Gate("问题陈述已生成", lambda r: r.get("problem_statement", "") != "", "问题陈述不能为空"),
    "SPEC 已生成": Gate("SPEC 已生成", lambda r: r.get("spec_generated", False), "SPEC 必须生成"),
    "PLAN 已生成": Gate("PLAN 已生成", lambda r: r.get("plan_generated", False), "PLAN 必须生成"),
}

# =============================================================================
# Registry Classes
# =============================================================================

class PhaseRegistry:
    """Phase 注册表"""

    @staticmethod
    def get(phase_id: str) -> Phase:
        """Get a phase by ID."""
        if phase_id not in _PHASE_BY_ID:
            raise KeyError(f"Phase not found: {phase_id}")
        return _PHASE_BY_ID[phase_id]

    @staticmethod
    def get_all() -> list[Phase]:
        """Get all phases."""
        return list(_ALL_PHASES)

    @staticmethod
    def get_by_scenario(scenario_id: str) -> list[Phase]:
        """Get phases for a scenario."""
        if scenario_id not in _SCENARIOS:
            raise KeyError(f"Scenario not found: {scenario_id}")
        return [_PHASE_BY_ID[pid] for pid in _SCENARIOS[scenario_id]]

    @staticmethod
    def list_scenarios() -> list[str]:
        """List all scenario IDs."""
        return list(_SCENARIOS.keys())


class AgentRegistry:
    """Agent 注册表"""

    @staticmethod
    def get(agent_id: str) -> Agent:
        """Get an agent by ID."""
        if agent_id not in _AGENT_BY_ID:
            raise KeyError(f"Agent not found: {agent_id}")
        return _AGENT_BY_ID[agent_id]

    @staticmethod
    def get_all() -> list[Agent]:
        """Get all agents."""
        return list(_ALL_AGENTS)


class SkillRegistry:
    """Skill 注册表"""

    @staticmethod
    def get(skill_id: str) -> Skill:
        """Get a skill by ID."""
        if skill_id not in _SKILL_BY_ID:
            raise KeyError(f"Skill not found: {skill_id}")
        return _SKILL_BY_ID[skill_id]

    @staticmethod
    def get_all() -> list[Skill]:
        """Get all skills."""
        return list(_ALL_SKILLS)

    @staticmethod
    def get_by_source(source: str) -> list[Skill]:
        """Get skills by source."""
        return [s for s in _ALL_SKILLS if s.source == source]


class ScenarioValidator:
    """Scenario 验证器"""

    def __init__(self, phase_registry: PhaseRegistry | None = None):
        self.phases = phase_registry or PhaseRegistry()

    def validate_sequence(self, phase_ids: list[str]) -> tuple[bool, list[str]]:
        """
        Validate a phase sequence.

        Checks:
        1. Entry phase has no pre_phases
        2. Each phase can flow to the next (post_phases)
        """
        errors = []

        if not phase_ids:
            return False, ["Phase sequence is empty"]

        # Check 1: Entry phase
        entry = self.phases.get(phase_ids[0])
        if entry.pre_phases:
            errors.append(f"Entry phase {entry.id} has pre_phases: {entry.pre_phases}")

        # Check 2: Continuity
        for i in range(len(phase_ids) - 1):
            current = self.phases.get(phase_ids[i])
            next_id = phase_ids[i + 1]
            if next_id not in current.post_phases:
                errors.append(f"Phase {current.id} cannot flow to {next_id}. Valid next: {current.post_phases}")

        return len(errors) == 0, errors

    def validate_scenario(self, scenario_id: str) -> tuple[bool, list[str]]:
        """Validate a predefined scenario."""
        if scenario_id not in _SCENARIOS:
            return False, [f"Scenario not found: {scenario_id}"]
        return self.validate_sequence(_SCENARIOS[scenario_id])


def get_gate(name: str) -> Gate | None:
    """Get a gate by name."""
    return _ALL_GATES.get(name)


def get_all_gates() -> dict[str, Gate]:
    """Get all gates."""
    return dict(_ALL_GATES)
```

### Step 4: Run test to verify it passes

```bash
uv run pytest tests/workflow/test_registry.py -v
```

Expected: PASS (all 9 tests)

### Step 5: Commit

```bash
git add src/workflow/registry.py tests/workflow/test_registry.py
git commit -m "feat: add registry system with 8 phases, 8 agents, 37 skills, 8 scenarios"
```

---

## Task 3: Memory Store (Scenario → Phase → Memory)

**Files:**
- Create: `src/workflow/memory.py`
- Test: `tests/workflow/test_memory.py`

### Step 1: Write the failing test

```python
# tests/workflow/test_memory.py

from pathlib import Path
from sloth_agent.workflow.memory import ScenarioMemoryStore

def test_memory_store_create(tmp_path):
    store = ScenarioMemoryStore(tmp_path, "standard")
    assert store.scenario_id == "standard"
    assert store.base_path.exists()

def test_memory_store_save_phase_input(tmp_path):
    store = ScenarioMemoryStore(tmp_path, "standard")
    store.save_phase_input("phase-1", {"requirements": "test"})
    path = store.get_phase_path("phase-1") / "input.json"
    assert path.exists()

def test_memory_store_save_phase_output(tmp_path):
    store = ScenarioMemoryStore(tmp_path, "standard")
    store.save_phase_output("phase-1", {"problem_statement": "test"})
    path = store.get_phase_path("phase-1") / "output.json"
    assert path.exists()

def test_memory_store_save_artifact(tmp_path):
    store = ScenarioMemoryStore(tmp_path, "standard")
    store.save_artifact("phase-1", "design.md", "# Design")
    path = store.get_phase_path("phase-1") / "artifacts" / "design.md"
    assert path.exists()

def test_memory_store_load_phase_input(tmp_path):
    store = ScenarioMemoryStore(tmp_path, "standard")
    store.save_phase_input("phase-1", {"key": "value"})
    data = store.load_phase_input("phase-1")
    assert data == {"key": "value"}

def test_memory_store_save_scenario_report(tmp_path):
    store = ScenarioMemoryStore(tmp_path, "standard")
    store.save_report("# Daily Report\n\nDone.")
    path = store.base_path / "report.md"
    assert path.exists()
```

### Step 2: Run test to verify it fails

```bash
uv run pytest tests/workflow/test_memory.py -v
```

Expected: FAIL with "ImportError: cannot import name 'ScenarioMemoryStore'"

### Step 3: Write minimal implementation

```python
# src/workflow/memory.py

"""Memory store for Scenario → Phase classification."""

import json
from pathlib import Path


class ScenarioMemoryStore:
    """按 Scenario → Phase 分类的记忆存储"""

    def __init__(self, base_dir: Path | str, scenario_id: str):
        self.scenario_id = scenario_id
        self.base_path = Path(base_dir) / "scenarios" / scenario_id
        self.base_path.mkdir(parents=True, exist_ok=True)

    def get_phase_path(self, phase_id: str) -> Path:
        """Get the directory for a phase."""
        phase_dir = self.base_path / phase_id
        phase_dir.mkdir(parents=True, exist_ok=True)
        return phase_dir

    def save_phase_input(self, phase_id: str, data: dict) -> None:
        """Save phase input data."""
        path = self.get_phase_path(phase_id) / "input.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def save_phase_output(self, phase_id: str, data: dict) -> None:
        """Save phase output data."""
        path = self.get_phase_path(phase_id) / "output.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def load_phase_input(self, phase_id: str) -> dict | None:
        """Load phase input data."""
        path = self.get_phase_path(phase_id) / "input.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def load_phase_output(self, phase_id: str) -> dict | None:
        """Load phase output data."""
        path = self.get_phase_path(phase_id) / "output.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def save_artifact(self, phase_id: str, filename: str, content: str) -> Path:
        """Save a phase artifact."""
        artifacts_dir = self.get_phase_path(phase_id) / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        path = artifacts_dir / filename
        path.write_text(content)
        return path

    def save_report(self, content: str) -> Path:
        """Save scenario report."""
        path = self.base_path / "report.md"
        path.write_text(content)
        return path
```

### Step 4: Run test to verify it passes

```bash
uv run pytest tests/workflow/test_memory.py -v
```

Expected: PASS (all 6 tests)

### Step 5: Commit

```bash
git add src/workflow/memory.py tests/workflow/test_memory.py
git commit -m "feat: add ScenarioMemoryStore for Phase → Memory classification"
```

---

## Task 4: Workflow Engine + Gate Validation

**Files:**
- Create: `src/workflow/engine.py`
- Test: `tests/workflow/test_engine.py`

### Step 1: Write the failing test

```python
# tests/workflow/test_engine.py

from pathlib import Path
from unittest.mock import MagicMock
from sloth_agent.workflow.engine import WorkflowEngine

def _make_engine(tmp_path):
    return WorkflowEngine(memory_dir=tmp_path)

def test_engine_execute_scenario(tmp_path):
    engine = _make_engine(tmp_path)
    # Mock the phase executor
    engine._execute_phase = MagicMock(return_value={"tests_passed": True})
    result = engine.execute("standard")
    assert result.scenario_id == "standard"
    assert result.success is True
    assert len(result.phase_results) == 8

def test_engine_gate_failure(tmp_path):
    engine = _make_engine(tmp_path)
    # Phase-3 has gate "TDD 循环通过"
    engine._execute_phase = MagicMock(return_value={"tests_passed": False})
    result = engine.execute("standard")
    assert result.success is False
    assert result.failed_phase == "phase-3"

def test_engine_invalid_scenario(tmp_path):
    engine = _make_engine(tmp_path)
    result = engine.execute("nonexistent")
    assert result.success is False
    assert result.error is not None

def test_engine_save_memory(tmp_path):
    engine = _make_engine(tmp_path)
    engine._execute_phase = MagicMock(side_effect=[
        {"problem_statement": "test"},
        {"spec_generated": True, "plan_generated": True},
    ])
    result = engine.execute("requirement-only")
    assert result.success is True
    # Check memory was saved
    mem_file = tmp_path / "scenarios" / "requirement-only" / "phase-1" / "output.json"
    assert mem_file.exists()
```

### Step 2: Run test to verify it fails

```bash
uv run pytest tests/workflow/test_engine.py -v
```

Expected: FAIL with "ImportError: cannot import name 'WorkflowEngine'"

### Step 3: Write minimal implementation

```python
# src/workflow/engine.py

"""Workflow execution engine."""

import logging
from dataclasses import dataclass, field
from pathlib import Path

from sloth_agent.workflow.memory import ScenarioMemoryStore
from sloth_agent.workflow.registry import (
    PhaseRegistry,
    ScenarioValidator,
    get_gate,
    get_all_gates,
)

logger = logging.getLogger("workflow.engine")


@dataclass
class PhaseResult:
    """Single phase execution result."""
    phase_id: str
    phase_name: str
    success: bool
    output: dict = field(default_factory=dict)
    error: str = ""
    failed_gate: str = ""


@dataclass
class ScenarioResult:
    """Scenario execution result."""
    scenario_id: str
    success: bool
    phase_results: list[PhaseResult] = field(default_factory=list)
    failed_phase: str = ""
    error: str = ""


class WorkflowEngine:
    """工作流引擎"""

    def __init__(self, memory_dir: Path | str | None = None):
        self.phase_registry = PhaseRegistry()
        self.validator = ScenarioValidator(self.phase_registry)
        self.gates = get_all_gates()
        self.memory_dir = Path(memory_dir) if memory_dir else Path("./memory")
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def execute(self, scenario_id: str) -> ScenarioResult:
        """Execute a scenario."""
        logger.info(f"Starting scenario: {scenario_id}")

        # Validate scenario
        valid, errors = self.validator.validate_scenario(scenario_id)
        if not valid:
            logger.error(f"Invalid scenario {scenario_id}: {errors}")
            return ScenarioResult(
                scenario_id=scenario_id,
                success=False,
                error=f"Invalid scenario: {errors}",
            )

        # Get phase sequence
        phase_ids = self.validator.phases.get(scenario_id)
        memory = ScenarioMemoryStore(self.memory_dir, scenario_id)

        phase_results = []
        for phase_id in phase_ids:
            phase = self.phase_registry.get(phase_id)
            logger.info(f"Executing phase: {phase.name} ({phase_id})")

            # Load input from previous phase output or initial input
            input_data = memory.load_phase_output(phase_id) or {}

            # Execute phase
            result = self._execute_phase(phase, input_data)

            phase_results.append(result)

            # Check gates
            gate_failed = self._check_gates(phase, result)
            if gate_failed:
                logger.error(f"Gate failed for {phase_id}: {gate_failed}")
                memory.save_phase_output(phase_id, result.output)
                return ScenarioResult(
                    scenario_id=scenario_id,
                    success=False,
                    phase_results=phase_results,
                    failed_phase=phase_id,
                    error=f"Gate failed: {gate_failed}",
                )

            # Save output
            memory.save_phase_output(phase_id, result.output)
            logger.info(f"Phase {phase_id} completed successfully")

        # Save report
        memory.save_report(self._generate_report(scenario_id, phase_results))

        return ScenarioResult(
            scenario_id=scenario_id,
            success=True,
            phase_results=phase_results,
        )

    def _execute_phase(self, phase, input_data: dict) -> PhaseResult:
        """Execute a single phase. Override in subclass or use Agent executor."""
        # Default: return empty result (actual execution delegated to Agent)
        return PhaseResult(
            phase_id=phase.id,
            phase_name=phase.name,
            success=True,
            output=input_data,
        )

    def _check_gates(self, phase, result: PhaseResult) -> str:
        """Check all gates for a phase. Returns failed gate name or empty."""
        for gate_name in phase.gates:
            gate = self.gates.get(gate_name)
            if gate and not gate.check(result.output):
                return gate_name
        return ""

    def _generate_report(self, scenario_id: str, phase_results: list[PhaseResult]) -> str:
        """Generate scenario execution report."""
        lines = [f"# Scenario Report: {scenario_id}\n"]
        for pr in phase_results:
            status = "OK" if pr.success else "FAILED"
            lines.append(f"- {pr.phase_name} ({pr.phase_id}): {status}")
            if pr.failed_gate:
                lines.append(f"  - Gate failed: {pr.failed_gate}")
            if pr.error:
                lines.append(f"  - Error: {pr.error}")
        return "\n".join(lines)
```

### Step 4: Run test to verify it passes

```bash
uv run pytest tests/workflow/test_engine.py -v
```

Expected: PASS (all 4 tests)

### Step 5: Commit

```bash
git add src/workflow/engine.py tests/workflow/test_engine.py
git commit -m "feat: add WorkflowEngine with gate validation and memory persistence"
```

---

## Task 5: YAML Configuration System

**Files:**
- Modify: `src/core/config.py` (add workflow config)
- Create: `configs/workflow.yaml`
- Test: `tests/workflow/test_config.py`

### Step 1: Write the failing test

```python
# tests/workflow/test_config.py

from pathlib import Path
from sloth_agent.core.config import load_config

def test_load_config_with_workflow(tmp_path):
    config_path = tmp_path / "agent.yaml"
    config_path.write_text("""
agent:
  name: "test-agent"
workflow:
  phases:
    phase-1:
      name: 需求分析
      agent: analyst
  scenarios:
    standard:
      name: 标准开发
      phases: [phase-1, phase-2]
""")
    config = load_config(config_path)
    assert config.agent.name == "test-agent"
    assert "workflow" in config.model_dump()
```

### Step 2: Run test to verify it fails

```bash
uv run pytest tests/workflow/test_config.py -v
```

Expected: FAIL (no workflow config in Config model)

### Step 3: Write minimal implementation

```python
# Add to src/core/config.py (before the Config class):

class PhaseConfig(BaseModel):
    name: str = ""
    agent: str = ""
    llm: str = ""


class WorkflowConfig(BaseModel):
    phases: dict[str, PhaseConfig] = Field(default_factory=dict)
    scenarios: dict[str, dict] = Field(default_factory=dict)
```

```python
# Modify the Config class to add:

class Config(BaseModel):
    # ... existing fields ...
    workflow: WorkflowConfig = Field(default_factory=WorkflowConfig)
```

```yaml
# configs/workflow.yaml

phases:
  phase-1:
    name: 需求分析
    agent: analyst
    llm: glm-4
  phase-2:
    name: 计划制定
    agent: planner
    llm: claude-3-5-sonnet
  phase-3:
    name: 编码实现
    agent: engineer
    llm: deepseek-chat
  phase-4:
    name: 调试排错
    agent: debugger
    llm: claude-3-5-sonnet
  phase-5:
    name: 代码审查
    agent: reviewer
    llm: claude-3-5-sonnet
  phase-6:
    name: 质量验证
    agent: qa-engineer
    llm: claude-3-5-sonnet
  phase-7:
    name: 发布上线
    agent: release-engineer
    llm: claude-3-5-sonnet
  phase-8:
    name: 上线监控
    agent: sre
    llm: MiniMax-Text-01

scenarios:
  standard:
    name: 标准开发
    phases: [phase-1, phase-2, phase-3, phase-4, phase-5, phase-6, phase-7, phase-8]
  frontend-only:
    name: 前端开发
    phases: [phase-3, phase-5, phase-6, phase-7]
  backend-only:
    name: 后端开发
    phases: [phase-3, phase-4, phase-5, phase-6, phase-7]
  requirement-only:
    name: 需求梳理
    phases: [phase-1, phase-2]
  ship-only:
    name: 纯发布
    phases: [phase-7, phase-8]
  bug-fix:
    name: 快速修复
    phases: [phase-4, phase-5, phase-7]
  review-only:
    name: 代码审查
    phases: [phase-5, phase-6]
  debug-only:
    name: Bug 排查
    phases: [phase-4]
```

### Step 4: Run test to verify it passes

```bash
uv run pytest tests/workflow/test_config.py -v
```

Expected: PASS

### Step 5: Commit

```bash
git add src/core/config.py configs/workflow.yaml tests/workflow/test_config.py
git commit -m "feat: add workflow YAML configuration system"
```

---

## Task 6: Integration Test — Full Scenario Execution

**Files:**
- Create: `tests/workflow/test_integration.py`

### Step 1: Write the integration test

```python
# tests/workflow/test_integration.py

from pathlib import Path
from unittest.mock import MagicMock, patch
from sloth_agent.workflow.engine import WorkflowEngine
from sloth_agent.workflow.registry import PhaseRegistry

def test_full_standard_scenario(tmp_path):
    """Test the standard scenario with mocked phase execution."""
    engine = WorkflowEngine(memory_dir=tmp_path)

    # Mock each phase execution to return gate-passing results
    mock_results = {
        "phase-1": {"problem_statement": "We need a card game"},
        "phase-2": {"spec_generated": True, "plan_generated": True},
        "phase-3": {"tests_passed": True, "coverage": 85},
        "phase-4": {"tests_passed": True, "new_errors": False},
        "phase-5": {"review_passed": True, "verification_done": True},
        "phase-6": {"qa_passed": True, "security_passed": True},
        "phase-7": {"deployed": True, "ci_passed": True},
        "phase-8": {"monitoring_ok": True, "report_generated": True},
    }

    original_execute = engine._execute_phase
    engine._execute_phase = MagicMock(side_effect=lambda phase, data: type(
        "Result", (),
        {"phase_id": phase.id, "phase_name": phase.name, "success": True, "output": mock_results[phase.id], "error": "", "failed_gate": ""}
    )())

    result = engine.execute("standard")

    assert result.success is True
    assert len(result.phase_results) == 8
    assert result.failed_phase == ""

    # Verify memory was saved
    for phase_id in ["phase-1", "phase-2", "phase-3"]:
        output_file = tmp_path / "scenarios" / "standard" / phase_id / "output.json"
        assert output_file.exists(), f"Missing output for {phase_id}"

    # Verify report
    report_file = tmp_path / "scenarios" / "standard" / "report.md"
    assert report_file.exists()
    assert "OK" in report_file.read_text()

def test_frontend_only_scenario(tmp_path):
    """Test the frontend-only scenario (starts at phase-3)."""
    engine = WorkflowEngine(memory_dir=tmp_path)

    mock_results = {
        "phase-3": {"tests_passed": True, "coverage": 85},
        "phase-5": {"review_passed": True, "verification_done": True},
        "phase-6": {"qa_passed": True, "security_passed": True},
        "phase-7": {"deployed": True, "ci_passed": True},
    }

    engine._execute_phase = MagicMock(side_effect=lambda phase, data: type(
        "Result", (),
        {"phase_id": phase.id, "phase_name": phase.name, "success": True, "output": mock_results[phase.id], "error": "", "failed_gate": ""}
    )())

    result = engine.execute("frontend-only")

    assert result.success is True
    assert len(result.phase_results) == 4
    assert result.phase_results[0].phase_id == "phase-3"

def test_gate_failure_stops_execution(tmp_path):
    """Test that a gate failure stops the scenario."""
    engine = WorkflowEngine(memory_dir=tmp_path)

    # Phase-3 gate "TDD 循环通过" will fail
    engine._execute_phase = MagicMock(side_effect=lambda phase, data: type(
        "Result", (),
        {"phase_id": phase.id, "phase_name": phase.name, "success": True, "output": {"tests_passed": False}, "error": "", "failed_gate": ""}
    )())

    result = engine.execute("standard")

    assert result.success is False
    assert result.failed_phase == "phase-3"
    assert len(result.phase_results) == 3  # phase-1, phase-2, phase-3
```

### Step 2: Run test

```bash
uv run pytest tests/workflow/test_integration.py -v
```

Expected: PASS (all 3 tests)

### Step 3: Commit

```bash
git add tests/workflow/test_integration.py
git commit -m "test: add integration tests for scenario execution"
```

---

## Task 7: Export Public API

**Files:**
- Modify: `src/workflow/__init__.py`
- Modify: `src/__init__.py`

### Step 1: Update exports

```python
# src/workflow/__init__.py

from sloth_agent.workflow.models import Phase, Agent, Skill, Scenario, Gate
from sloth_agent.workflow.registry import (
    PhaseRegistry,
    AgentRegistry,
    SkillRegistry,
    ScenarioValidator,
    get_gate,
    get_all_gates,
)
from sloth_agent.workflow.engine import WorkflowEngine, PhaseResult, ScenarioResult
from sloth_agent.workflow.memory import ScenarioMemoryStore

__all__ = [
    # Models
    "Phase", "Agent", "Skill", "Scenario", "Gate",
    # Registries
    "PhaseRegistry", "AgentRegistry", "SkillRegistry", "ScenarioValidator",
    "get_gate", "get_all_gates",
    # Engine
    "WorkflowEngine", "PhaseResult", "ScenarioResult",
    # Memory
    "ScenarioMemoryStore",
]
```

```python
# Modify src/__init__.py to add:

from sloth_agent import workflow

__all__ = ["core", "workflow", "memory", "providers", "reliability", "tdd", "human"]
```

### Step 2: Run full test suite

```bash
uv run pytest tests/workflow/ -v
```

Expected: All tests pass (27 total)

### Step 3: Commit

```bash
git add src/__init__.py src/workflow/__init__.py
git commit -m "feat: export public workflow API"
```

---

## Summary

| Task | Deliverable | Tests |
|------|------------|-------|
| 1 | Core data models | 5 |
| 2 | Registry system | 9 |
| 3 | Memory store | 6 |
| 4 | Workflow engine | 4 |
| 5 | YAML config | 1 |
| 6 | Integration tests | 3 |
| 7 | Public API | (verification) |

**Total: 27 tests across 7 tasks**

Plan complete and saved to `docs/plans/20260416-phase-role-architecture.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?
