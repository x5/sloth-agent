"""Tests for CLI run command (PE-4)."""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner


class TestRunCommand:
    """PE-4: CLI run command wiring."""

    def test_run_command_with_plan_file(self, tmp_path: Path):
        """run with a plan file should start pipeline."""
        from sloth_agent.cli.app import app

        # Create plan file
        plan = tmp_path / "plan.md"
        plan.write_text("# Task: Test\nA test task.\n")

        cli_runner = CliRunner()

        # Mock the runner to avoid needing actual LLM
        with patch("sloth_agent.core.runner.Runner.__init__", return_value=None):
            with patch("sloth_agent.core.runner.Runner.run") as mock_run:
                from sloth_agent.core.runner import RunState
                mock_run.return_value = RunState(
                    run_id="test", phase="completed", output="done"
                )
                result = cli_runner.invoke(app, ["run", str(plan)])

        # Should complete successfully
        assert "Sloth Agent" in result.output
        mock_run.assert_called_once()

    def test_run_command_with_nonexistent_plan(self):
        """run with nonexistent plan file should still start."""
        from sloth_agent.cli.app import app

        cli_runner = CliRunner()

        with patch("sloth_agent.core.runner.Runner.__init__", return_value=None):
            with patch("sloth_agent.core.runner.Runner.run") as mock_run:
                from sloth_agent.core.runner import RunState
                mock_run.return_value = RunState(
                    run_id="test", phase="completed", output="done"
                )
                result = cli_runner.invoke(app, ["run", "nonexistent.md"])

        # Should still start (plan_path will be None in metadata)
        assert "Sloth Agent" in result.output
