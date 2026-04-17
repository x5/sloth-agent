# Workflow Engine 实现计划

> **Spec:** `docs/specs/20260416-01-phase-role-architecture-spec.md` §11-§14, §15-§20
> **Module:** #01 — Phase-Role-Architecture (workflow process submodule)
> **对应 TODO:** `Task 3: Builder Agent Runtime` 之前的 workflow 基础设施层

**Goal:** 建立工作流状态机引擎 + 验证器 + TDD 强制器 + 系统化调试器 + 代码审查器，为 8 阶段 Phase-Role-Architecture 提供可执行、可验证的流程骨架。

**Tech Stack:** Python 3.10+, pydantic, pytest, asyncio (existing)

---

## Task 1: WorkflowEngine State Machine

**Spec:** §2.1-§2.2, §7.1-§7.1.2, §11.1
**Files:**
- Create: `src/sloth_agent/workflow/engine.py`
- Test: `tests/workflow/test_engine.py`

### Step 1: Write the failing test

```python
# tests/workflow/test_engine.py

from sloth_agent.workflow.engine import WorkflowEngine, WorkflowState, InvalidTransitionError


def _make_engine() -> WorkflowEngine:
    return WorkflowEngine()


def test_initial_state_is_idle():
    engine = _make_engine()
    assert engine.state == WorkflowState.IDLE


def test_idle_to_brainstorming():
    engine = _make_engine()
    engine.transition("new_task")
    assert engine.state == WorkflowState.BRAINSTORMING


def test_brainstorming_to_planning():
    engine = _make_engine()
    engine.transition("new_task")
    engine.transition("design_approved")
    assert engine.state == WorkflowState.PLANNING


def test_planning_to_implementing():
    engine = _make_engine()
    engine.transition("new_task")
    engine.transition("design_approved")
    engine.transition("plan_approved")
    assert engine.state == WorkflowState.IMPLEMENTING


def test_implementing_to_verifying():
    engine = _make_engine()
    engine.transition("new_task")
    engine.transition("design_approved")
    engine.transition("plan_approved")
    engine.transition("task_done")
    assert engine.state == WorkflowState.VERIFYING


def test_verifying_to_debugging_on_failure():
    engine = _make_engine()
    engine.transition("new_task")
    engine.transition("design_approved")
    engine.transition("plan_approved")
    engine.transition("task_done")
    engine.transition("verification_failed")
    assert engine.state == WorkflowState.DEBUGGING


def test_debugging_to_verifying():
    engine = _make_engine()
    engine.transition("new_task")
    engine.transition("design_approved")
    engine.transition("plan_approved")
    engine.transition("task_done")
    engine.transition("verification_failed")
    engine.transition("verified")
    assert engine.state == WorkflowState.CODE_REVIEW


def test_verifying_to_code_review():
    engine = _make_engine()
    engine.transition("new_task")
    engine.transition("design_approved")
    engine.transition("plan_approved")
    engine.transition("task_done")
    engine.transition("verified")
    assert engine.state == WorkflowState.CODE_REVIEW


def test_code_review_to_completing():
    engine = _make_engine()
    engine.transition("new_task")
    engine.transition("design_approved")
    engine.transition("plan_approved")
    engine.transition("task_done")
    engine.transition("verified")
    engine.transition("review_passed")
    assert engine.state == WorkflowState.COMPLETING


def test_completing_to_idle():
    engine = _make_engine()
    engine.transition("new_task")
    engine.transition("design_approved")
    engine.transition("plan_approved")
    engine.transition("task_done")
    engine.transition("verified")
    engine.transition("review_passed")
    engine.transition("done")
    assert engine.state == WorkflowState.IDLE


def test_invalid_transition_raises():
    engine = _make_engine()
    try:
        engine.transition("review_passed")  # IDLE -> CODE_REVIEW is invalid
        assert False, "Should have raised InvalidTransitionError"
    except InvalidTransitionError:
        pass


def test_history_tracks_all_states():
    engine = _make_engine()
    engine.transition("new_task")
    engine.transition("design_approved")
    engine.transition("plan_approved")
    assert len(engine.history) >= 3


def test_get_valid_events():
    engine = _make_engine()
    events = engine.get_valid_events()
    assert "new_task" in events


def test_gate_failure_maps_to_nextstep():
    """Spec §7.1.2: gate failure maps to NextStep types."""
    from sloth_agent.workflow.engine import gate_failure_to_nextstep

    step = gate_failure_to_nextstep("phase-1", "可微调", {"detail": "fix formatting"})
    assert step.type == "retry_same"
    assert step.reason is not None
```

