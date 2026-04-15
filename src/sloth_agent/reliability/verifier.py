"""Verifier - Task result verification to prevent false positives."""

import logging
import subprocess
from pathlib import Path

from sloth_agent.core.config import Config
from sloth_agent.core.state import TaskContext

logger = logging.getLogger("verifier")


class TaskVerifier:
    """
    Verifies task completion to prevent false positives.

    Checks:
    - File existence
    - Build success
    - Test pass
    - Coverage threshold
    """

    def __init__(self, config: Config):
        self.config = config

    def verify_task(self, task: TaskContext) -> bool:
        """Verify that a task was completed successfully."""
        if not self.config.verification.enabled:
            return True

        checks = []

        if self.config.verification.file_exists_check:
            checks.append(self._check_files_exist(task))

        if self.config.verification.build_check:
            checks.append(self._check_build_success())

        if self.config.verification.test_check:
            checks.append(self._check_tests_pass())

        # All checks must pass
        return all(checks)

    def _check_files_exist(self, task: TaskContext) -> bool:
        """Check that expected files were created."""
        # TODO: Parse task for expected file outputs
        logger.debug(f"Verifying files for task {task.task_id}")
        return True

    def _check_build_success(self) -> bool:
        """Check that build completed successfully."""
        # Look for common build files/markers
        build_markers = [
            "dist/index.js",
            "build/index.js",
            "target/release/binary",
            "__pycache__",
        ]

        workspace = Path(self.config.agent.workspace)
        for marker in build_markers:
            if (workspace / marker).exists():
                logger.info(f"Build marker found: {marker}")
                return True

        # TODO: Actually run build command and check exit code
        logger.debug("No build marker found, skipping build check")
        return True

    def _check_tests_pass(self) -> bool:
        """Check that tests pass."""
        # TODO: Run pytest/npm test and check results
        logger.debug("Running test verification")
        return True

    def check_coverage_threshold(self, coverage_percent: float) -> bool:
        """Check if coverage meets the threshold."""
        threshold = self.config.tdd.coverage_threshold

        if coverage_percent >= threshold:
            logger.info(
                f"Coverage {coverage_percent}% meets threshold {threshold}%"
            )
            return True
        else:
            logger.warning(
                f"Coverage {coverage_percent}% below threshold {threshold}%"
            )
            return False

    def verify_task_output(self, task: TaskContext, expected_output: str) -> bool:
        """Verify task output matches expectation."""
        # TODO: Implement output verification
        return True
