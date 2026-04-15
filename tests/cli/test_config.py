"""Tests for configuration model."""

from sloth_agent.core.config import Config, ChatConfig


def test_chat_config_defaults():
    config = ChatConfig()
    assert config.max_context_turns == 20
    assert config.auto_approve_risk_level == 2
    assert config.stream_responses is True
    assert config.prompt_prefix == "sloth> "


def test_config_has_chat_field():
    config = Config()
    assert hasattr(config, "chat")
    assert config.chat.max_context_turns == 20
