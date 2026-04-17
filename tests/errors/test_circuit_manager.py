"""Tests for ProviderCircuitManager — multi-provider circuit management."""

from sloth_agent.errors.circuit_manager import ProviderCircuitManager


class TestProviderRegistration:
    def test_register_creates_breaker(self):
        mgr = ProviderCircuitManager()
        mgr.register("deepseek")
        assert mgr.is_available("deepseek")

    def test_remove_deletes_breaker(self):
        mgr = ProviderCircuitManager()
        mgr.register("deepseek")
        mgr.remove("deepseek")
        assert mgr.is_available("deepseek") is False

    def test_duplicate_register_is_safe(self):
        mgr = ProviderCircuitManager()
        mgr.register("deepseek")
        mgr.register("deepseek")
        assert len(mgr.get_all_providers()) == 1


class TestGetAvailableProvider:
    def test_returns_preferred_when_available(self):
        mgr = ProviderCircuitManager()
        mgr.register("deepseek")
        mgr.register("qwen")
        assert mgr.get_available_provider("deepseek") == "deepseek"

    def test_fallback_to_next_available(self):
        mgr = ProviderCircuitManager(failure_threshold=2)
        mgr.register("deepseek")
        mgr.register("qwen")
        # Trip deepseek
        mgr.record("deepseek", False)
        mgr.record("deepseek", False)
        assert mgr.get_available_provider("deepseek") == "qwen"

    def test_returns_none_when_all_tripped(self):
        mgr = ProviderCircuitManager(failure_threshold=1)
        mgr.register("deepseek")
        mgr.record("deepseek", False)
        assert mgr.get_available_provider("deepseek") is None


class TestGetAllAvailable:
    def test_all_available_initially(self):
        mgr = ProviderCircuitManager()
        mgr.register("deepseek")
        mgr.register("qwen")
        mgr.register("glm")
        available = mgr.get_all_available()
        assert set(available) == {"deepseek", "qwen", "glm"}

    def test_filters_out_tripped(self):
        mgr = ProviderCircuitManager(failure_threshold=1)
        mgr.register("deepseek")
        mgr.register("qwen")
        mgr.record("deepseek", False)
        available = mgr.get_all_available()
        assert available == ["qwen"]


class TestRecord:
    def test_success_resets(self):
        mgr = ProviderCircuitManager(failure_threshold=2)
        mgr.register("deepseek")
        mgr.record("deepseek", False)
        mgr.record("deepseek", True)
        assert mgr.is_available("deepseek")

    def test_unknown_provider_ignored(self):
        mgr = ProviderCircuitManager()
        mgr.record("unknown", False)  # Should not raise


class TestStatus:
    def test_status_returns_all(self):
        mgr = ProviderCircuitManager(failure_threshold=2)
        mgr.register("deepseek")
        mgr.register("qwen")
        mgr.record("deepseek", False)
        status = mgr.get_status()
        assert "deepseek" in status
        assert "qwen" in status
        assert status["deepseek"]["failure_count"] == 1
        assert status["deepseek"]["state"] == "closed"

    def test_status_shows_open(self):
        mgr = ProviderCircuitManager(failure_threshold=1)
        mgr.register("deepseek")
        mgr.record("deepseek", False)
        status = mgr.get_status()
        assert status["deepseek"]["state"] == "open"


class TestReset:
    def test_reset_all(self):
        mgr = ProviderCircuitManager(failure_threshold=1)
        mgr.register("deepseek")
        mgr.register("qwen")
        mgr.record("deepseek", False)
        mgr.record("qwen", False)
        mgr.reset_all()
        assert mgr.get_all_available() == ["deepseek", "qwen"]

    def test_reset_single(self):
        mgr = ProviderCircuitManager(failure_threshold=1)
        mgr.register("deepseek")
        mgr.register("qwen")
        mgr.record("deepseek", False)
        mgr.record("qwen", False)
        mgr.reset("deepseek")
        assert mgr.is_available("deepseek")
        assert not mgr.is_available("qwen")
