"""E2E tests for Phase Execution Pipeline (PE-5).

Tests the full Builder→Reviewer→Deployer pipeline with mocked LLM.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sloth_agent.core.builder import BuilderOutput, CoverageReport
from sloth_agent.core.config import Config
from sloth_agent.core.nextstep import NextStep, NextStepType
from sloth_agent.core.runner import RunState, Runner


class TestE2EPipeline:
    """E2E: Full pipeline happy path."""

    def test_happy_path_builder_to_deployer(self, tmp_path: Path):
        """Plan → Builder → Gate1 pass → Reviewer → Gate2 pass → Deployer → Gate3 → final_output."""
        config = Config()
        runner = Runner(config)

        # Create plan file
        plan = tmp_path / "plan.md"
        plan.write_text("# Task: Add utility\nAdd a helper function.\n")

        # Create a clean generated file
        src = tmp_path / "src"
        src.mkdir()
        (src / "utils.py").write_text("def helper(): return 'ok'\n")

        state = RunState(
            run_id="e2e-1",
            current_agent="builder",
            current_phase="build",
            phase="running",
            metadata={"plan_path": str(plan)},
        )

        # Track phases visited
        phases_visited = []

        # Fully mock all three think methods to verify pipeline flow
        def mock_builder_think(state):
            phases_visited.append("builder")
            state.handoff_payload = {
                "branch": "main",
                "changed_files": ["src/utils.py"],
                "diff_summary": "Added utils",
            }
            return NextStep(
                type=NextStepType.phase_handoff,
                next_agent="reviewer",
                next_phase="review",
            )

        def mock_reviewer_think(state):
            phases_visited.append("reviewer")
            state.handoff_payload["review"] = {
                "approved": True,
                "blocking_issues": [],
            }
            return NextStep(
                type=NextStepType.phase_handoff,
                next_agent="deployer",
                next_phase="deploy",
            )

        def mock_deployer_think(state):
            phases_visited.append("deployer")
            return NextStep(
                type=NextStepType.final_output,
                output="Deployed successfully on branch main",
            )

        # Mock gates to always pass
        def mock_gate(state, step):
            return type("GR", (), {
                "passed": True,
                "failed_checks": [],
                "passed_checks": ["lint"],
                "raw_output": "",
            })()

        runner._think_builder = mock_builder_think
        runner._think_reviewer = mock_reviewer_think
        runner._think_deployer = mock_deployer_think
        runner._check_gate_for_handoff = mock_gate

        final = runner.run(state)

        assert final.phase == "completed", f"Got {final.phase}, errors: {final.errors}"
        assert "Deployed" in (final.output or "")
        assert phases_visited == ["builder", "reviewer", "deployer"]

    def test_gate1_fail_builder_retries(self, tmp_path: Path):
        """Builder fails lint → Gate1 fails → retry_same → Builder retries."""
        config = Config()
        runner = Runner(config)

        plan = tmp_path / "plan.md"
        plan.write_text("# Task: Bad code\n\n")

        state = RunState(
            run_id="e2e-2",
            current_agent="builder",
            current_phase="build",
            phase="running",
            metadata={"plan_path": str(plan)},
        )

        turn_count = 0

        def mock_think(state):
            nonlocal turn_count
            turn_count += 1

            if turn_count == 1:
                # First builder turn: return handoff (simulating completed work)
                return NextStep(
                    type=NextStepType.phase_handoff,
                    next_agent="reviewer",
                    next_phase="review",
                )
            elif turn_count <= 3:
                # After gate failure, retry
                return NextStep(type=NextStepType.retry_same)
            else:
                return NextStep(type=NextStepType.final_output, output="fixed")

        # Gate1 fails on first pass
        gate_pass_count = 0

        def mock_gate(state, step):
            nonlocal gate_pass_count
            gate_pass_count += 1
            # First gate check fails, second passes
            passed = gate_pass_count > 1
            return type("GR", (), {
                "passed": passed,
                "failed_checks": [] if passed else ["lint"],
                "passed_checks": ["lint"] if passed else [],
                "raw_output": "",
            })()

        runner.think = mock_think
        runner._check_gate_for_handoff = mock_gate

        final = runner.run(state)
        # After gate failure with retry_same, should eventually reach final_output
        assert final.phase == "completed"

    def test_gate2_fail_reviewer_blocking(self, tmp_path: Path):
        """Reviewer finds blocking issue → Gate2 fails → retry_different → back to builder."""
        config = Config()
        runner = Runner(config)

        state = RunState(
            run_id="e2e-3",
            current_agent="reviewer",
            current_phase="review",
            phase="running",
        )

        turn_count = 0

        def mock_think(state):
            nonlocal turn_count
            turn_count += 1

            if turn_count == 1:
                return NextStep(
                    type=NextStepType.phase_handoff,
                    next_agent="deployer",
                    next_phase="deploy",
                )
            elif turn_count == 2:
                # After gate failure → retry_different, think should abort or retry
                return NextStep(type=NextStepType.abort, reason="gate failure")
            return NextStep(type=NextStepType.final_output, output="done")

        # Gate2 fails (blocking issues)
        def mock_gate(state, step):
            return type("GR", (), {
                "passed": False,
                "failed_checks": ["blocking_issues"],
                "passed_checks": [],
                "raw_output": "",
            })()

        runner.think = mock_think
        runner._check_gate_for_handoff = mock_gate

        final = runner.run(state)
        assert final.phase == "aborted"

    def test_gate3_fail_deployer_aborts(self, tmp_path: Path):
        """Deployer smoke test fails → Gate3 fails → abort."""
        config = Config()
        runner = Runner(config)

        state = RunState(
            run_id="e2e-4",
            current_agent="deployer",
            current_phase="deploy",
            phase="running",
        )

        runner._think_deployer = MagicMock(
            return_value=NextStep(
                type=NextStepType.abort,
                reason="Deploy failed: script error",
            )
        )

        final = runner.run(state)
        assert final.phase == "aborted"
        assert "Deploy failed" in (final.errors[0] if final.errors else "")

    def test_state_persisted_during_run(self, tmp_path: Path):
        """Runner.persist() should write state.json during run."""
        config = Config()
        runner = Runner(config)

        state = RunState(
            run_id="persist-test",
            current_agent="builder",
            phase="running",
        )

        # One-turn run
        runner.think = lambda s: NextStep(type=NextStepType.final_output, output="done")
        final = runner.run(state)

        # Check state was persisted
        run_dir = Path(runner._memory_dir()) / "sessions" / "persist-test"
        assert (run_dir / "state.json").exists()
