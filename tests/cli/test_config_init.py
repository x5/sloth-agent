"""Tests for config init interactive wizard helpers."""

import pytest
from sloth_agent.cli.config_cmd import _get_base_url, _get_default_models


class TestGetBaseUrl:
    def test_all_providers_have_urls(self):
        providers = ["deepseek", "qwen", "kimi", "glm", "minimax", "xiaomi"]
        for p in providers:
            url = _get_base_url(p)
            assert url.startswith("https://")
            assert "http" in url

    def test_unknown_provider_empty(self):
        assert _get_base_url("unknown") == ""


class TestGetDefaultModels:
    def test_deepseek_has_coding_and_reasoning(self):
        models = _get_default_models("deepseek")
        assert "coding" in models
        assert "reasoning" in models

    def test_qwen_has_review(self):
        models = _get_default_models("qwen")
        assert "review" in models

    def test_kimi_has_vision(self):
        models = _get_default_models("kimi")
        assert "vision" in models

    def test_unknown_provider_empty(self):
        assert _get_default_models("unknown") == {}


class TestInteractiveInitHelpers:
    def test_base_url_matches_model_mapping(self):
        """Provider's base_url and models should both be non-empty for known providers."""
        providers = ["deepseek", "qwen", "kimi", "glm", "minimax", "xiaomi"]
        for p in providers:
            url = _get_base_url(p)
            models = _get_default_models(p)
            assert url, f"{p}: missing base_url"
            assert models, f"{p}: missing model mapping"
