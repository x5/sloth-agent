"""Data models for the tool runtime layer.

Spec: tools-invocation-spec §3, §5.1
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ToolCategory(str, Enum):
    READ = "read"
    WRITE = "write"
    EDIT = "edit"
    EXECUTE = "execute"
    SEARCH = "search"
    VCS = "vcs"


class ToolCallRequest(BaseModel):
    tool_name: str
    params: dict[str, Any] = Field(default_factory=dict)
    source: str = "direct"  # "direct" | "keyword" | "llm"
    confidence: float = 1.0


class ToolResult(BaseModel):
    success: bool
    output: str = ""
    error: str | None = None
    duration_ms: int = 0
    retries: int = 0
    tool_name: str = ""


class ToolExecutionRecord(BaseModel):
    tool_name: str
    request_params: dict[str, Any] = Field(default_factory=dict)
    success: bool
    output_summary: str | None = None
    error: str | None = None
    duration_ms: int = 0
    approved_by: str | None = None
    interruption_id: str | None = None


class RiskDecision(BaseModel):
    approved: bool
    reason: str
    requires_user_question: bool = False
    question: str | None = None


class Interruption(BaseModel):
    id: str
    type: str = "tool_approval"
    tool_name: str
    request_params: dict[str, Any] = Field(default_factory=dict)
    reason: str


class RejectedCall(BaseModel):
    """Returned by HallucinationGuard when a call is rejected."""
    reason: str
    tool_name: str = ""
