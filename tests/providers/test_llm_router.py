"""Tests for LLMRouter."""

import pytest

from sloth_agent.providers.llm_router import LLMRouter, MockProvider


def _make_router():
    routes = {
        "architect": {"provider": "glm"},
        "engineer": {"provider": "deepseek"},
        "reviewer": {"provider": "qwen"},
    }
    router = LLMRouter(routes)
    router.register_provider("deepseek", MockProvider("deepseek-response"))
    router.register_provider("qwen", MockProvider("qwen-response"))
    router.register_provider("glm", MockProvider("glm-response"))
    return router


def test_router_get_provider():
    """agent names route to correct providers."""
    router = _make_router()
    engineer_provider = router.get_provider("engineer")
    assert engineer_provider.generate([]) == "deepseek-response"

    reviewer_provider = router.get_provider("reviewer")
    assert reviewer_provider.generate([]) == "qwen-response"

    architect_provider = router.get_provider("architect")
    assert architect_provider.generate([]) == "glm-response"


def test_provider_generate_mock():
    """Mock provider's generate interface returns a string."""
    provider = MockProvider("hello world")
    result = provider.generate([{"role": "user", "content": "hi"}])
    assert isinstance(result, str)
    assert result == "hello world"
