"""Tests for pricing module."""

import tempfile
from pathlib import Path

import pytest

from sloth_agent.cost.pricing import calculate_cost, get_pricing, get_budget_defaults


class TestBuiltinPricing:
    def test_all_providers_have_pricing(self):
        pricing = get_pricing()
        expected = ["deepseek", "qwen", "kimi", "glm", "minimax", "xiaomi"]
        for p in expected:
            assert p in pricing
            assert len(pricing[p]) > 0

    def test_deepseek_models_have_input_and_output_price(self):
        pricing = get_pricing()
        for model in pricing["deepseek"]:
            assert "input_per_1k" in pricing["deepseek"][model]
            assert "output_per_1k" in pricing["deepseek"][model]

    def test_glm_flash_is_free(self):
        pricing = get_pricing()
        flash = pricing["glm"]["glm-4.5-flash"]
        assert flash["input_per_1k"] == 0
        assert flash["output_per_1k"] == 0


class TestCalculateCost:
    def test_deepseek_v3_cost(self):
        input_cost, output_cost = calculate_cost(
            "deepseek-v3.2", "deepseek", 1000, 1000
        )
        assert input_cost == pytest.approx(0.001, rel=1e-6)
        assert output_cost == pytest.approx(0.002, rel=1e-6)

    def test_zero_tokens_zero_cost(self):
        input_cost, output_cost = calculate_cost(
            "deepseek-v3.2", "deepseek", 0, 0
        )
        assert input_cost == 0
        assert output_cost == 0

    def test_free_model_zero_cost(self):
        input_cost, output_cost = calculate_cost(
            "glm-4.5-flash", "glm", 10000, 5000
        )
        assert input_cost == 0
        assert output_cost == 0

    def test_unknown_model_zero_cost(self):
        input_cost, output_cost = calculate_cost(
            "unknown-model", "unknown-provider", 1000, 1000
        )
        assert input_cost == 0
        assert output_cost == 0

    def test_large_scale_cost(self):
        # 100K input + 50K output for qwen3.6-plus
        input_cost, output_cost = calculate_cost(
            "qwen3.6-plus", "qwen", 100000, 50000
        )
        assert input_cost == pytest.approx(0.1, rel=1e-6)  # 100 * 0.001
        assert output_cost == pytest.approx(0.1, rel=1e-6)  # 50 * 0.002


class TestPricingOverrides:
    def test_override_file_not_found_returns_builtin(self):
        pricing = get_pricing("/nonexistent/path/cost.yaml")
        builtin = get_pricing()
        assert pricing == builtin

    def test_override_file_changes_price(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""pricing:
  deepseek:
    deepseek-v3.2:
      input_per_1k: 0.01
      output_per_1k: 0.02
""")
            f.flush()
            pricing = get_pricing(f.name)
            ds = pricing["deepseek"]["deepseek-v3.2"]
            assert ds["input_per_1k"] == 0.01
            assert ds["output_per_1k"] == 0.02
            # Other models unchanged
            assert pricing["qwen"]["qwen3.6-plus"]["input_per_1k"] == 0.001

    def test_new_provider_in_override(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""pricing:
  openai:
    gpt-4o:
      input_per_1k: 0.005
      output_per_1k: 0.015
""")
            f.flush()
            pricing = get_pricing(f.name)
            assert "openai" in pricing
            assert pricing["openai"]["gpt-4o"]["input_per_1k"] == 0.005


class TestBudgetDefaults:
    def test_defaults_without_file(self):
        defaults = get_budget_defaults("/nonexistent")
        assert defaults["daily_limit"] == 10.0
        assert defaults["scenario_limit"] == 3.0
        assert defaults["soft_limit_percent"] == 0.8
        assert defaults["hard_limit_percent"] == 1.0

    def test_overrides_from_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""budget:
  daily_limit: 50.0
  soft_limit_percent: 0.9
""")
            f.flush()
            defaults = get_budget_defaults(f.name)
            assert defaults["daily_limit"] == 50.0
            assert defaults["soft_limit_percent"] == 0.9
            # Unchanged
            assert defaults["hard_limit_percent"] == 1.0
