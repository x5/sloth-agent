"""Tests for AdaptiveTrigger wired into Runner."""

import pytest
from unittest.mock import patch, MagicMock

from sloth_agent.core.adaptive import AdaptiveTrigger, Replanner, TriggerReason


class TestAdaptiveTriggerWireIn:
    def test_runner_has_adaptive_trigger(self):
        from sloth_agent.core.config import Config
        from sloth_agent.core.runner import Runner

        runner = Runner(Config())
        assert runner.adaptive_trigger is not None
        assert runner.replanner is not None

    def test_gate_failure_records_to_adaptive(self):
        from sloth_agent.core.config import Config
        from sloth_agent.core.runner import Runner

        runner = Runner(Config())
        runner.adaptive_trigger.record_gate_failure("gate1")
        status = runner.adaptive_trigger.get_status()
        assert status["gate_failures"]["gate1"] == 1

    def test_replan_triggered_after_threshold(self):
        trigger = AdaptiveTrigger(gate_failure_threshold=2)
        trigger.record_gate_failure("gate1")
        assert not trigger.should_replan()  # Only 1 failure, threshold is 2
        trigger.record_gate_failure("gate1")
        assert trigger.should_replan()  # 2 failures >= threshold

    def test_max_replans_prevents_infinite_loop(self):
        trigger = AdaptiveTrigger(max_replans=2)
        trigger.record_gate_failure("gate1")
        trigger.record_gate_failure("gate1")
        assert trigger.should_replan()

        trigger.apply_replan()
        assert trigger.can_accept_replan()  # 1 < 2

        trigger.record_gate_failure("gate1")
        trigger.record_gate_failure("gate1")
        assert trigger.should_replan()

        trigger.apply_replan()
        assert not trigger.can_accept_replan()  # 2 >= 2
        assert not trigger.should_replan()  # Can't replan anymore

    def test_success_resets_consecutive_failures(self):
        trigger = AdaptiveTrigger(gate_failure_threshold=2)
        trigger.record_gate_failure("gate1")
        trigger.record_success()
        # Even though gate1 has 1 failure, consecutive is reset
        assert not trigger.should_replan()

    def test_replanner_generates_updated_plan(self):
        replanner = Replanner()
        original = "# Original Plan\n- Task 1\n- Task 2"
        result = replanner.replan(
            original,
            {"turn": 5, "phase": "running", "agent": "builder"},
            TriggerReason.GATE_FAILURE,
        )
        assert "Gate failure" in result.updated_plan or "Reduced scope" in result.updated_plan
        assert len(result.changed_sections) > 0
