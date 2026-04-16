"""Unit tests for Executor."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sloth_agent.core.config import Config
from sloth_agent.core.tools.executor import Executor
from sloth_agent.core.tools.models import ToolCallRequest
from sloth_agent.core.tools.tool_registry import FileReadTool, FileWriteTool, ToolRegistry


@pytest.fixture
def registry():
    reg = ToolRegistry(Config())
    return reg


@pytest.fixture
def executor(registry):
    return Executor(registry, Config())


def _call(name, params):
    return ToolCallRequest(tool_name=name, params=params)


class TestExecutorSuccess:
    def test_read_file(self, executor, tmp_path):
        f = tmp_path / "hello.txt"
        f.write_text("world")
        result = executor.execute(_call("read_file", {"path": str(f)}))
        assert result.success is True
        assert result.output == "world"
        assert result.error is None

    def test_write_file(self, executor, tmp_path):
        p = tmp_path / "out.txt"
        result = executor.execute(
            _call("write_file", {"path": str(p), "content": "data"})
        )
        assert result.success is True
        assert p.read_text() == "data"


class TestExecutorFailure:
    def test_unknown_tool(self, executor):
        result = executor.execute(_call("nonexistent", {}))
        assert result.success is False
        assert "Unknown tool" in result.error

    def test_read_nonexistent_file(self, executor, tmp_path):
        result = executor.execute(
            _call("read_file", {"path": str(tmp_path / "missing.txt")})
        )
        assert result.success is False
        assert "No such file" in result.error or "cannot access" in result.error


class TestExecutorRetry:
    def test_retry_recorded_on_failure(self):
        """Tool with max_retries=1 should have retries=1 after failure."""
        reg = ToolRegistry(Config())
        exec_ = Executor(reg)
        result = exec_.execute(_call("read_file", {"path": "/nonexistent_file_xyz"}))
        assert result.success is False
        assert result.retries == 1  # FileReadTool has max_retries=1


class TestExecutorLogging:
    def test_log_file_created(self, tmp_path):
        """When config is provided, log file should be created."""
        reg = ToolRegistry(Config())
        exec_ = Executor(reg, Config())
        f = tmp_path / "log_test.txt"
        f.write_text("test")
        exec_.execute(_call("read_file", {"path": str(f)}))
        # Check if logs directory has tool-calls.jsonl
        log_path = Path(exec_._log_dir) / "tool-calls.jsonl"
        assert log_path.exists()
