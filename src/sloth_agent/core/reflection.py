"""Reflection mechanism and stuck detection (spec §5.1.2)."""

from pydantic import BaseModel
from typing import Literal


class Reflection(BaseModel):
    """Structured reflection output from reasoner model."""
    error_category: Literal["syntax", "logic", "dependency", "design", "plan", "environment"]
    root_cause: str
    learnings: list[str]
    action: Literal["retry_same", "retry_different", "replan", "abort"]
    retry_hint: str | None = None
    confidence: float


class StuckDetector:
    """Detect when the agent is stuck in a loop."""

    def __init__(self, window: list[Reflection] | None = None):
        self.window: list[Reflection] = window or []

    def record(self, reflection: Reflection) -> None:
        self.window.append(reflection)

    def reset(self) -> None:
        self.window.clear()

    def is_stuck(self) -> bool:
        if len(self.window) < 3:
            return False
        recent = self.window[-3:]

        # Rule 1: Same error category
        if all(r.error_category == recent[0].error_category for r in recent):
            if self._similarity(recent) > 0.8:
                return True

        # Rule 2: Three consecutive retry_same without success
        if all(r.action == "retry_same" for r in recent):
            return True

        # Rule 3: Declining confidence
        if all(recent[i].confidence < recent[i - 1].confidence for i in range(1, len(recent))):
            return True

        return False

    def get_unstuck_action(self) -> str:
        count = self._consecutive_stuck_count()
        if count <= 1:
            return "retry_different"
        elif count == 2:
            return "replan"
        else:
            return "abort"

    def _consecutive_stuck_count(self) -> int:
        count = 0
        for r in reversed(self.window):
            if r.action == "retry_same":
                count += 1
            else:
                break
        return min(count, 3)

    @staticmethod
    def _similarity(reflections: list[Reflection]) -> float:
        """Simple Jaccard-like similarity on root_cause words."""
        if len(reflections) < 2:
            return 1.0
        words_sets = [set(r.root_cause.lower().split()) for r in reflections]
        intersection = set.intersection(*words_sets)
        union = set.union(*words_sets)
        if not union:
            return 1.0
        return len(intersection) / len(union)
