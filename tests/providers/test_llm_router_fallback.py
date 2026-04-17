"""Tests for LLMRouter with circuit breaker fallback."""

import pytest

from sloth_agent.providers.llm_router import LLMRouter, MockProvider
from sloth_agent.errors.circuit_manager import ProviderCircuitManager


class TestRouterWithoutCircuitManager:
    def test_get_model_returns_provider(self):
        router = LLMRouter()
        router.register_provider("deepseek", MockProvider("ds"))
        router.routes = {"builder": {"stages": {"coding": {"provider": "deepseek"}}}}
        provider = router.get_model("builder", "coding")
        assert provider.response == "ds"

    def test_no_route_raises(self):
        router = LLMRouter()
        with pytest.raises(ValueError, match="No route"):
            router.get_model("unknown", "stage")

    def test_unregistered_provider_raises(self):
        router = LLMRouter()
        router.routes = {"builder": {"stages": {"coding": {"provider": "missing"}}}}
        with pytest.raises(ValueError, match="not registered"):
            router.get_model("builder", "coding")


class TestRouterWithCircuitManager:
    def _make_router(self, threshold=2):
        router = LLMRouter(
            circuit_manager=ProviderCircuitManager(failure_threshold=threshold),
        )
        router.register_provider("deepseek", MockProvider("ds"))
        router.register_provider("qwen", MockProvider("qw"))
        router.register_provider("glm", MockProvider("glm-free"))
        router.routes = {"builder": {"stages": {"coding": {"provider": "deepseek"}}}}
        return router

    def test_preferred_available_returns_it(self):
        router = self._make_router()
        provider = router.get_model("builder", "coding")
        assert provider.response == "ds"

    def test_fallback_when_preferred_tripped(self):
        router = self._make_router(threshold=2)
        # Trip deepseek
        router.record_provider_result("deepseek", False)
        router.record_provider_result("deepseek", False)
        provider = router.get_model("builder", "coding")
        # Should fallback to qwen (next registered)
        assert provider.response in ("qw", "glm-free")

    def test_mock_when_all_tripped(self):
        router = self._make_router(threshold=1)
        router.record_provider_result("deepseek", False)
        router.record_provider_result("qwen", False)
        router.record_provider_result("glm", False)
        provider = router.get_model("builder", "coding")
        assert isinstance(provider, MockProvider)
        assert "unavailable" in provider.response

    def test_record_forwards_to_circuit_manager(self):
        router = self._make_router(threshold=1)
        router.record_provider_result("deepseek", False)
        assert router.circuit_manager.get_status()["deepseek"]["state"] == "open"

    def test_success_reopens_circuit(self):
        router = self._make_router(threshold=1)
        router.record_provider_result("deepseek", False)
        assert not router.circuit_manager.is_available("deepseek")
        router.record_provider_result("deepseek", True)
        assert router.circuit_manager.is_available("deepseek")
