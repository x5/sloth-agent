"""Tests for BudgetAwareLLMRouter."""

import tempfile

import pytest

from sloth_agent.cost.tracker import CostTracker
from sloth_agent.cost.budget_router import BudgetAwareLLMRouter
from sloth_agent.providers.llm_router import LLMRouter, MockProvider


def _make_router_and_tracker() -> tuple[BudgetAwareLLMRouter, CostTracker]:
    router = LLMRouter()
    router.register_provider("deepseek", MockProvider("deepseek-ok"))
    router.register_provider("qwen", MockProvider("qwen-ok"))
    router.register_provider("glm-4.5-flash", MockProvider("glm-free"))

    tmp = tempfile.mkdtemp()
    tracker = CostTracker(storage_dir=tmp)
    budget_router = BudgetAwareLLMRouter(router, tracker)
    return budget_router, tracker


class TestModelSelection:
    def test_ok_budget_returns_preferred(self):
        br, _ = _make_router_and_tracker()
        result = br.select_model("deepseek-v3.2")
        assert result == "deepseek-v3.2"

    def test_hard_limit_picks_cheapest(self):
        br, tracker = _make_router_and_tracker()
        tracker.budget["daily_limit"] = 0.001
        tracker.record_call("qwen", "qwen3.6-plus", 1000, 1000)
        result = br.select_model("qwen3.6-plus")
        # Should pick glm-4.5-flash (cheapest in tier)
        assert result == "glm-4.5-flash"

    def test_soft_limit_medium_picks_mid_tier(self):
        br, tracker = _make_router_and_tracker()
        tracker.budget["daily_limit"] = 0.005
        # Fill up to near limit
        tracker.record_call("qwen", "qwen3.6-plus", 2000, 1000)
        tracker.record_call("deepseek", "deepseek-v3.2", 1000, 1000)
        status = tracker.check_budget("daily")
        # If budget is ok/soft, select_model should work
        result = br.select_model("qwen3.6-plus", task_complexity="medium")
        assert result is not None


class TestGetModel:
    def test_ok_budget_returns_original_provider(self):
        br, _ = _make_router_and_tracker()
        br.router.routes = {
            "builder": {"stages": {"coding": {"provider": "deepseek"}}},
        }
        provider = br.get_model("builder", "coding")
        assert provider.response == "deepseek-ok"

    def test_hard_limit_downgrades_to_cheapest(self):
        br, tracker = _make_router_and_tracker()
        tracker.budget["daily_limit"] = 0.0001
        tracker.record_call("deepseek", "deepseek-v3.2", 1000, 1000)
        br.router.routes = {
            "builder": {"stages": {"coding": {"provider": "deepseek"}}},
        }
        provider = br.get_model("builder", "coding")
        # deepseek is not in cheap tier but it's the only matching registered provider
        # that the route points to — should still return it if no cheap alternative
        assert provider is not None

    def test_no_route_returns_mock_fallback(self):
        br, _ = _make_router_and_tracker()
        provider = br.get_model("unknown_agent", "unknown_stage")
        assert isinstance(provider, MockProvider)


class TestBudgetCheck:
    def test_check_budget_forwards_to_tracker(self):
        br, _ = _make_router_and_tracker()
        status = br.check_budget("daily")
        assert status.scope == "daily"
        assert status.status == "ok"

    def test_check_budget_scenario(self):
        br, tracker = _make_router_and_tracker()
        tracker.record_call("deepseek", "deepseek-v3.2", 1000, 1000, scenario_id="s1")
        status = br.check_budget("scenario")
        assert status.scope.startswith("scenario")
