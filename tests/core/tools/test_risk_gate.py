"""Unit tests for RiskGate."""

from unittest.mock import MagicMock, patch

import pytest

from sloth_agent.core.config import Config
from sloth_agent.core.tools.hallucination_guard import HallucinationGuard
from sloth_agent.core.tools.models import RejectedCall, ToolCallRequest
from sloth_agent.core.tools.risk_gate import RiskGate
from sloth_agent.core.tools.tool_registry import (
    FileReadTool,
    BashTool,
    ToolRegistry,
)


@pytest.fixture
def registry():
    return ToolRegistry(Config())


@pytest.fixture
def guard(registry):
    return RiskGate(Config(), registry, HallucinationGuard())


def _call(name, params=None):
    return ToolCallRequest(tool_name=name, params=params or {})


class TestRiskGateAutoApprove:
    def test_low_risk_auto_approved(self, registry, tmp_path):
        """Low-risk tools should be auto-approved when HallucinationGuard passes."""
        f = tmp_path / "x"
        f.write_text("data")
        mock_guard = MagicMock()
        mock_guard.validate_tool_call.return_value = _call("read_file", {"path": str(f)})
        gate = RiskGate(Config(), registry, mock_guard)
        result = gate.evaluate(_call("read_file", {"path": str(f)}))
        assert result.approved is True

    def test_medium_risk_plan_approval_in_autonomous_window(self, registry, tmp_path):
        # write_file has permission=plan_approval, risk_level=2
        # In autonomous window, plan_approval should pass
        f = tmp_path / "x"
        f.write_text("data")
        mock_guard = MagicMock()
        mock_guard.validate_tool_call.return_value = _call(
            "write_file", {"path": str(f), "content": "y"}
        )
        config = Config()
        config.execution.auto_execute_hours = "00:00-23:59"
        gate = RiskGate(config, registry, mock_guard)
        result = gate.evaluate(
            _call("write_file", {"path": str(f), "content": "y"})
        )
        assert result.approved is True

    def test_medium_risk_plan_approval_outside_window(self, registry):
        # write_file has permission=plan_approval
        # Outside autonomous window, should require plan context
        mock_guard = MagicMock()
        mock_guard.validate_tool_call.return_value = _call("write_file", {"path": "x", "content": "y"})
        config = Config()
        config.execution.auto_execute_hours = "03:00-04:00"
        gate = RiskGate(config, registry, mock_guard)
        result = gate.evaluate(_call("write_file", {"path": "x", "content": "y"}))
        assert result.approved is False
        assert "plan_approval" in result.reason

    def test_high_risk_requires_approval(self, guard):
        # run_command has risk_level=3
        result = guard.evaluate(
            _call("run_command", {"command": "echo hi"})
        )
        assert result.approved is False
        assert result.requires_user_question is True

    def test_unknown_tool_rejected(self, guard):
        result = guard.evaluate(_call("nonexistent_tool"))
        assert result.approved is False
        assert "Unknown tool" in result.reason


class TestRiskGateHallucinationGuard:
    def test_hallucination_rejected(self, registry):
        """If HallucinationGuard rejects, RiskGate should reject too."""
        mock_guard = MagicMock()
        mock_guard.validate_tool_call.return_value = RejectedCall(
            reason="banned command", tool_name="run_command"
        )
        gate = RiskGate(Config(), registry, mock_guard)
        result = gate.evaluate(_call("run_command", {"command": "rm -rf /"}))
        assert result.approved is False
        assert "HallucinationGuard" in result.reason


class TestRiskGateAutonomousWindow:
    def test_autonomous_window_plan_approval_approved(self, registry):
        """During autonomous window, plan_approval tools should be approved."""
        config = Config()
        config.execution.auto_execute_hours = "00:00-23:59"
        mock_guard = MagicMock()
        mock_guard.validate_tool_call.return_value = _call(
            "write_file", {"path": "x", "content": "hi"}
        )
        gate = RiskGate(config, registry, mock_guard)
        result = gate.evaluate(_call("write_file", {"path": "x", "content": "hi"}))
        assert result.approved is True

    def test_autonomous_window_explicit_approval_still_denied(self, registry):
        """Even during autonomous window, explicit_approval tools require confirmation."""
        config = Config()
        config.execution.auto_execute_hours = "00:00-23:59"
        mock_guard = MagicMock()
        mock_guard.validate_tool_call.return_value = _call(
            "run_command", {"command": "echo hi"}
        )
        gate = RiskGate(config, registry, mock_guard)
        result = gate.evaluate(_call("run_command", {"command": "echo hi"}))
        assert result.approved is False
        assert "explicit_approval" in result.reason
