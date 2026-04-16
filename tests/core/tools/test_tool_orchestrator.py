"""Unit tests for ToolOrchestrator."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sloth_agent.core.config import Config
from sloth_agent.core.runner import RunState
from sloth_agent.core.tools.executor import Executor
from sloth_agent.core.tools.hallucination_guard import HallucinationGuard
from sloth_agent.core.tools.models import (
    Interruption,
    RiskDecision,
    ToolCallRequest,
    ToolResult,
)
from sloth_agent.core.tools.orchestrator import ToolOrchestrator
from sloth_agent.core.tools.risk_gate import RiskGate
from sloth_agent.core.tools.tool_registry import (
    FileReadTool,
    FileWriteTool,
    ToolRegistry,
)


@pytest.fixture
def registry():
    return ToolRegistry(Config())


@pytest.fixture
def orchestrator(registry):
    return ToolOrchestrator(Config(), registry)


def _call(name, params):
    return ToolCallRequest(tool_name=name, params=params)


def _state():
    return RunState(run_id="test", phase="running")


class TestToolOrchestratorSuccess:
    def test_execute_allowed_tool(self, orchestrator, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        state = _state()
        result = orchestrator.execute(state, _call("read_file", {"path": str(f)}))
        assert isinstance(result, ToolResult)
        assert result.success is True
        assert len(state.tool_history) == 1

    def test_write_file(self, tmp_path):
        """write_file has permission=plan_approval, so mock RiskGate to allow."""
        registry = ToolRegistry(Config())
        orch = ToolOrchestrator(Config(), registry)
        mock_gate = MagicMock()
        mock_gate.evaluate.return_value = RiskDecision(
            approved=True, reason="plan-approved"
        )
        orch.risk_gate = mock_gate

        state = _state()
        p = tmp_path / "out.txt"
        result = orch.execute(
            state, _call("write_file", {"path": str(p), "content": "data"})
        )
        assert isinstance(result, ToolResult)
        assert result.success is True


class TestToolOrchestratorInterruption:
    def test_risk_gate_denied_returns_interruption(self, registry, tmp_path):
        orch = ToolOrchestrator(Config(), registry)
        # Mock RiskGate to deny
        mock_gate = MagicMock()
        mock_gate.evaluate.return_value = RiskDecision(
            approved=False, reason="high risk needs approval"
        )
        orch.risk_gate = mock_gate

        state = _state()
        result = orch.execute(state, _call("run_command", {"command": "echo hi"}))
        assert isinstance(result, Interruption)
        assert len(state.pending_interruptions) == 1

    def test_interruption_has_correct_fields(self, registry):
        orch = ToolOrchestrator(Config(), registry)
        mock_gate = MagicMock()
        mock_gate.evaluate.return_value = RiskDecision(
            approved=False, reason="dangerous"
        )
        orch.risk_gate = mock_gate

        state = _state()
        result = orch.execute(state, _call("run_command", {"command": "rm -rf /"}))
        assert result.tool_name == "run_command"
        assert result.reason == "dangerous"


class TestToolOrchestratorResolveInterruption:
    def test_approved_interruption(self, registry, tmp_path):
        orch = ToolOrchestrator(Config(), registry)
        state = _state()

        # Create a pending interruption manually
        interruption = Interruption(
            id="test-123",
            tool_name="write_file",
            request_params={"path": str(tmp_path / "resolved.txt"), "content": "ok"},
            reason="was blocked",
        )
        state.pending_interruptions.append(interruption.model_dump())

        result = orch.resolve_interruption(state, "test-123", approved=True)
        assert result is not None
        assert result.success is True
        assert len(state.tool_history) == 1
        assert state.tool_history[0]["approved_by"] == "user"

    def test_denied_interruption(self, registry):
        orch = ToolOrchestrator(Config(), registry)
        state = _state()

        interruption = Interruption(
            id="test-456",
            tool_name="run_command",
            request_params={"command": "echo hi"},
            reason="blocked",
        )
        state.pending_interruptions.append(interruption.model_dump())

        result = orch.resolve_interruption(state, "test-456", approved=False)
        assert result is None
        assert len(state.tool_history) == 1
        assert state.tool_history[0]["error"] == "Denied by user"

    def test_unknown_interruption(self, registry):
        orch = ToolOrchestrator(Config(), registry)
        state = _state()
        result = orch.resolve_interruption(state, "nonexistent", approved=True)
        assert result is None
