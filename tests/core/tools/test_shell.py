"""Unit tests for shell execution tool."""

import pytest

from sloth_agent.core.tools.builtin.shell import RunCommandTool


class TestRunCommandTool:
    def test_successful_command(self):
        tool = RunCommandTool()
        result = tool.execute(command="echo hello")
        assert result["returncode"] == 0
        assert "hello" in result["stdout"]

    def test_command_with_stderr(self):
        tool = RunCommandTool()
        result = tool.execute(command="echo error >&2")
        assert "error" in result["stderr"]

    def test_failing_command(self):
        tool = RunCommandTool()
        result = tool.execute(command="exit 1")
        assert result["returncode"] == 1

    def test_timeout(self):
        tool = RunCommandTool()
        result = tool.execute(command="sleep 10", timeout=1)
        assert result["returncode"] == -1
        assert "timed out" in result["stderr"]

    def test_metadata(self):
        tool = RunCommandTool()
        assert tool.category.value == "execute"
        assert tool.risk_level == 3

    def test_schema(self):
        tool = RunCommandTool()
        schema = tool.get_schema()
        assert schema["name"] == "run_command"
        assert "command" in schema["parameters"]["properties"]
