"""Tests for three-layer context boundary enforcement."""

from dataclasses import dataclass

from sloth_agent.core.runner import ModelVisibleContext, RuntimeOnlyContext


def test_model_visible_only_in_prompt():
    """LLM request dict should only contain ModelVisibleContext data."""
    ctx = ModelVisibleContext(
        history=[{"role": "user", "content": "hello"}],
        retrieved_memory=[],
        current_task="write code",
        handoff_payload=None,
    )
    prompt_data = ctx.to_prompt_data()
    assert "history" in prompt_data
    assert "current_task" in prompt_data
    # These should NOT be in prompt data
    assert "config" not in prompt_data
    assert "tool_registry" not in prompt_data


def test_runtime_context_not_sent():
    """RuntimeOnlyContext data must not appear in LLM prompt data."""
    class FakeConfig:
        pass

    runtime = RuntimeOnlyContext(
        config=FakeConfig(),
        tool_registry={},
        skill_registry={},
        logger=None,
        workspace_handle="/tmp/ws",
    )
    prompt_data = runtime.to_prompt_data()
    # Runtime context should produce empty/minimal prompt data
    assert "config" not in prompt_data
    assert "tool_registry" not in prompt_data
    assert "logger" not in prompt_data
