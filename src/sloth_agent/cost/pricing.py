"""Pricing table — built-in prices for all supported models, loadable from YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# Built-in pricing (¥ per 1K tokens). Source: spec 20260416-12-cost-budget-spec.md §2.1
_BUILTIN_PRICING: dict[str, dict[str, dict[str, float]]] = {
    "deepseek": {
        "deepseek-v3.2": {"input_per_1k": 0.001, "output_per_1k": 0.002},
        "deepseek-r1-0528": {"input_per_1k": 0.002, "output_per_1k": 0.004},
        "deepseek-v4": {"input_per_1k": 0.002, "output_per_1k": 0.004},
    },
    "qwen": {
        "qwen3.6-plus": {"input_per_1k": 0.001, "output_per_1k": 0.002},
        "qwen3.5-plus": {"input_per_1k": 0.0005, "output_per_1k": 0.001},
        "qwen3-max": {"input_per_1k": 0.002, "output_per_1k": 0.004},
    },
    "kimi": {
        "kimi-k2.5": {"input_per_1k": 0.002, "output_per_1k": 0.004},
        "kimi-k2": {"input_per_1k": 0.001, "output_per_1k": 0.002},
    },
    "glm": {
        "glm-5.1": {"input_per_1k": 0.002, "output_per_1k": 0.004},
        "glm-5": {"input_per_1k": 0.001, "output_per_1k": 0.002},
        "glm-4.5-flash": {"input_per_1k": 0, "output_per_1k": 0},
    },
    "minimax": {
        "minimax-m2.7": {"input_per_1k": 0.002, "output_per_1k": 0.004},
        "minimax-m1": {"input_per_1k": 0.001, "output_per_1k": 0.002},
    },
    "xiaomi": {
        "mimo-v2-pro": {"input_per_1k": 0.001, "output_per_1k": 0.002},
        "mimo-v2-omni": {"input_per_1k": 0.002, "output_per_1k": 0.004},
        "mimo-v2-flash": {"input_per_1k": 0.0005, "output_per_1k": 0.001},
    },
}


def get_pricing(overrides_path: Path | str | None = None) -> dict[str, dict[str, dict[str, float]]]:
    """Return the pricing table, optionally overridden by a YAML file.

    YAML structure must match the builtin format:
        pricing:
          deepseek:
            deepseek-v3.2:
              input_per_1k: 0.001
              output_per_1k: 0.002
    """
    if overrides_path is None:
        return dict(_BUILTIN_PRICING)

    overrides_path = Path(overrides_path)
    if not overrides_path.exists():
        return dict(_BUILTIN_PRICING)

    data = yaml.safe_load(overrides_path.read_text(encoding="utf-8"))
    if not data or "pricing" not in data:
        return dict(_BUILTIN_PRICING)

    # Deep-merge overrides into builtin
    result = dict(_BUILTIN_PRICING)
    for provider, models in data["pricing"].items():
        if provider not in result:
            result[provider] = {}
        for model, prices in models.items():
            result[provider][model] = prices
    return result


def calculate_cost(model: str, provider: str, input_tokens: int, output_tokens: int, pricing: dict | None = None) -> tuple[float, float]:
    """Calculate input and output cost for a given LLM call.

    Returns (input_cost, output_cost) in ¥.
    """
    pricing = pricing or _BUILTIN_PRICING
    model_prices = pricing.get(provider, {}).get(model, {})
    input_per_1k = model_prices.get("input_per_1k", 0)
    output_per_1k = model_prices.get("output_per_1k", 0)

    input_cost = (input_tokens / 1000) * input_per_1k
    output_cost = (output_tokens / 1000) * output_per_1k
    return input_cost, output_cost


def get_budget_defaults(overrides_path: Path | str | None = None) -> dict[str, Any]:
    """Return budget default values, optionally overridden by YAML."""
    defaults = {
        "daily_limit": 10.0,
        "scenario_limit": 3.0,
        "soft_limit_percent": 0.8,
        "hard_limit_percent": 1.0,
    }
    if overrides_path is None:
        return defaults

    overrides_path = Path(overrides_path)
    if not overrides_path.exists():
        return defaults

    data = yaml.safe_load(overrides_path.read_text(encoding="utf-8"))
    if not data or "budget" not in data:
        return defaults

    for key in defaults:
        if key in data["budget"]:
            defaults[key] = data["budget"][key]
    return defaults
