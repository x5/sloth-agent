"""ToolOrchestrator — chains RiskGate -> Executor -> ResultFormatter -> RunState.

Spec: tools-invocation-spec §5
"""

import uuid
from typing import Any

from sloth_agent.core.config import Config
from sloth_agent.core.tools.executor import Executor
from sloth_agent.core.tools.formatter import ResultFormatter
from sloth_agent.core.tools.hallucination_guard import HallucinationGuard
from sloth_agent.core.tools.models import (
    Interruption,
    ToolCallRequest,
    ToolExecutionRecord,
    ToolResult,
)
from sloth_agent.core.tools.risk_gate import RiskGate
from sloth_agent.core.tools.tool_registry import ToolRegistry


class ToolOrchestrator:
    """Orchestrates tool execution with risk gating, execution, and formatting."""

    def __init__(
        self,
        config: Config,
        registry: ToolRegistry,
        llm_provider: Any = None,
    ):
        self.config = config
        self.llm_provider = llm_provider
        self.registry = registry
        self.risk_gate = RiskGate(config, registry, HallucinationGuard())
        self.executor = Executor(registry, config)
        self.formatter = ResultFormatter()

    def execute(self, state, request: ToolCallRequest) -> ToolResult | Interruption:
        """Execute a tool call through the full pipeline.

        Args:
            state: RunState instance to update with tool history
            request: ToolCallRequest to execute
        """
        from sloth_agent.core.runner import RunState

        # 1. Risk gate evaluation
        decision = self.risk_gate.evaluate(request)

        if not decision.approved:
            interruption = Interruption(
                id=uuid.uuid4().hex[:12],
                tool_name=request.tool_name,
                request_params=request.params,
                reason=decision.reason,
            )
            state.pending_interruptions.append(interruption.model_dump())
            return interruption

        # 2. Execute
        result = self.executor.execute(request)

        # 3. Write back to RunState
        record = ToolExecutionRecord(
            tool_name=request.tool_name,
            request_params=request.params,
            success=result.success,
            output_summary=result.output[:200] if result.output else None,
            error=result.error,
            duration_ms=result.duration_ms,
        )

        # Append structured record if state has tool_history
        if hasattr(state, "tool_history"):
            state.tool_history.append(record.model_dump())

        return result

    def resolve_interruption(
        self, state, interruption_id: str, approved: bool
    ) -> ToolResult | None:
        """Resolve a pending interruption.

        Args:
            state: RunState with pending_interruptions
            interruption_id: ID of the interruption to resolve
            approved: Whether the user approved the tool call
        """
        # Find and remove the interruption
        idx = None
        for i, interruption_data in enumerate(state.pending_interruptions):
            if interruption_data.get("id") == interruption_id:
                idx = i
                break

        if idx is None:
            return None

        interruption_data = state.pending_interruptions.pop(idx)

        if approved:
            request = ToolCallRequest(
                tool_name=interruption_data["tool_name"],
                params=interruption_data.get("request_params", {}),
            )
            result = self.executor.execute(request)

            record = ToolExecutionRecord(
                tool_name=request.tool_name,
                request_params=request.params,
                success=result.success,
                output_summary=result.output[:200] if result.output else None,
                error=result.error,
                duration_ms=result.duration_ms,
                approved_by="user",
            )
            state.tool_history.append(record.model_dump())
            return result
        else:
            record = ToolExecutionRecord(
                tool_name=interruption_data["tool_name"],
                request_params=interruption_data.get("request_params", {}),
                success=False,
                error="Denied by user",
                approved_by="user",
            )
            state.tool_history.append(record.model_dump())
            return None