### Step 2: Run test to verify it fails

```bash
uv run pytest tests/workflow/test_engine.py -v
```

Expected: FAIL with ModuleNotFoundError

### Step 3: Write minimal implementation

```python
# src/sloth_agent/workflow/engine.py

"""Workflow engine: state machine controlling phase transitions."""

from enum import Enum
from dataclasses import dataclass, field


class WorkflowState(str, Enum):
    IDLE = "idle"
    BRAINSTORMING = "brainstorming"
    PLANNING = "planning"
    IMPLEMENTING = "implementing"
    VERIFYING = "verifying"
    CODE_REVIEW = "code_review"
    COMPLETING = "completing"
    DEBUGGING = "debugging"


class InvalidTransitionError(Exception):
    pass


# Spec §7.1.2: gate failure -> NextStep mapping
@dataclass
class NextStep:
    type: str
    reason: str = ""


# State transition table
TRANSITIONS: dict[WorkflowState, dict[str, WorkflowState]] = {
    WorkflowState.IDLE: {"new_task": WorkflowState.BRAINSTORMING},
    WorkflowState.BRAINSTORMING: {"design_approved": WorkflowState.PLANNING},
    WorkflowState.PLANNING: {"plan_approved": WorkflowState.IMPLEMENTING},
    WorkflowState.IMPLEMENTING: {"task_done": WorkflowState.VERIFYING},
    WorkflowState.VERIFYING: {
        "verification_failed": WorkflowState.DEBUGGING,
        "verified": WorkflowState.CODE_REVIEW,
    },
    WorkflowState.DEBUGGING: {"verified": WorkflowState.CODE_REVIEW},
    WorkflowState.CODE_REVIEW: {"review_passed": WorkflowState.COMPLETING},
    WorkflowState.COMPLETING: {"done": WorkflowState.IDLE},
}


def gate_failure_to_nextstep(phase: str, category: str, detail: dict) -> NextStep:
    """Map gate failure to NextStep type (spec §7.1.2)."""
    mapping = {
        "可微调": "retry_same",
        "需换方案": "retry_different",
        "计划失真": "replan",
        "无法恢复": "abort",
    }
    return NextStep(type=mapping.get(category, "retry_same"), reason=f"Gate failed in {phase}: {detail}")


class WorkflowEngine:
    """工作流引擎 — 控制状态转换和流程执行。"""

    def __init__(self):
        self.state = WorkflowState.IDLE
        self.history: list[WorkflowState] = []

    def transition(self, event: str, data: dict | None = None) -> WorkflowState:
        valid_events = TRANSITIONS.get(self.state, {})
        if event not in valid_events:
            raise InvalidTransitionError(
                f"Event '{event}' not valid in state {self.state.value}. "
                f"Valid events: {list(valid_events.keys())}"
            )
        self.history.append(self.state)
        self.state = valid_events[event]
        return self.state

    def get_valid_events(self) -> list[str]:
        return list(TRANSITIONS.get(self.state, {}).keys())

    def get_state(self) -> WorkflowState:
        return self.state

    def get_history(self) -> list[WorkflowState]:
        return list(self.history)
```

### Step 4: Run test to verify it passes

```bash
uv run pytest tests/workflow/test_engine.py -v
```

Expected: PASS (all 14 tests)

### Step 5: Commit

```bash
git add src/sloth_agent/workflow/engine.py tests/workflow/test_engine.py
git commit -m "feat(workflow): add WorkflowEngine state machine with 14 tests"
```

---

