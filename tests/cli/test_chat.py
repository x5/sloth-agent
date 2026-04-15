"""Tests for conversation context management."""

from sloth_agent.cli.context import ConversationContext, Message


def test_context_add_message():
    ctx = ConversationContext(max_turns=2)
    ctx.add_message("user", "hello")
    ctx.add_message("assistant", "hi")
    assert len(ctx.messages) == 2


def test_context_truncation():
    ctx = ConversationContext(max_turns=1)
    ctx.add_message("user", "1")
    ctx.add_message("assistant", "a")
    ctx.add_message("user", "2")
    ctx.add_message("assistant", "b")
    msgs = ctx.get_messages()
    # Should only keep last 2 messages (1 turn) plus system prompt slot
    assert len(msgs) <= 3  # system + 2


def test_context_clear():
    ctx = ConversationContext()
    ctx.add_message("user", "test")
    ctx.clear()
    assert len(ctx.messages) == 0


def test_context_system_prompt():
    ctx = ConversationContext()
    ctx.set_system_prompt("You are a helper")
    msgs = ctx.get_messages()
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"] == "You are a helper"


def test_context_summary():
    ctx = ConversationContext()
    ctx.add_message("user", "test")
    assert "1 messages" in ctx.summary()


def test_context_get_messages_empty():
    ctx = ConversationContext()
    ctx.set_system_prompt("test")
    msgs = ctx.get_messages()
    assert len(msgs) == 1  # just system prompt
    assert msgs[0]["role"] == "system"
