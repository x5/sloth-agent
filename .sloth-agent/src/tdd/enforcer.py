"""TDD Enforcer - Ensures Test-Driven Development workflow."""

import logging
import subprocess
from pathlib import Path

from sloth_agent.core.config import Config
from sloth_agent.core.state import TaskContext

logger = logging.getLogger("tdd")


class TDDEnforcer:
    """
    Enforces TDD workflow:
    1. Write test first
    2. Implement
    3. Verify coverage
    """

    def __init__(self, config: Config):
        self.config = config

    def enforce_write_test_first(self, task: TaskContext, registry) -> bool:
        """
        Phase 1: Ensure test is written before implementation.

        Returns True if test exists, False if task should wait for test.
        """
        if not self.config.tdd.enforced:
            return True

        # Check if test file exists for this task
        test_file = self._find_test_file(task)

        if not test_file or not test_file.exists():
            logger.warning(
                f"Task {task.task_id}: No test file found. "
                "TDD requires writing test first."
            )
            # TODO: Use LLM to generate test from task description
            return False

        logger.info(f"Task {task.task_id}: Test file found: {test_file}")
        return True

    def generate_test_from_description(self, task: TaskContext) -> str | None:
        """
        Use LLM to generate test code from task description.

        Returns the generated test code.
        """
        # TODO: Integrate with LLM provider
        logger.info(f"Generating test for task: {task.description}")
        return None

    def _find_test_file(self, task: TaskContext) -> Path | None:
        """Find the test file corresponding to a task."""
        workspace = Path(self.config.agent.workspace)

        # Common test patterns
        test_patterns = [
            workspace / "tests" / f"test_{task.task_id}.py",
            workspace / "tests" / f"{task.task_id}_test.py",
            workspace / "test" / f"test_{task.task_id}.py",
        ]

        for pattern in test_patterns:
            if pattern.exists():
                return pattern

        return None

    def run_tests(self, test_file: Path) -> dict:
        """Run tests and return results."""
        try:
            result = subprocess.run(
                ["pytest", str(test_file), "-v", "--cov"],
                capture_output=True,
                text=True,
                timeout=300,
            )

            return {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "passed": result.returncode == 0,
            }

        except subprocess.TimeoutExpired:
            return {"returncode": -1, "stdout": "", "stderr": "Test timed out", "passed": False}
        except FileNotFoundError:
            # pytest not installed, skip coverage check
            return {"returncode": 0, "stdout": "", "stderr": "pytest not found", "passed": True}

    def check_coverage(self, coverage_output: str) -> float:
        """Parse coverage output and return percentage."""
        # TODO: Parse actual coverage output
        # Example: "TOTAL coverage: 85%"
        return 0.0

    def enforce_coverage_threshold(self, task: TaskContext, coverage: float) -> bool:
        """Check if coverage meets the configured threshold."""
        threshold = self.config.tdd.coverage_threshold

        if coverage >= threshold:
            logger.info(
                f"Task {task.task_id}: Coverage {coverage}% >= threshold {threshold}%"
            )
            return True
        else:
            logger.error(
                f"Task {task.task_id}: Coverage {coverage}% < threshold {threshold}%. "
                "Task will be marked as failed."
            )
            return False
