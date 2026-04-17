"""Tests for AdaptiveTrigger and Replanner."""

import pytest

from sloth_agent.core.adaptive import (
    AdaptiveTrigger,
    AdaptiveState,
    PlanUpdate,
    Replanner,
    TriggerReason,
)


class TestAdaptiveTrigger:
    def test_starts_with_no_replans(self):
        trigger = AdaptiveTrigger()
        assert trigger.state.replan_count == 0
        assert trigger.can_accept_replan()

    def test_should_replan_false_initially(self):
        trigger = AdaptiveTrigger()
        assert not trigger.should_replan()

    def test_gate_failure_triggers_replan(self):
        trigger = AdaptiveTrigger(gate_failure_threshold=2)
        trigger.record_gate_failure("gate1")
        trigger.record_gate_failure("gate1")
        assert trigger.should_replan()

    def test_consecutive_failures_trigger_replan(self):
        trigger = AdaptiveTrigger(gate_failure_threshold=3)
        trigger.record_gate_failure("gate1")
        trigger.record_gate_failure("gate2")
        trigger.record_gate_failure("gate3")
        assert trigger.should_replan()

    def test_max_replans_blocks_further(self):
        trigger = AdaptiveTrigger(max_replans=1)
        trigger.record_gate_failure("gate1")
        trigger.record_gate_failure("gate1")
        assert trigger.should_replan()
        trigger.apply_replan()
        assert not trigger.should_replan()  # Hit max

    def test_success_resets_consecutive(self):
        trigger = AdaptiveTrigger(gate_failure_threshold=3)
        trigger.record_gate_failure("gate1")
        trigger.record_gate_failure("gate2")
        trigger.record_success()
        trigger.record_gate_failure("gate3")
        # After success reset, only 1 consecutive failure
        assert not trigger.should_replan()

    def test_get_status(self):
        trigger = AdaptiveTrigger()
        trigger.record_gate_failure("gate1")
        status = trigger.get_status()
        assert status["replan_count"] == 0
        assert status["consecutive_failures"] == 1
        assert "gate1" in status["gate_failures"]
        assert status["can_replan"] is True

    def test_apply_replan_increments(self):
        trigger = AdaptiveTrigger()
        trigger.apply_replan()
        assert trigger.state.replan_count == 1


class TestReplanner:
    def test_replan_returns_plan_update(self):
        replanner = Replanner()
        result = replanner.replan(
            original_plan="# My Plan\n## Tasks\n- Task 1",
            current_state={"phase": "coding"},
            trigger=TriggerReason.GATE_FAILURE,
        )
        assert isinstance(result, PlanUpdate)
        assert result.reason == TriggerReason.GATE_FAILURE
        assert len(result.changed_sections) > 0

    def test_gate_failure_adds_adaptation_section(self):
        replanner = Replanner()
        result = replanner.replan(
            original_plan="# Plan\n## Goal\nBuild something",
            current_state={},
            trigger=TriggerReason.GATE_FAILURE,
        )
        assert "Gate failure adaptation" in result.updated_plan
        assert "Reduced scope" in result.updated_plan

    def test_context_overflow_adds_mitigation(self):
        replanner = Replanner()
        result = replanner.replan(
            original_plan="# Plan",
            current_state={},
            trigger=TriggerReason.CONTEXT_OVERFLOW,
        )
        assert "Context overflow mitigation" in result.updated_plan

    def test_stuck_detected_adds_recovery(self):
        replanner = Replanner()
        result = replanner.replan(
            original_plan="# Plan",
            current_state={},
            trigger=TriggerReason.STUCK_DETECTED,
        )
        assert "Stuck recovery" in result.updated_plan

    def test_budget_exceeded_adds_generic(self):
        replanner = Replanner()
        result = replanner.replan(
            original_plan="# Plan",
            current_state={},
            trigger=TriggerReason.BUDGET_EXCEEDED,
        )
        assert "budget_exceeded" in result.updated_plan

    def test_identify_changes(self):
        original = "# Plan\n## Task 1\n- Do A"
        updated = "# Plan\n## Task 1\n- Do A\n## New\n- Do B"
        changes = Replanner._identify_changes(original, updated)
        assert any("New" in c for c in changes)


class TestPlanUpdate:
    def test_default_values(self):
        pu = PlanUpdate(
            original_plan="old",
            updated_plan="new",
            reason=TriggerReason.GATE_FAILURE,
        )
        assert pu.changed_sections == []
        assert pu.confidence == 0.0


class TestTriggerReason:
    def test_all_reasons_exist(self):
        reasons = [
            TriggerReason.GATE_FAILURE,
            TriggerReason.CONTEXT_OVERFLOW,
            TriggerReason.PLAN_DEVIATION,
            TriggerReason.STUCK_DETECTED,
            TriggerReason.BUDGET_EXCEEDED,
        ]
        assert len(reasons) == 5
