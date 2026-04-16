"""Unit tests for tool data models."""

import pytest

from sloth_agent.core.tools.models import (
    Interruption,
    RejectedCall,
    RiskDecision,
    ToolCallRequest,
    ToolCategory,
    ToolExecutionRecord,
    ToolResult,
)


class TestToolCategory:
    def test_all_categories_exist(self):
        assert ToolCategory.READ.value == "read"
        assert ToolCategory.WRITE.value == "write"
        assert ToolCategory.EDIT.value == "edit"
        assert ToolCategory.EXECUTE.value == "execute"
        assert ToolCategory.SEARCH.value == "search"
        assert ToolCategory.VCS.value == "vcs"


class TestToolCallRequest:
    def test_defaults(self):
        req = ToolCallRequest(tool_name="read_file")
        assert req.tool_name == "read_file"
        assert req.params == {}
        assert req.source == "direct"
        assert req.confidence == 1.0

    def test_with_params(self):
        req = ToolCallRequest(
            tool_name="write_file",
            params={"path": "foo.py", "content": "hi"},
            source="llm",
            confidence=0.9,
        )
        assert req.params["path"] == "foo.py"
        assert req.source == "llm"
        assert req.confidence == 0.9

    def test_roundtrip(self):
        req = ToolCallRequest(tool_name="run_command", params={"cmd": "ls"})
        restored = ToolCallRequest.model_validate_json(req.model_dump_json())
        assert restored.tool_name == "run_command"
        assert restored.params == {"cmd": "ls"}


class TestToolResult:
    def test_success(self):
        r = ToolResult(success=True, output="hello", tool_name="read_file")
        assert r.success is True
        assert r.error is None

    def test_failure(self):
        r = ToolResult(success=False, error="not found", tool_name="read_file")
        assert r.success is False
        assert r.output == ""

    def test_roundtrip(self):
        r = ToolResult(success=True, output="data", duration_ms=42, retries=1)
        restored = ToolResult.model_validate_json(r.model_dump_json())
        assert restored.duration_ms == 42
        assert restored.retries == 1


class TestToolExecutionRecord:
    def test_basic(self):
        rec = ToolExecutionRecord(
            tool_name="read_file",
            request_params={"path": "x.py"},
            success=True,
        )
        assert rec.tool_name == "read_file"
        assert rec.approved_by is None
        assert rec.interruption_id is None

    def test_roundtrip(self):
        rec = ToolExecutionRecord(
            tool_name="write_file",
            request_params={"path": "out.txt"},
            success=True,
            output_summary="Written 100 bytes",
            duration_ms=5,
        )
        restored = ToolExecutionRecord.model_validate_json(rec.model_dump_json())
        assert restored.output_summary == "Written 100 bytes"


class TestRiskDecision:
    def test_approved(self):
        d = RiskDecision(approved=True, reason="auto-approved")
        assert d.requires_user_question is False

    def test_requires_question(self):
        d = RiskDecision(
            approved=False,
            reason="needs approval",
            requires_user_question=True,
            question="Execute tool?",
        )
        assert d.question == "Execute tool?"

    def test_roundtrip(self):
        d = RiskDecision(approved=True, reason="ok")
        restored = RiskDecision.model_validate_json(d.model_dump_json())
        assert restored.reason == "ok"


class TestInterruption:
    def test_defaults(self):
        i = Interruption(
            id="abc123",
            tool_name="run_command",
            request_params={"command": "deploy"},
            reason="high risk",
        )
        assert i.type == "tool_approval"
        assert i.id == "abc123"

    def test_roundtrip(self):
        i = Interruption(
            id="xyz",
            tool_name="read_file",
            request_params={"path": "secret.txt"},
            reason="outside workspace",
        )
        restored = Interruption.model_validate_json(i.model_dump_json())
        assert restored.tool_name == "read_file"


class TestRejectedCall:
    def test_basic(self):
        r = RejectedCall(reason="path not found", tool_name="read_file")
        assert r.reason == "path not found"

    def test_roundtrip(self):
        r = RejectedCall(reason="banned command", tool_name="run_command")
        restored = RejectedCall.model_validate_json(r.model_dump_json())
        assert restored.reason == "banned command"
