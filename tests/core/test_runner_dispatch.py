"""Tests for Runner Agent Dispatch (PE-1) and Gate Wiring (PE-2)."""

from unittest.mock import MagicMock, patch
from pathlib import Path

import pytest

from sloth_agent.core.config import Config
from sloth_agent.core.nextstep import NextStep, NextStepType
from sloth_agent.core.runner import RunState, Runner


def _make_state(**kwargs) -> RunState:
    return RunState(run_id="test-run", **kwargs)


class TestRunnerThinkDispatch:
    """PE-1: think() dispatches to correct agent handler."""

    def test_dispatch_builder(self, tmp_path: Path):
        config = Config()
        runner = Runner(config)
        state = _make_state(current_agent="builder", current_phase="build")

        # Mock _think_builder to verify dispatch
        runner._think_builder = MagicMock(
            return_value=NextStep(type=NextStepType.final_output, output="done")
        )
        result = runner.think(state)
        runner._think_builder.assert_called_once_with(state)

    def test_dispatch_reviewer(self):
        config = Config()
        runner = Runner(config)
        state = _make_state(current_agent="reviewer", current_phase="review")

        runner._think_reviewer = MagicMock(
            return_value=NextStep(type=NextStepType.final_output, output="done")
        )
        result = runner.think(state)
        runner._think_reviewer.assert_called_once_with(state)

    def test_dispatch_deployer(self):
        config = Config()
        runner = Runner(config)
        state = _make_state(current_agent="deployer", current_phase="deploy")

        runner._think_deployer = MagicMock(
            return_value=NextStep(type=NextStepType.final_output, output="done")
        )
        result = runner.think(state)
        runner._think_deployer.assert_called_once_with(state)

    def test_dispatch_unknown_agent(self):
        config = Config()
        runner = Runner(config)
        state = _make_state(current_agent="unknown")

        result = runner.think(state)
        assert result.type == NextStepType.abort
        assert "Unknown agent" in (result.reason or "")

    def test_dispatch_none_agent(self):
        config = Config()
        runner = Runner(config)
        state = _make_state(current_agent=None)

        result = runner.think(state)
        assert result.type == NextStepType.abort


class TestThinkBuilder:
    """PE-1/PE-3: _think_builder parses plan and executes."""

    def test_no_plan_path_aborts(self):
        config = Config()
        runner = Runner(config)
        state = _make_state(current_agent="builder", metadata={})

        result = runner._think_builder(state)
        assert result.type == NextStepType.abort
        assert "No plan_path" in (result.reason or "")

    def test_builder_with_mock_plan(self, tmp_path: Path):
        """Builder should parse plan, call Builder.build_sync, return phase_handoff."""
        config = Config()
        runner = Runner(config)

        # Create a minimal plan file
        plan_file = tmp_path / "plan.md"
        plan_file.write_text("# Task: Add helper\nAdd a helper function.\n")

        state = _make_state(
            current_agent="builder",
            current_phase="build",
            metadata={"plan_path": str(plan_file)},
        )

        # Mock Builder.build_sync to return a valid output
        from sloth_agent.core.builder import BuilderOutput, CoverageReport

        mock_output = BuilderOutput(
            branch="main",
            changed_files=["src/helper.py"],
            diff_summary="Added helper",
            test_results=CoverageReport(total=0, passed=0, failed=0),
            coverage=0.0,
        )

        with patch("sloth_agent.core.builder.Builder.build_sync", return_value=mock_output):
            result = runner._think_builder(state)

        assert result.type == NextStepType.phase_handoff
        assert result.next_agent == "reviewer"
        assert result.next_phase == "review"
        assert "helper.py" in (result.output or "")
        # Check handoff payload was populated
        assert state.handoff_payload is not None
        assert state.handoff_payload["changed_files"] == ["src/helper.py"]


class TestThinkReviewer:
    """PE-1: _think_reviewer reviews builder output."""

    def test_reviewer_no_files_returns_retry(self):
        config = Config()
        runner = Runner(config)
        state = _make_state(
            current_agent="reviewer",
            current_phase="review",
            handoff_payload={"changed_files": []},
        )

        result = runner._think_reviewer(state)
        assert result.type == NextStepType.retry_different
        assert "No files to review" in (result.reason or "")

    def test_reviewer_approves_clean_code(self, tmp_path: Path):
        config = Config()
        runner = Runner(config)

        # Create a clean file
        clean_file = tmp_path / "clean.py"
        clean_file.write_text("def hello():\n    return 'world'\n")

        state = _make_state(
            current_agent="reviewer",
            current_phase="review",
            handoff_payload={
                "changed_files": [str(clean_file)],
                "branch": "main",
            },
        )

        result = runner._think_reviewer(state)
        assert result.type == NextStepType.phase_handoff
        assert result.next_agent == "deployer"

    def test_reviewer_rejects_eval(self, tmp_path: Path):
        config = Config()
        runner = Runner(config)

        # Create a file with eval (should be blocking)
        bad_file = tmp_path / "bad.py"
        bad_file.write_text("def run(code):\n    eval(code)\n")

        state = _make_state(
            current_agent="reviewer",
            current_phase="review",
            handoff_payload={
                "changed_files": [str(bad_file)],
                "branch": "main",
            },
        )

        result = runner._think_reviewer(state)
        assert result.type == NextStepType.retry_different
        assert "blocking" in (result.reason or "").lower()


