"""NextStep protocol for unified runtime semantics (spec §5.1.1.2)."""

from enum import Enum

from pydantic import BaseModel, Field
from typing import Any, Literal


class NextStepType(str, Enum):
    final_output = "final_output"
    tool_call = "tool_call"
    phase_handoff = "phase_handoff"
    retry_same = "retry_same"
    retry_different = "retry_different"
    replan = "replan"
    interruption = "interruption"
    abort = "abort"


class ToolRequest(BaseModel):
    """Tool call request."""
    tool_name: str
    params: dict[str, Any] = Field(default_factory=dict)


class NextStep(BaseModel):
    """Unified runtime step protocol.

    All runtime events (reflection, gate, approval, phase transition)
    map to one of these step types.
    """
    type: NextStepType
    output: str | None = None
    request: ToolRequest | None = None
    next_agent: str | None = None
    next_phase: str | None = None
    reason: str | None = None
