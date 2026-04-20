"""LLM Router - Route requests to providers based on agent name.

Supports circuit-breaker-backed fallback chains.
"""

from __future__ import annotations

from typing import Any

from sloth_agent.errors.circuit_manager import ProviderCircuitManager


class MockProvider:
    """A provider that returns a fixed response (for testing / fallback)."""

    name = "mock"

    def __init__(self, response: str = "OK"):
        self.response = response

    def generate(self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 4096) -> str:
        return self.response


class LLMRouter:
    """Route LLM requests to different providers based on agent name.

    Each agent declares its own model/provider in agents/*.md.
    Supports optional circuit breaker integration for automatic fallback.
    """

    def __init__(
        self,
        routes: dict[str, Any] | None = None,
        circuit_manager: ProviderCircuitManager | None = None,
    ):
        """
        Args:
            routes: dict like
                {
                    "architect": {"provider": "glm"},
                    "engineer": {"provider": "deepseek"},
                }
            circuit_manager: Optional circuit manager for provider health tracking.
        """
        self.routes = routes or {}
        self.providers: dict[str, Any] = {}
        self.circuit_manager = circuit_manager

    def register_provider(self, name: str, provider: Any) -> None:
        """Register a provider instance."""
        self.providers[name] = provider
        if self.circuit_manager:
            self.circuit_manager.register(name)

    def get_provider(self, agent_name: str) -> Any:
        """Get the provider for a given agent name.

        If circuit_manager is configured, will fallback to an available
        provider when the preferred one is tripped.
        """
        route = self.routes.get(agent_name)
        if route is None:
            raise ValueError(f"No route for agent={agent_name}")

        provider_name = route["provider"]

        # Without circuit manager: direct lookup
        if self.circuit_manager is None:
            if provider_name not in self.providers:
                raise ValueError(f"Provider '{provider_name}' not registered")
            return self.providers[provider_name]

        # With circuit manager: try preferred, then fallback
        if self.circuit_manager.is_available(provider_name):
            return self.providers[provider_name]

        # Fallback to any available provider
        available = self.circuit_manager.get_available_provider()
        if available and available in self.providers:
            return self.providers[available]

        # All providers tripped — return mock fallback
        return MockProvider(response="[all providers unavailable]")

    def record_provider_result(self, provider_name: str, success: bool) -> None:
        """Forward result to circuit manager."""
        if self.circuit_manager:
            self.circuit_manager.record(provider_name, success)
