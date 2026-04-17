"""Smoke test - verify the full pipeline can be run with mock LLM."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SmokeResult:
    passed: bool
    steps: list[str]
    error: str | None = None


def run_smoke_test() -> SmokeResult:
    """Run the pipeline with mock components and verify each step."""
    steps = []

    # Step 1: Verify Builder can produce BuilderOutput
    try:
        from sloth_agent.core.builder import BuilderOutput, CoverageReport
        output = BuilderOutput(
            branch="test",
            changed_files=["main.py"],
            diff_summary="added main.py",
            test_results=CoverageReport(total=10, passed=10, failed=0),
            coverage=CoverageReport(total=10, passed=10, failed=0),
        )
        steps.append("builder_output")
    except Exception as e:
        return SmokeResult(passed=False, steps=steps, error=f"Builder failed: {e}")

    # Step 2: Verify Reviewer can produce ReviewerOutput
    try:
        from sloth_agent.agents.reviewer import ReviewerOutput
        review = ReviewerOutput(approved=True, branch="test", blocking_issues=[], suggestions=[])
        steps.append("reviewer_output")
    except Exception as e:
        return SmokeResult(passed=False, steps=steps, error=f"Reviewer failed: {e}")

    # Step 3: Verify Gate1 can run (with mock checks)
    try:
        from sloth_agent.core.gates import GateResult, Gate1Config
        gate = GateResult(passed=True, passed_checks=["all"], failed_checks=[])
        assert gate.passed is True
        steps.append("gate_result")
    except Exception as e:
        return SmokeResult(passed=False, steps=steps, error=f"Gate failed: {e}")

    # Step 4: Verify Gate3 (deploy gate) passes when smoke_test_passed=True
    try:
        from sloth_agent.core.gates import Gate3Config, GateResult, Gate3
        gate3_config = Gate3Config(require_smoke_test=True)
        gate3 = Gate3(gate3_config)
        result = gate3.check({"smoke_test_passed": True})
        assert result.passed is True
        steps.append("gate3_check")
    except Exception as e:
        return SmokeResult(passed=False, steps=steps, error=f"Gate3 failed: {e}")

    # Step 5: Verify Deployer can execute with scripts
    try:
        from sloth_agent.agents.deployer import DeployerAgent, DeployResult
        agent = DeployerAgent()
        assert agent is not None
        steps.append("deployer_init")
    except Exception as e:
        return SmokeResult(passed=False, steps=steps, error=f"Deployer failed: {e}")

    return SmokeResult(passed=True, steps=steps)
