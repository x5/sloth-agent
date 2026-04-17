"""ProviderCircuitManager — manages circuit breakers for all providers."""

from __future__ import annotations

import logging
from typing import Any

from sloth_agent.errors.circuit_breaker import CircuitBreaker

logger = logging.getLogger("circuit_manager")


class ProviderCircuitManager:
    """Manage circuit breakers for multiple LLM providers.

    Tracks per-provider health and provides fallback routing when a provider
    is tripped.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 300,
    ):
        self._breakers: dict[str, CircuitBreaker] = {}
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout

    # ------------------------------------------------------------------
    # Provider registration
    # ------------------------------------------------------------------

    def register(self, name: str) -> None:
        """Register a provider with a new circuit breaker."""
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(
                failure_threshold=self._failure_threshold,
                recovery_timeout=self._recovery_timeout,
            )

    def remove(self, name: str) -> None:
        """Remove a provider."""
        self._breakers.pop(name, None)

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    def is_available(self, name: str) -> bool:
        """Check if a specific provider is available."""
        breaker = self._breakers.get(name)
        if breaker is None:
            return False
        return breaker.can_execute()

    def get_available_provider(self, preferred: str | None = None) -> str | None:
        """Return the best available provider.

        If preferred is available, return it. Otherwise return the first
        available one in registration order.
        """
        if preferred and self.is_available(preferred):
            return preferred

        for name, breaker in self._breakers.items():
            if breaker.can_execute():
                return name

        return None

    def get_all_available(self) -> list[str]:
        """Return all currently available providers."""
        return [n for n, b in self._breakers.items() if b.can_execute()]

    def get_all_providers(self) -> list[str]:
        """Return all registered providers."""
        return list(self._breakers.keys())

    # ------------------------------------------------------------------
    # State recording
    # ------------------------------------------------------------------

    def record(self, provider: str, success: bool) -> None:
        """Record the result of a provider call."""
        breaker = self._breakers.get(provider)
        if breaker is None:
            return

        if success:
            breaker.record_success()
        else:
            breaker.record_failure()
            if breaker.state == "open":
                logger.warning(
                    f"Circuit breaker OPEN for provider '{provider}' "
                    f"(failures={breaker.failure_count})"
                )

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def get_status(self) -> dict[str, dict[str, Any]]:
        """Return status of all breakers."""
        status = {}
        for name, breaker in self._breakers.items():
            status[name] = {
                "state": breaker.state,
                "failure_count": breaker.failure_count,
                "last_failure_time": breaker.last_failure_time,
            }
        return status

    def reset_all(self) -> None:
        """Reset all breakers to closed."""
        for breaker in self._breakers.values():
            breaker.reset()

    def reset(self, name: str) -> None:
        """Reset a specific breaker."""
        breaker = self._breakers.get(name)
        if breaker:
            breaker.reset()
