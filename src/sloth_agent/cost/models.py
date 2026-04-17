"""Data models for cost tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CostRecord:
    """One LLM call's cost record."""

    timestamp: float
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float
    scenario_id: str | None = None
    phase_id: str | None = None
    agent_id: str | None = None
    run_id: str | None = None
    call_id: str = ""


@dataclass
class BudgetStatus:
    """Result of a budget check."""

    scope: str  # "daily" | "scenario"
    limit: float
    used: float
    remaining: float
    used_percent: float
    status: str  # "ok" | "soft_limit_reached" | "hard_exceeded"
    action: str  # "continue" | "degrade" | "stop_all"


@dataclass
class CostBreakdown:
    """Aggregated cost view."""

    total: float
    by_provider: dict[str, float] = field(default_factory=dict)
    by_scenario: dict[str, float] = field(default_factory=dict)
    by_model: dict[str, float] = field(default_factory=dict)
    total_tokens: int = 0
    total_calls: int = 0
