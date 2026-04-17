"""Tests for LLMRouter."""

import pytest

from sloth_agent.providers.llm_router import LLMRouter, MockProvider


def _make_router():
    routes = {
        "builder": {"stages": {"coding": {"provider": "deepseek"}}},
        "reviewer": {"stages": {"review": {"provider": "qwen"}}},
    }
    router = LLMRouter(routes)
    router.register_provider("deepseek", MockProvider("deepseek-response"))
    router.register_provider("qwen", MockProvider("qwen-response"))
    return router


def test_router_get_model():
    """builder/coding → MockProvider(deepseek), reviewer/review → MockProvider(qwen)."""
    router = _make_router()
    builder_provider = router.get_model("builder", "coding")
    assert builder_provider.generate([]) == "deepseek-response"

    reviewer_provider = router.get_model("reviewer", "review")
    assert reviewer_provider.generate([]) == "qwen-response"


def test_provider_generate_mock():
    """Mock provider's generate interface returns a string."""
    provider = MockProvider("hello world")
    result = provider.generate([{"role": "user", "content": "hi"}])
    assert isinstance(result, str)
    assert result == "hello world"
