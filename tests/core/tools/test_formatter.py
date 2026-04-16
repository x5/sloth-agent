"""Unit tests for ResultFormatter."""

from sloth_agent.core.tools.formatter import ResultFormatter
from sloth_agent.core.tools.models import ToolResult


class TestResultFormatter:
    def setup_method(self):
        self.fmt = ResultFormatter()

    def test_for_human_success(self):
        r = ToolResult(success=True, output="hello", tool_name="read_file", duration_ms=10)
        out = self.fmt.for_human(r)
        assert "OK" in out
        assert "read_file" in out
        assert "hello" in out

    def test_for_human_fail(self):
        r = ToolResult(success=False, error="not found", tool_name="read_file")
        out = self.fmt.for_human(r)
        assert "FAIL" in out
        assert "not found" in out

    def test_for_human_truncates_long_output(self):
        r = ToolResult(success=True, output="x" * 10000, tool_name="read_file")
        out = self.fmt.for_human(r)
        assert "more chars" in out

    def test_for_llm_success(self):
        r = ToolResult(success=True, output="data", tool_name="read_file")
        out = self.fmt.for_llm(r)
        assert "succeeded" in out
        assert "read_file" in out

    def test_for_llm_fail(self):
        r = ToolResult(success=False, error="error", tool_name="read_file")
        out = self.fmt.for_llm(r)
        assert "failed" in out

    def test_for_llm_truncates(self):
        r = ToolResult(success=True, output="x" * 5000, tool_name="read_file")
        out = self.fmt.for_llm(r)
        assert "truncated" in out

    def test_for_log_success(self):
        r = ToolResult(success=True, tool_name="read_file", duration_ms=42, retries=1)
        out = self.fmt.for_log(r)
        assert "OK" in out
        assert "duration=42ms" in out
        assert "retries=1" in out

    def test_for_log_fail(self):
        r = ToolResult(success=False, tool_name="read_file", error="fail")
        out = self.fmt.for_log(r)
        assert "FAIL" in out
        assert "error=fail" in out
