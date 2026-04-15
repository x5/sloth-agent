"""Tests for CLI app entry point."""

from sloth_agent.cli.app import app


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
