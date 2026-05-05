"""Tests for ContextEngine."""

import pytest
from sloth_agent.core.context.engine import ContextEngine, ContextPolicy, ContextResult


class TestContextEngine:
    def test_build_simple(self):
        engine = ContextEngine(ContextPolicy(mode="brainstorm", max_tokens=100000))
        result = engine.build(
            "You are a helpful assistant.",
            [
                {"role": "user", "content": "Hello", "id": "1"},
                {"role": "assistant", "content": "Hi there!", "id": "2"},
            ],
        )
        assert isinstance(result, ContextResult)
        assert result.system_prompt == "You are a helpful assistant."
        assert len(result.model_visible_context) > 0
        assert "token_utilization" in result.diagnostics
        assert result.diagnostics["mode"] == "brainstorm"

    def test_build_empty_messages(self):
        engine = ContextEngine()
        result = engine.build(
            "system",
            [],
        )
        assert isinstance(result, ContextResult)
        assert result.diagnostics["total_tokens"] >= 0

    def test_protect_reply_chains(self):
        engine = ContextEngine(
            ContextPolicy(mode="brainstorm", protect_threads=True, max_tokens=100000)
        )
        messages = [
            {"role": "user", "content": "Root", "id": "msg_1"},
            {"role": "agent", "content": "Reply", "id": "msg_2", "parent_message_id": "msg_1"},
            {"role": "user", "content": "Another", "id": "msg_3", "parent_message_id": "msg_2"},
        ]
        result = engine._protect_reply_chains(messages)
        # msg_1 and msg_2 should be protected (moved to end) because msg_2 references msg_1
        # and msg_3 references msg_2
        ids = [m.get("id") for m in result]
        # Protected ones (msg_1, msg_2) come after regular ones (msg_3)
        last_ids = ids[-2:]
        assert "msg_1" in last_ids
        assert "msg_2" in last_ids

    def test_protect_reply_chains_no_parents(self):
        engine = ContextEngine(ContextPolicy(protect_threads=True))
        messages = [
            {"role": "user", "content": "A", "id": "m1"},
            {"role": "agent", "content": "B", "id": "m2"},
            {"role": "user", "content": "C", "id": "m3"},
        ]
        result = engine._protect_reply_chains(messages)
        assert len(result) == 3
        # Order unchanged since no parent references
        assert result[0]["id"] == "m1"

    def test_diagnostics_budget_exceeded(self):
        engine = ContextEngine(
            ContextPolicy(mode="brainstorm", max_tokens=500, output_reserve=100)
        )
        # Create many large messages to exceed budget
        messages = [
            {"role": "user", "content": "x" * 500, "id": f"m{i}"}
            for i in range(20)
        ]
        result = engine.build("You are helpful.", messages)
        assert result.diagnostics["compression_ratio"] >= 0
        assert "total_tokens" in result.diagnostics

    def test_non_brainstorm_mode(self):
        engine = ContextEngine(ContextPolicy(mode="chat"))
        result = engine.build("sys", [{"role": "user", "content": "hi"}])
        assert result.diagnostics["mode"] == "chat"

    def test_default_policy(self):
        engine = ContextEngine()
        result = engine.build("sys", [{"role": "user", "content": "test"}])
        assert result.diagnostics["mode"] == "brainstorm"
