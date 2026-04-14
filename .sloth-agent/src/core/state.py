"""Core state definitions for the agent."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TaskState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEED = "succeed"
    FAILED = "failed"
    RETRYING = "retrying"
    WAITING_APPROVAL = "waiting_approval"


class ExecutionStep(BaseModel):
    step_id: str
    description: str
    state: TaskState
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: Any = None
    error: str | None = None
    tools_used: list[str] = Field(default_factory=list)


class ErrorContext(BaseModel):
    error_type: str
    error_message: str
    stack_trace: str | None = None
    occurred_at: datetime
    task_id: str
    recoverable: bool = False
    skill_suggestion: str | None = None


class TaskContext(BaseModel):
    task_id: str
    description: str
    state: TaskState = TaskState.PENDING
    retries: int = 0
    max_retries: int = 3
    tools_needed: list[str] = Field(default_factory=list)
    execution_log: list[ExecutionStep] = Field(default_factory=list)
    error_context: ErrorContext | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    checkpoint_id: str | None = None


class PlanContext(BaseModel):
    plan_id: str
    date: str  # YYYY-MM-DD
    tasks: list[TaskContext]
    approved: bool = False
    approved_at: datetime | None = None
    approver: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)


class ReportContext(BaseModel):
    report_id: str
    date: str
    plan_id: str
    tasks_summary: dict[str, Any]
    errors_encountered: list[ErrorContext] = Field(default_factory=list)
    skills_created: list[str] = Field(default_factory=list)
    skills_revised: list[str] = Field(default_factory=list)
    coverage_report: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=datetime.now)