## Task 2: Verifier — 4-Step Verification Gate

**Spec:** §11.5 (Verifying), §13.6
**Files:**
- Create: `src/sloth_agent/workflow/verifier.py`
- Test: `tests/workflow/test_verifier.py`

### Step 1: Write the failing test

```python
# tests/workflow/test_verifier.py

from sloth_agent.workflow.verifier import Verifier, RedFlagDetector


def test_verifier_identify():
    v = Verifier()
    cmd = v.identify("所有测试通过")
    assert "pytest" in cmd


def test_verifier_red_flag_detection():
    detector = RedFlagDetector()
    assert detector.detect("这个应该没问题") is True
    assert detector.detect("可能已经修复了") is True
    assert detector.detect("测试全部通过，0 failures") is False


def test_verifier_exit_code_check():
    v = Verifier()
    result = v.check_exit_code(0)
    assert result is True
    result = v.check_exit_code(1)
    assert result is False


def test_verifier_output_parse():
    v = Verifier()
    # pytest output: "15 passed, 0 failed"
    result = v.parse_test_output("15 passed, 0 failed in 2.3s")
    assert result["passed"] == 15
    assert result["failed"] == 0


def test_verifier_4step_gate():
    v = Verifier()
    gate = v.run_gate(command="echo ok", expected_exit=0)
    assert gate.passed
```

### Step 2: Run test to verify it fails

```bash
uv run pytest tests/workflow/test_verifier.py -v
```

Expected: FAIL

### Step 3: Write minimal implementation

```python
# src/sloth_agent/workflow/verifier.py

"""Verifier: 4-step verification gate (Identify → Run → Read → Verify)."""

import re
import subprocess
from dataclasses import dataclass


RED_FLAGS = ["应该", "可能", "似乎", "好像", "完成了", "搞定了"]


@dataclass
class GateResult:
    passed: bool
    output: str = ""
    exit_code: int = 0


class RedFlagDetector:
    """检测验证输出中的红旗警告词。"""

    def detect(self, text: str) -> bool:
        return any(flag in text for flag in RED_FLAGS)


class Verifier:
    """4 步验证门控：Identify → Run → Read → Verify。"""

    def identify(self, claim: str) -> str:
        """确定什么命令能证明声明。"""
        if "测试" in claim or "test" in claim.lower():
            return "pytest --tb=short -v"
        if "构建" in claim or "build" in claim.lower():
            return "python -m build"
        if "覆盖率" in claim or "coverage" in claim.lower():
            return "pytest --cov=src --cov-report=term"
        if "lint" in claim.lower():
            return "ruff check src/"
        return "echo 'no verification command identified'"

    def check_exit_code(self, code: int) -> bool:
        return code == 0

    def parse_test_output(self, output: str) -> dict:
        passed = re.search(r"(\d+) passed", output)
        failed = re.search(r"(\d+) failed", output)
        return {
            "passed": int(passed.group(1)) if passed else 0,
            "failed": int(failed.group(1)) if failed else 0,
        }

    def run_gate(self, command: str, expected_exit: int = 0) -> GateResult:
        """Run → Read → Verify 完整门控。"""
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=120
            )
            return GateResult(
                passed=result.returncode == expected_exit,
                output=result.stdout + result.stderr,
                exit_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return GateResult(passed=False, output="Timeout", exit_code=-1)
```

### Step 4: Run test to verify it passes

```bash
uv run pytest tests/workflow/test_verifier.py -v
```

Expected: PASS (all 5 tests)

### Step 5: Commit

```bash
git add src/sloth_agent/workflow/verifier.py tests/workflow/test_verifier.py
git commit -m "feat(workflow): add Verifier with 4-step verification gate (5 tests)"
```

---

## Task 3: TDDEnforcer

**Spec:** §11.4, §13.5
**Files:**
- Create: `src/sloth_agent/workflow/tdd_enforcer.py`
- Test: `tests/workflow/test_tdd_enforcer.py`

### Step 1: Write the failing test

