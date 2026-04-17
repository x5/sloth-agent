"""LLM Router - Route requests to providers based on agent and stage."""

from __future__ import annotations

from typing import Any


class MockProvider:
    """A provider that returns a fixed response (for testing / fallback)."""

    name = "mock"

    def __init__(self, response: str = "OK"):
        self.response = response

    def generate(self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 4096) -> str:
        return self.response


class LLMRouter:
    """Route LLM requests to different providers based on agent + stage."""

    def __init__(self, routes: dict[str, Any] | None = None):
        """
        Args:
            routes: dict like
                {
                    "builder": {"stages": {"coding": {"provider": "deepseek"}}},
                    "reviewer": {"stages": {"review": {"provider": "qwen"}}},
                }
        """
        self.routes = routes or {}
        self.providers: dict[str, Any] = {}

    def register_provider(self, name: str, provider: Any) -> None:
        """Register a provider instance."""
        self.providers[name] = provider

    def get_model(self, agent: str, stage: str) -> Any:
        """Get the provider for a given agent + stage combination."""
        route = self.routes.get(agent, {}).get("stages", {}).get(stage)
        if route is None:
            raise ValueError(f"No route for agent={agent}, stage={stage}")
        provider_name = route["provider"]
        if provider_name not in self.providers:
            raise ValueError(f"Provider '{provider_name}' not registered")
        return self.providers[provider_name]
