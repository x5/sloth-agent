"""Budget-aware LLM router — wraps LLMRouter with budget checks and model degradation."""

from __future__ import annotations

from typing import Any

from sloth_agent.cost.tracker import CostTracker
from sloth_agent.cost.models import BudgetStatus


# Model tiers by cost (cheapest to most expensive)
_CHEAP_MODELS = ["glm-4.5-flash", "qwen3.5-plus", "deepseek-v3.2", "mimo-v2-flash"]
_MID_MODELS = ["qwen3.6-plus", "glm-5", "minimax-m1", "deepseek-r1-0528", "mimo-v2-pro"]
_EXPENSIVE_MODELS = ["glm-5.1", "kimi-k2.5", "minimax-m2.7", "qwen3-max", "mimo-v2-omni"]


class BudgetAwareLLMRouter:
    """Wrap an existing LLMRouter to enforce budget limits.

    When budget approaches limits, automatically downgrade to cheaper models.
    """

    def __init__(
        self,
        llm_router: Any,
        cost_tracker: CostTracker,
    ):
        """
        Args:
            llm_router: The underlying LLMRouter instance.
            cost_tracker: Active CostTracker instance.
        """
        self.router = llm_router
        self.tracker = cost_tracker

    def select_model(
        self,
        preferred: str,
        agent: str = "",
        task_complexity: str = "medium",
    ) -> str:
        """Select a model based on budget status.

        Returns the model/provider to use.
        """
        budget = self.tracker.check_budget("daily")

        if budget.status == "hard_exceeded":
            return self._pick_cheapest_available(preferred)
        elif budget.status == "soft_limit_reached":
            if task_complexity == "low":
                return self._pick_from_tier(_CHEAP_MODELS, preferred)
            elif task_complexity == "medium":
                return self._pick_from_tier(_MID_MODELS, preferred)

        return preferred

    def check_budget(self, scope: str = "daily") -> BudgetStatus:
        """Forward budget check."""
        return self.tracker.check_budget(scope)

    def get_provider(self, agent_name: str, task_complexity: str = "medium") -> Any:
        """Get the provider for agent_name, respecting budget constraints.

        Wraps the underlying LLMRouter.get_provider() with budget-aware model selection.
        """
        budget = self.tracker.check_budget("daily")

        # Try to get the originally routed model
        try:
            provider = self.router.get_provider(agent_name)
            model_name = getattr(provider, "name", "")
        except (ValueError, AttributeError):
            # Router failed, return mock fallback
            from sloth_agent.providers.llm_router import MockProvider
            return MockProvider(response="[budget: degraded response]")

        if budget.status == "hard_exceeded":
            # Swap to cheapest available provider
            cheapest = self._pick_cheapest_available(model_name)
            if cheapest != model_name and cheapest in self.router.providers:
                return self.router.providers[cheapest]
            return provider  # Fallback to original if no alternative

        elif budget.status == "soft_limit_reached":
            tier = _MID_MODELS if task_complexity != "low" else _CHEAP_MODELS
            chosen = self._pick_from_tier(tier, model_name)
            if chosen != model_name and chosen in self.router.providers:
                return self.router.providers[chosen]
            return provider

        return provider

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _pick_cheapest_available(self, preferred: str) -> str:
        """Return the cheapest available model name."""
        registered = set(self.router.providers.keys())
        for model in _CHEAP_MODELS:
            if model in registered:
                return model
        return preferred

    def _pick_from_tier(self, tier: list[str], preferred: str) -> str:
        """Return the first model in the tier that is registered."""
        registered = set(self.router.providers.keys())
        for model in tier:
            if model in registered:
                return model
        return preferred