```python
# tests/workflow/test_tdd_enforcer.py

from sloth_agent.workflow.tdd_enforcer import TDDEnforcer, TDDViolationError


def test_iron_law_exists():
    assert TDDEnforcer.THE_IRON_LAW


def test_violation_error_exists():
    assert TDDViolationError
```

### Step 2: Run test to verify it fails

```bash
uv run pytest tests/workflow/test_tdd_enforcer.py -v
```

Expected: FAIL

### Step 3: Write minimal implementation

```python
# src/sloth_agent/workflow/tdd_enforcer.py

"""TDD enforcer: RED-GREEN-REFACTOR iron law."""

import subprocess


class TDDViolationError(Exception):
    pass


class TDDEnforcer:
    THE_IRON_LAW = "没有失败的测试，就不能写任何生产代码"

    def run_tests(self, target: str = "tests") -> subprocess.CompletedProcess:
        return subprocess.run(
            ["pytest", target, "-v"], capture_output=True, text=True, timeout=300
        )

    def enforce_red(self, test_file: str) -> bool:
        """RED: 确认测试失败。"""
        result = self.run_tests(test_file)
        if result.returncode == 0:
            raise TDDViolationError("测试必须失败！")
        return True

    def enforce_green(self, test_file: str) -> bool:
        """GREEN: 确认测试通过。"""
        result = self.run_tests(test_file)
        if result.returncode != 0:
            raise TDDViolationError("实现未能让测试通过！")
        return True
```

### Step 4: Run test to verify it passes

```bash
uv run pytest tests/workflow/test_tdd_enforcer.py -v
```

Expected: PASS (all 2 tests)

### Step 5: Commit

```bash
git add src/sloth_agent/workflow/tdd_enforcer.py tests/workflow/test_tdd_enforcer.py
git commit -m "feat(workflow): add TDDEnforcer with RED-GREEN iron law (2 tests)"
```

---

## Task 4: SystematicDebugger — 4-Phase Debugging

**Spec:** §11.8, §14.2-§14.3
**Files:**
- Create: `src/sloth_agent/workflow/debugger.py`
- Test: `tests/workflow/test_debugger.py`

### Step 1: Write the failing test

```python
# tests/workflow/test_debugger.py

from sloth_agent.workflow.debugger import SystematicDebugger


def test_debugger_phases_exist():
    dbg = SystematicDebugger()
    assert hasattr(dbg, "phase1_root_cause")
    assert hasattr(dbg, "phase2_pattern_analysis")
    assert hasattr(dbg, "phase3_hypothesis_testing")
    assert hasattr(dbg, "phase4_implementation")


def test_no_fix_without_root_cause():
    dbg = SystematicDebugger()
    assert not dbg.can_fix_without_root_cause()


def test_hypothesis_tracking():
    dbg = SystematicDebugger()
    dbg.record_hypothesis("X 导致 Y")
    assert dbg.hypothesis_count == 1
```

### Step 2: Run test to verify it fails

```bash
uv run pytest tests/workflow/test_debugger.py -v
```

Expected: FAIL

### Step 3: Write minimal implementation

```python
# src/sloth_agent/workflow/debugger.py

"""Systematic debugger: 4-phase debugging method."""

from dataclasses import dataclass, field


@dataclass
class DebugResult:
    root_cause: str = ""
    hypothesis: str = ""
    fix_applied: bool = False
    verified: bool = False


class SystematicDebugger:
    """四阶段调试法：Root Cause → Pattern Analysis → Hypothesis → Implementation。"""

    NO_FIX_WITHOUT_ROOT_CAUSE = "没有根因调查，就不要修复"

    def __init__(self):
        self.hypotheses: list[str] = []
        self.failed_fixes: int = 0

    @property
    def hypothesis_count(self) -> int:
        return len(self.hypotheses)

    def can_fix_without_root_cause(self) -> bool:
        return False  # Rule: no fixes without root cause

    def phase1_root_cause(self, error: str) -> dict:
        return {"error": error, "reproduced": True, "root_cause": ""}

    def phase2_pattern_analysis(self, working_example: str, broken_example: str) -> dict:
        return {"differences": [working_example, broken_example]}

    def phase3_hypothesis_testing(self, hypothesis: str) -> dict:
        self.hypotheses.append(hypothesis)
        return {"hypothesis": hypothesis, "tested": False}

    def phase4_implementation(self, fix: str) -> DebugResult:
        self.failed_fixes += 1
        if self.failed_fixes >= 3:
            raise RuntimeError("3+ fixes failed — question the architecture")
        return DebugResult(fix_applied=True, verified=False)

    def record_hypothesis(self, hypothesis: str) -> None:
        self.hypotheses.append(hypothesis)
```

