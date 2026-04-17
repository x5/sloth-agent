"""Tests for Gate1/2/3, phase_handoff, and gate failure mapping (plan Task 18)."""

from sloth_agent.core.gates import Gate1, Gate2, Gate3, Gate1Config, Gate2Config, Gate3Config, GateResult


class MockSubprocess:
    """Mock subprocess for gate checks."""
    def __init__(self, results: dict):
        self.results = results

    def run(self, cmd, **kwargs):
        result = self.results.get(cmd.split()[0], type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})())
        return result


def test_gate1_pass(tmp_path):
    config = Gate1Config()
    gate = Gate1(config)

    gate._run_lint = lambda w: type("R", (), {"passed": True, "output": ""})()
    gate._run_type_check = lambda w: type("R", (), {"passed": True, "output": ""})()
    gate._run_tests = lambda w: type("R", (), {"passed": True, "output": ""})()

    result = gate.check(tmp_path, str(tmp_path))
    assert result.passed is True
    assert result.failed_checks == []


def test_gate1_lint_fail(tmp_path):
    config = Gate1Config()
    gate = Gate1(config)
    gate._run_lint = lambda w: type("R", (), {"passed": False, "output": "lint error"})()
    gate._run_type_check = lambda w: type("R", (), {"passed": True, "output": ""})()
    gate._run_tests = lambda w: type("R", (), {"passed": True, "output": ""})()

    result = gate.check(tmp_path, str(tmp_path))
    assert result.passed is False
    assert "lint" in result.failed_checks


def test_gate1_type_check_fail(tmp_path):
    config = Gate1Config()
    gate = Gate1(config)
    gate._run_lint = lambda w: type("R", (), {"passed": True, "output": ""})()
    gate._run_type_check = lambda w: type("R", (), {"passed": False, "output": "type error"})()
    gate._run_tests = lambda w: type("R", (), {"passed": True, "output": ""})()

    result = gate.check(tmp_path, str(tmp_path))
    assert result.passed is False
    assert "type_check" in result.failed_checks


class _MockReviewerOutput:
    def __init__(self, blocking_issues, coverage):
        self.blocking_issues = blocking_issues
        self.coverage = coverage


def test_gate2_pass():
    config = Gate2Config()
    gate = Gate2(config)
    output = _MockReviewerOutput(blocking_issues=[], coverage=0.85)
    result = gate.check(output, coverage=0.85)
    assert result.passed is True


def test_gate2_blocking_issues():
    config = Gate2Config()
    gate = Gate2(config)
    output = _MockReviewerOutput(blocking_issues=["SQL injection"], coverage=0.90)
    result = gate.check(output, coverage=0.90)
    assert result.passed is False


def test_gate2_low_coverage():
    config = Gate2Config()
    gate = Gate2(config)
    output = _MockReviewerOutput(blocking_issues=[], coverage=0.50)
    result = gate.check(output, coverage=0.50)
    assert result.passed is False


def test_gate3_pass():
    config = Gate3Config()
    gate = Gate3(config)
    result = gate.check({"smoke_test_passed": True, "output": "ok"})
    assert result.passed is True


def test_gate3_fail():
    config = Gate3Config()
    gate = Gate3(config)
    result = gate.check({"smoke_test_passed": False, "output": "failed"})
    assert result.passed is False


def test_phase_handoff():
    from sloth_agent.core.runner import Runner, NextStep, RunState
    from sloth_agent.core.nextstep import NextStepType
    runner = Runner.__new__(Runner)
    state = RunState(run_id="test", current_agent="builder", current_phase="coding", turn=5)
    step = NextStep(type=NextStepType.phase_handoff, next_agent="reviewer", next_phase="review", output="handoff data")
    state = runner._handle_phase_handoff(state, step)
    assert state.current_agent == "reviewer"
    assert state.current_phase == "review"
    assert state.turn == 0
    assert state.handoff_payload == "handoff data"


def test_gate_failure_maps_to_retry_same():
    from sloth_agent.core.runner import Runner
    gate_result = GateResult(passed=False, passed_checks=[], failed_checks=["lint"], raw_output="error")
    step = Runner._gate_failure_to_nextstep(gate_result)
    assert step.type.value == "retry_same"


def test_gate_failure_maps_to_retry_different():
    from sloth_agent.core.runner import Runner
    gate_result = GateResult(passed=False, passed_checks=[], failed_checks=["blocking_issues"], raw_output="error")
    step = Runner._gate_failure_to_nextstep(gate_result)
    assert step.type.value == "retry_different"
