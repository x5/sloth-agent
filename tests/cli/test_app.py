"""Tests for CLI app entry point."""

from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

from sloth_agent.cli.app import app
from sloth_agent.core.runner import RunState


def test_app_has_commands():
    """Verify all expected commands are registered."""
    command_names = [
        cmd.name or cmd.callback.__name__
        for cmd in app.registered_commands
    ]
    assert "run" in command_names
    assert "chat" in command_names
    assert "status" in command_names
    assert "skills" in command_names
    assert "scenarios" in command_names


def test_run_command_calls_pipeline(tmp_path):
    """Mock Runner, verify run command calls pipeline."""
    plan_file = tmp_path / "plan.md"
    plan_file.write_text("# Test Plan\n\nDo something.")

    mock_state = RunState(run_id="test-run", phase="completed", output="done")

    with patch("sloth_agent.core.config.load_config") as mock_load_config, \
         patch("sloth_agent.core.runner.Runner") as mock_runner_cls:
        mock_config = MagicMock()
        mock_load_config.return_value = mock_config

        mock_runner = MagicMock()
        mock_runner.run.return_value = mock_state
        mock_runner_cls.return_value = mock_runner

        runner = CliRunner()
        result = runner.invoke(app, ["run", str(plan_file)])

        assert result.exit_code == 0
        mock_runner.run.assert_called_once()