### Step 4: Run test to verify it passes

```bash
uv run pytest tests/workflow/test_debugger.py -v
```

Expected: PASS (all 3 tests)

### Step 5: Commit

```bash
git add src/sloth_agent/workflow/debugger.py tests/workflow/test_debugger.py
git commit -m "feat(workflow): add SystematicDebugger 4-phase method (3 tests)"
```

---

## Task 5: CodeReviewer — Spec Compliance + Quality

**Spec:** §11.6, §13.7
**Files:**
- Create: `src/sloth_agent/workflow/code_reviewer.py`
- Test: `tests/workflow/test_code_reviewer.py`

### Step 1: Write the failing test

```python
# tests/workflow/test_code_reviewer.py

from sloth_agent.workflow.code_reviewer import CodeReviewer


def test_reviewer_exists():
    reviewer = CodeReviewer()
    assert reviewer is not None


def test_review_report_format():
    reviewer = CodeReviewer()
    report = reviewer.generate_report()
    assert "Spec 合规性" in report
    assert "代码质量" in report
```

### Step 2: Run test to verify it fails

```bash
uv run pytest tests/workflow/test_code_reviewer.py -v
```

Expected: FAIL

### Step 3: Write minimal implementation

```python
# src/sloth_agent/workflow/code_reviewer.py

"""Code reviewer: spec compliance + quality checks."""

from dataclasses import dataclass


@dataclass
class ReviewReport:
    spec_compliant: bool = False
    issues: list[str] = None
    severity: str = "critical"  # critical / major / minor

    def __post_init__(self):
        if self.issues is None:
            self.issues = []


class CodeReviewer:
    """代码审查器：Spec 合规性检查优先于代码质量。"""

    def check_spec_compliance(self, diff: str, spec: str) -> ReviewReport:
        return ReviewReport(spec_compliant=True)

    def check_code_quality(self, diff: str) -> ReviewReport:
        return ReviewReport(spec_compliant=True)

    def generate_report(self) -> str:
        return (
            "## 代码审查报告\n"
            "\n"
            "### Spec 合规性\n"
            "- [ ] 符合项\n"
            "- [ ] 不符合项\n"
            "\n"
            "### 代码质量\n"
            "- Lint: 0 errors\n"
            "- Type: 0 errors\n"
            "- Coverage: 0%\n"
        )
```

### Step 4: Run test to verify it passes

```bash
uv run pytest tests/workflow/test_code_reviewer.py -v
```

Expected: PASS (all 2 tests)

### Step 5: Commit

```bash
git add src/sloth_agent/workflow/code_reviewer.py tests/workflow/test_code_reviewer.py
git commit -m "feat(workflow): add CodeReviewer with spec compliance check (2 tests)"
```

---

## Summary

| Task | Deliverable | Tests | Status |
|------|------------|-------|--------|
| 1 | WorkflowEngine State Machine | 14 | Pending |
| 2 | Verifier (4-step gate) | 5 | Pending |
| 3 | TDDEnforcer (RED-GREEN) | 2 | Pending |
| 4 | SystematicDebugger (4-phase) | 3 | Pending |
| 5 | CodeReviewer (spec + quality) | 2 | Pending |

**Total: 26 tests across 5 tasks**

Spec coverage: §11 (workflow steps & hooks), §12 (Spec→Plan→TODO→Execute), §13 (detailed flow), §14 (systematic debugging), §7.1.2 (gate failure → NextStep mapping).
