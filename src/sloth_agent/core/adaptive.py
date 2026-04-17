"""Adaptive execution — detect plan deviations and trigger replanning."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("adaptive")


class TriggerReason(str, Enum):
    GATE_FAILURE = "gate_failure"
    CONTEXT_OVERFLOW = "context_overflow"
    PLAN_DEVIATION = "plan_deviation"
    STUCK_DETECTED = "stuck_detected"
    BUDGET_EXCEEDED = "budget_exceeded"


@dataclass
class PlanUpdate:
    """Result of a replanning operation."""

    original_plan: str
    updated_plan: str
    reason: TriggerReason
    changed_sections: list[str] = field(default_factory=list)
    confidence: float = 0.0  # 0.0-1.0, how confident we are in the update


@dataclass
class AdaptiveState:
    """Track adaptive execution state."""

    replan_count: int = 0
    max_replans: int = 3
    consecutive_failures: int = 0
    gate_failures: dict[str, int] = field(default_factory=dict)
    stuck_pattern: str | None = None


class AdaptiveTrigger:
    """Detect conditions that warrant replanning.

    Triggers:
    - Gate failure: same gate fails consecutively
    - Context overflow: context window exceeds budget
    - Plan deviation: current state diverges from plan assumptions
    - Stuck detected: repeated same errors
    - Budget exceeded: cost tracker signals hard limit
    """

    def __init__(self, max_replans: int = 3, gate_failure_threshold: int = 2):
        self.max_replans = max_replans
        self.gate_failure_threshold = gate_failure_threshold
        self.state = AdaptiveState(max_replans=max_replans)

    def should_replan(self) -> bool:
        """Check whether replanning is warranted."""
        if self.state.replan_count >= self.state.max_replans:
            return False

        # Same gate failed multiple times
        for gate, count in self.state.gate_failures.items():
            if count >= self.gate_failure_threshold:
                return True

        # Too many consecutive failures of any kind
        if self.state.consecutive_failures >= self.gate_failure_threshold:
            return True

        return False

    def record_gate_failure(self, gate_id: str) -> None:
        """Record a gate failure."""
        self.state.gate_failures[gate_id] = (
            self.state.gate_failures.get(gate_id, 0) + 1
        )
        self.state.consecutive_failures += 1
        logger.warning(
            f"Gate '{gate_id}' failed "
            f"(count={self.state.gate_failures[gate_id]}, "
            f"consecutive={self.state.consecutive_failures})"
        )

    def record_success(self) -> None:
        """Record a successful step."""
        self.state.consecutive_failures = 0

    def can_accept_replan(self) -> bool:
        """Check if we can still accept more replans."""
        return self.state.replan_count < self.state.max_replans

    def apply_replan(self) -> None:
        """Increment replan counter."""
        self.state.replan_count += 1
        logger.info(f"Replan #{self.state.replan_count} applied")

    def get_status(self) -> dict:
        """Get current adaptive state."""
        return {
            "replan_count": self.state.replan_count,
            "max_replans": self.state.max_replans,
            "consecutive_failures": self.state.consecutive_failures,
            "gate_failures": dict(self.state.gate_failures),
            "can_replan": self.can_accept_replan(),
        }


class Replanner:
    """Generate updated plans based on current execution state."""

    def replan(
        self,
        original_plan: str,
        current_state: dict,
        trigger: TriggerReason,
    ) -> PlanUpdate:
        """Generate an updated plan.

        In v0.2 this is rule-based. Future versions may use LLM-based
        replanning for more nuanced updates.
        """
        updated_plan = self._generate_updated_plan(
            original_plan, current_state, trigger
        )

        return PlanUpdate(
            original_plan=original_plan,
            updated_plan=updated_plan,
            reason=trigger,
            changed_sections=self._identify_changes(original_plan, updated_plan),
        )

    def _generate_updated_plan(
        self, original: str, state: dict, reason: TriggerReason
    ) -> str:
        """Rule-based plan update generation."""
        lines = original.strip().split("\n")

        match reason:
            case TriggerReason.GATE_FAILURE:
                lines.append(
                    "\n## Updated: Gate failure adaptation\n"
                    "- Reduced scope to core functionality only\n"
                    "- Added explicit testing checkpoints\n"
                    "- Simplified implementation approach"
                )
            case TriggerReason.CONTEXT_OVERFLOW:
                lines.append(
                    "\n## Updated: Context overflow mitigation\n"
                    "- Split large tasks into smaller, independent units\n"
                    "- Reduced context requirements per task"
                )
            case TriggerReason.STUCK_DETECTED:
                lines.append(
                    "\n## Updated: Stuck recovery\n"
                    "- Changed implementation strategy\n"
                    "- Added explicit verification steps"
                )
            case _:
                lines.append(
                    f"\n## Updated: {reason.value}\n"
                    "- Plan adjusted based on current execution state"
                )

        return "\n".join(lines)

    @staticmethod
    def _identify_changes(original: str, updated: str) -> list[str]:
        """Identify which sections were changed."""
        orig_lines = set(original.strip().split("\n"))
        updated_lines = set(updated.strip().split("\n"))
        return list(updated_lines - orig_lines)
