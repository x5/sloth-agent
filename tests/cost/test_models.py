"""Tests for CostTracker and cost data models."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from sloth_agent.cost.tracker import CostTracker
from sloth_agent.cost.models import CostBreakdown, CostRecord, BudgetStatus


class TestCostRecord:
    def test_record_fields(self):
        r = CostRecord(
            timestamp=1000.0, provider="deepseek", model="deepseek-v3.2",
            input_tokens=1000, output_tokens=500,
            input_cost=0.001, output_cost=0.001, total_cost=0.002,
            call_id="abc123",
        )
        assert r.provider == "deepseek"
        assert r.total_cost == 0.002
        assert r.scenario_id is None


class TestCostTracker:
    def _make_tracker(self) -> CostTracker:
        tmp = tempfile.mkdtemp()
        return CostTracker(storage_dir=tmp)

    def test_record_single_call(self):
        tracker = self._make_tracker()
        record = tracker.record_call(
            provider="deepseek", model="deepseek-v3.2",
            input_tokens=1000, output_tokens=1000,
        )
        assert record.provider == "deepseek"
        assert record.model == "deepseek-v3.2"
        assert record.input_tokens == 1000
        assert record.output_tokens == 1000
        assert record.total_cost > 0
        assert record.call_id != ""

    def test_daily_total_accumulates(self):
        tracker = self._make_tracker()
        tracker.record_call("deepseek", "deepseek-v3.2", 1000, 1000)
        tracker.record_call("deepseek", "deepseek-v3.2", 1000, 1000)
        first = tracker.records[0].total_cost
        assert tracker.daily_total == pytest.approx(first * 2, rel=1e-6)

    def test_scenario_totals(self):
        tracker = self._make_tracker()
        tracker.record_call("deepseek", "deepseek-v3.2", 1000, 1000, scenario_id="s1")
        tracker.record_call("deepseek", "deepseek-v3.2", 1000, 1000, scenario_id="s1")
        tracker.record_call("qwen", "qwen3.6-plus", 1000, 1000, scenario_id="s2")
        assert tracker.scenario_totals["s1"] > tracker.scenario_totals["s2"]

    def test_get_cost_by_model(self):
        tracker = self._make_tracker()
        tracker.record_call("deepseek", "deepseek-v3.2", 1000, 1000)
        tracker.record_call("qwen", "qwen3.6-plus", 1000, 1000)
        by_model = tracker.get_cost_by_model()
        assert "deepseek-v3.2" in by_model
        assert "qwen3.6-plus" in by_model

    def test_get_cost_by_provider(self):
        tracker = self._make_tracker()
        tracker.record_call("deepseek", "deepseek-v3.2", 1000, 1000)
        tracker.record_call("deepseek", "deepseek-r1-0528", 1000, 1000)
        by_provider = tracker.get_cost_by_provider()
        assert by_provider["deepseek"] > 0

    def test_persistence_roundtrip(self):
        tmp = tempfile.mkdtemp()
        tracker = CostTracker(storage_dir=tmp)
        tracker.record_call("deepseek", "deepseek-v3.2", 1000, 1000, run_id="r1")
        tracker.record_call("qwen", "qwen3.6-plus", 2000, 500, run_id="r2")

        # Create a new tracker from same directory
        tracker2 = CostTracker(storage_dir=tmp)
        assert len(tracker2.records) == 2
        assert tracker2.daily_total == pytest.approx(tracker.daily_total, rel=1e-6)

    def test_get_daily_tokens(self):
        tracker = self._make_tracker()
        tracker.record_call("deepseek", "deepseek-v3.2", 1000, 500)
        tracker.record_call("qwen", "qwen3.6-plus", 2000, 1000)
        assert tracker.get_daily_tokens() == 4500

    def test_forecast_at_zero_hour(self):
        tracker = self._make_tracker()
        tracker.record_call("deepseek", "deepseek-v3.2", 1000, 1000)
        assert tracker.forecast_daily_cost(current_hour=0) == tracker.daily_total

    def test_forecast_linear_extrapolation(self):
        tracker = self._make_tracker()
        tracker.record_call("deepseek", "deepseek-v3.2", 1000, 1000)
        cost_12h = tracker.forecast_daily_cost(current_hour=12)
        # Should be roughly 2x the current daily total
        assert cost_12h == pytest.approx(tracker.daily_total * 2, rel=1e-6)

    def test_get_breakdown(self):
        tracker = self._make_tracker()
        tracker.record_call("deepseek", "deepseek-v3.2", 1000, 1000, scenario_id="s1")
        tracker.record_call("qwen", "qwen3.6-plus", 2000, 500, scenario_id="s2")
        bd = tracker.get_breakdown()
        assert bd.total > 0
        assert bd.total_calls == 2
        assert "deepseek" in bd.by_provider
        assert "qwen" in bd.by_provider
        assert bd.total_tokens == 4500

    def test_get_total_cost(self):
        tracker = self._make_tracker()
        tracker.record_call("deepseek", "deepseek-v3.2", 1000, 1000)
        tracker.record_call("qwen", "qwen3.6-plus", 1000, 1000)
        total = tracker.get_total_cost()
        assert total > 0

    def test_get_usage_by_model(self):
        tracker = self._make_tracker()
        tracker.record_call("deepseek", "deepseek-v3.2", 1000, 1000)
        tracker.record_call("deepseek", "deepseek-v3.2", 2000, 500)
        usage = tracker.get_usage_by_model()
        assert "deepseek-v3.2" in usage
        assert usage["deepseek-v3.2"]["calls"] == 2
        assert usage["deepseek-v3.2"]["input_tokens"] == 3000


class TestBudget:
    def _make_tracker(self) -> CostTracker:
        tmp = tempfile.mkdtemp()
        return CostTracker(storage_dir=tmp)

    def test_budget_ok(self):
        tracker = self._make_tracker()
        # 10 yuan daily limit, default
        status = tracker.check_budget("daily")
        assert status.status == "ok"
        assert status.action == "continue"

    def test_budget_soft_limit(self):
        tmp = tempfile.mkdtemp()
        tracker = CostTracker(storage_dir=tmp)
        tracker.budget["daily_limit"] = 0.01  # 1 fen
        tracker.record_call("deepseek", "deepseek-v3.2", 1000, 1000)
        tracker.record_call("deepseek", "deepseek-v3.2", 1000, 1000)
        tracker.record_call("deepseek", "deepseek-v3.2", 1000, 1000)
        # Cost should be above 80% of 0.01
        status = tracker.check_budget("daily")
        assert status.status in ("soft_limit_reached", "hard_exceeded")

    def test_budget_hard_limit(self):
        tmp = tempfile.mkdtemp()
        tracker = CostTracker(storage_dir=tmp)
        tracker.budget["daily_limit"] = 0.001  # 0.1 fen, very low
        tracker.record_call("deepseek", "deepseek-v3.2", 1000, 1000)
        status = tracker.check_budget("daily")
        assert status.status == "hard_exceeded"
        assert status.action == "stop_all"

    def test_scenario_budget(self):
        tracker = self._make_tracker()
        tracker.record_call("deepseek", "deepseek-v3.2", 1000, 1000, scenario_id="s1")
        status = tracker.check_budget("scenario")
        assert status.status == "ok"

    def test_invalid_scope(self):
        tracker = self._make_tracker()
        with pytest.raises(ValueError, match="Unknown budget scope"):
            tracker.check_budget("weekly")


class TestFileStorage:
    def test_jsonl_file_created(self):
        tmp = tempfile.mkdtemp()
        tracker = CostTracker(storage_dir=tmp)
        tracker.record_call("deepseek", "deepseek-v3.2", 1000, 1000)

        today = tracker._today_str()
        path = Path(tmp) / f"{today}.jsonl"
        assert path.exists()
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["provider"] == "deepseek"
        assert data["model"] == "deepseek-v3.2"

    def test_multiple_records_same_file(self):
        tmp = tempfile.mkdtemp()
        tracker = CostTracker(storage_dir=tmp)
        tracker.record_call("deepseek", "deepseek-v3.2", 1000, 1000)
        tracker.record_call("qwen", "qwen3.6-plus", 2000, 500)

        today = tracker._today_str()
        path = Path(tmp) / f"{today}.jsonl"
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2