class TestThinkDeployer:
    """PE-1: _think_deployer deploys and returns final or abort."""

    def test_deployer_no_scripts_returns_success(self, tmp_path: Path):
        config = Config()
        runner = Runner(config)
        state = _make_state(
            current_agent="deployer",
            current_phase="deploy",
            handoff_payload={"branch": "main"},
        )

        # Override _memory_dir to point to tmp_path
        runner._memory_dir = lambda: str(tmp_path / "memory")

        result = runner._think_deployer(state)
        assert result.type == NextStepType.final_output
        assert "Deployed" in (result.output or "")


class TestGateWiring:
    """PE-2: Gate checks after phase_handoff in run() loop."""

    def test_gate1_after_builder_handoff(self, tmp_path: Path):
        """Gate1 should run when builder hands off to reviewer."""
        config = Config()
        runner = Runner(config)

        state = _make_state(current_agent="builder", phase="running")
        state.metadata["plan_path"] = str(tmp_path / "plan.md")
        (tmp_path / "plan.md").write_text("# Task: simple\n\n")

        # Mock _check_gate_for_handoff to verify it's called
        runner._check_gate_for_handoff = MagicMock(
            return_value=type("GR", (), {"passed": True, "failed_checks": [], "passed_checks": [], "raw_output": ""})()
        )

        # Mock builder to return handoff
        from sloth_agent.core.builder import BuilderOutput, CoverageReport
        mock_output = BuilderOutput(
            branch="main",
            changed_files=[],
            diff_summary="",
            test_results=CoverageReport(),
            coverage=0.0,
        )
        runner._think_builder = MagicMock(
            return_value=NextStep(type=NextStepType.phase_handoff, next_agent="reviewer", next_phase="review")
        )
        runner._think_reviewer = MagicMock(
            return_value=NextStep(type=NextStepType.final_output, output="done")
        )

        runner.run(state)
        # Gate should have been called at least once (after builder handoff)
        assert runner._check_gate_for_handoff.call_count >= 1

    def test_gate_failure_triggers_retry(self, tmp_path: Path):
        """Gate failure should trigger retry_same from _gate_failure_to_nextstep."""
        config = Config()
        runner = Runner(config)
        state = _make_state(current_agent="builder", phase="running")

        # Gate returns failed with lint failure
        runner._check_gate_for_handoff = MagicMock(
            return_value=type("GR", (), {
                "passed": False,
                "failed_checks": ["lint"],
                "passed_checks": [],
                "raw_output": "",
            })()
        )

        call_count = 0

        def mock_think(state):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return NextStep(type=NextStepType.phase_handoff, next_agent="reviewer", next_phase="review")
            elif call_count <= 3:
                return NextStep(type=NextStepType.retry_same)
            return NextStep(type=NextStepType.abort, reason="too many retries")

        runner.think = mock_think
        final = runner.run(state)
        # Should have been called multiple times (handoff → gate fail → retry → retry → abort)
        assert call_count >= 3

    def test_gate2_after_reviewer_handoff(self, tmp_path: Path):
        """Gate2 runs when reviewer hands off to deployer."""
        config = Config()
        runner = Runner(config)
        state = _make_state(current_agent="reviewer", phase="running")

        gate_calls = []

        def mock_gate_check(state, step):
            gate_calls.append(step.next_agent)
            return type("GR", (), {"passed": True, "failed_checks": [], "passed_checks": [], "raw_output": ""})()

        runner._check_gate_for_handoff = mock_gate_check
        runner._think_reviewer = MagicMock(
            return_value=NextStep(type=NextStepType.phase_handoff, next_agent="deployer", next_phase="deploy")
        )
        runner._think_deployer = MagicMock(
            return_value=NextStep(type=NextStepType.final_output, output="deployed")
        )

        runner.run(state)
        assert "deployer" in gate_calls
