"""RiskGate — evaluates whether a tool call should be approved.

Canonical spec: docs/specs/20260416-02-tools-invocation-spec.md §10.6
Invocation spec: 20260416-tools-invocation-spec.md §4.2
"""

from datetime import datetime

from sloth_agent.core.config import Config
from sloth_agent.core.tools.hallucination_guard import HallucinationGuard
from sloth_agent.core.tools.models import RiskDecision, ToolCallRequest
from sloth_agent.core.tools.tool_registry import ToolRegistry


class RiskGate:
    """Risk evaluation gate — dual-layer: permission + risk level."""

    def __init__(
        self,
        config: Config,
        registry: ToolRegistry,
        guard: HallucinationGuard | None = None,
    ):
        self.config = config
        self.registry = registry
        self.guard = guard or HallucinationGuard()

    def evaluate(self, request: ToolCallRequest) -> RiskDecision:
        """Evaluate whether a tool call should be approved.

        Layer 1: HallucinationGuard validation
        Layer 2: Permission-based check (tool.permission)
        Layer 3: Risk-level + runtime check (risk_level + autonomous window)
        """
        # Layer 1: HallucinationGuard
        validated = self.guard.validate_tool_call(request)
        if hasattr(validated, "reason") and hasattr(validated, "tool_name"):
            # It's a RejectedCall (has both reason AND tool_name from RejectedCall)
            # ToolCallRequest also has tool_name, but RejectedCall is the one with just reason+tool_name
            if not hasattr(validated, "params"):
                return RiskDecision(
                    approved=False, reason=f"HallucinationGuard: {validated.reason}"
                )

        # Get tool info
        tool = self.registry.get_tool(request.tool_name)
        if not tool:
            return RiskDecision(
                approved=False, reason=f"Unknown tool: {request.tool_name}"
            )

        # Layer 2: Permission-based check
        permission_decision = self._check_permission(tool)
        if permission_decision:
            return permission_decision

        # Layer 3: Risk-level + runtime check
        return self._check_risk_level(tool, request)

    def _check_permission(self, tool) -> RiskDecision | None:
        """Layer 2: Permission-based static policy check.

        Canonical spec: 20260416-02-tools-invocation-spec.md §10.6.2
        """
        match tool.permission:
            case "auto":
                return RiskDecision(
                    approved=True, reason=f"permission=auto"
                )
            case "plan_approval":
                # In autonomous/plan mode, allow. In interactive mode, require confirmation.
                if self._in_autonomous_window():
                    return RiskDecision(
                        approved=True, reason="permission=plan_approval, in autonomous window"
                    )
                return RiskDecision(
                    approved=False,
                    reason="permission=plan_approval requires plan context",
                    requires_user_question=True,
                    question=f"Execute {tool.name}? (requires plan approval)",
                )
            case "explicit_approval":
                # Always require explicit user confirmation
                return RiskDecision(
                    approved=False,
                    reason="permission=explicit_approval requires user confirmation",
                    requires_user_question=True,
                    question=f"Execute {tool.name}? (explicit approval required)",
                )
            case "high_risk":
                return RiskDecision(
                    approved=False,
                    reason="permission=high_risk requires additional review",
                    requires_user_question=True,
                    question=f"Execute {tool.name}? (HIGH RISK — additional review required)",
                )
            case _:
                return None

    def _check_risk_level(self, tool, request: ToolCallRequest) -> RiskDecision:
        """Layer 3: Risk-level + runtime dynamic check.

        Invocation spec: 20260416-tools-invocation-spec.md §4.2
        """
        auto_approve_level = self.config.chat.auto_approve_risk_level

        if tool.risk_level <= auto_approve_level:
            return RiskDecision(
                approved=True,
                reason=f"risk {tool.risk_level} <= auto-approve level {auto_approve_level}",
            )

        if self._in_autonomous_window():
            return RiskDecision(
                approved=True, reason="autonomous mode window"
            )

        return RiskDecision(
            approved=False,
            reason=f"risk level {tool.risk_level} requires approval",
            requires_user_question=True,
            question=f"Execute {tool.name}? (risk level {tool.risk_level})",
        )

    def _in_autonomous_window(self) -> bool:
        """Check if current time is within autonomous execution hours."""
        exec_cfg = self.config.execution
        return self._is_time_in_range(exec_cfg.auto_execute_hours)

    def _is_time_in_range(self, time_range: str) -> bool:
        """Parse 'HH:MM-HH:MM' and check if current time falls within."""
        try:
            start_str, end_str = time_range.split("-")
            start_h, start_m = map(int, start_str.split(":"))
            end_h, end_m = map(int, end_str.split(":"))
            now = datetime.now()
            current_minutes = now.hour * 60 + now.minute
            start_minutes = start_h * 60 + start_m
            end_minutes = end_h * 60 + end_m

            if start_minutes <= end_minutes:
                return start_minutes <= current_minutes <= end_minutes
            else:
                return current_minutes >= start_minutes or current_minutes <= end_minutes
        except (ValueError, AttributeError):
            return True
