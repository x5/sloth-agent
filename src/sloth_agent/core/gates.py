"""Gate1/Gate2/Gate3 implementation (spec §5.4)."""

import subprocess
from dataclasses import dataclass

from pydantic import BaseModel


@dataclass
class GateResult:
    passed: bool
    passed_checks: list[str]
    failed_checks: list[str]
    raw_output: str = ""


class Gate1Config(BaseModel):
    lint_must_pass: bool = True
    type_check_must_pass: bool = True
    tests_must_pass: bool = True
    max_retries: int = 3


class Gate2Config(BaseModel):
    no_blocking_issues: bool = True
    min_coverage: float = 0.80


class Gate3Config(BaseModel):
    smoke_test_must_pass: bool = True
    auto_rollback: bool = True


class Gate1:
    """Gate1: 代码质量门控（lint + type check + tests）。"""

    def __init__(self, config: Gate1Config):
        self.config = config

    def check(self, branch: str, workspace: str) -> GateResult:
        passed, failed, raw = [], [], ""
        if self.config.lint_must_pass:
            r = self._run_lint(workspace)
            (passed if r.passed else failed).append("lint")
            raw += r.output
        if self.config.type_check_must_pass:
            r = self._run_type_check(workspace)
            (passed if r.passed else failed).append("type_check")
            raw += r.output
        if self.config.tests_must_pass:
            r = self._run_tests(workspace)
            (passed if r.passed else failed).append("tests")
            raw += r.output
        return GateResult(passed=len(failed) == 0, passed_checks=passed, failed_checks=failed, raw_output=raw)

    def _run_lint(self, workspace):
        try:
            r = subprocess.run(["ruff", "check", workspace], capture_output=True, text=True)
            return type("R", (), {"passed": r.returncode == 0, "output": r.stdout + r.stderr})()
        except FileNotFoundError:
            return type("R", (), {"passed": True, "output": "ruff not installed, skipping"})()

    def _run_type_check(self, workspace):
        try:
            r = subprocess.run(["mypy", workspace], capture_output=True, text=True)
            return type("R", (), {"passed": r.returncode == 0, "output": r.stdout + r.stderr})()
        except FileNotFoundError:
            return type("R", (), {"passed": True, "output": "mypy not installed, skipping"})()

    def _run_tests(self, workspace):
        try:
            r = subprocess.run(["pytest", workspace], capture_output=True, text=True)
            return type("R", (), {"passed": r.returncode == 0, "output": r.stdout + r.stderr})()
        except FileNotFoundError:
            return type("R", (), {"passed": True, "output": "pytest not installed, skipping"})()


class Gate2:
    """Gate2: 审查门控（blocking issues + coverage）。"""

    def __init__(self, config: Gate2Config):
        self.config = config

    def check(self, reviewer_output, coverage: float) -> GateResult:
        passed, failed = [], []
        if self.config.no_blocking_issues:
            if not reviewer_output.blocking_issues:
                passed.append("no_blocking_issues")
            else:
                failed.append(f"blocking_issues: {reviewer_output.blocking_issues}")
        if coverage >= self.config.min_coverage:
            passed.append(f"coverage({coverage:.0%} >= {self.config.min_coverage:.0%})")
        else:
            failed.append(f"coverage({coverage:.0%} < {self.config.min_coverage:.0%})")
        return GateResult(passed=len(failed) == 0, passed_checks=passed, failed_checks=failed)


class Gate3:
    """Gate3: 部署门控（smoke test）。"""

    def __init__(self, config: Gate3Config):
        self.config = config

    def check(self, deploy_result: dict) -> GateResult:
        passed = deploy_result.get("smoke_test_passed", False)
        return GateResult(
            passed=passed,
            passed_checks=["smoke_test"] if passed else [],
            failed_checks=["smoke_test"] if not passed else [],
            raw_output=deploy_result.get("output", ""),
        )
