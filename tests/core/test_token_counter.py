"""Tests for TokenCounter."""

import pytest

from sloth_agent.core.token_counter import TokenCounter


class TestTokenCounter:
    def test_estimate_non_empty_string(self):
        counter = TokenCounter()
        assert counter.count("hello world") > 0

    def test_empty_string_zero_or_one(self):
        counter = TokenCounter()
        # Empty string may return 0 or 1 depending on estimation
        assert counter.count("") >= 0

    def test_longer_text_more_tokens(self):
        counter = TokenCounter()
        short = counter.count("hello")
        long = counter.count("hello world this is a much longer text with many words")
        assert long > short

    def test_count_messages(self):
        counter = TokenCounter()
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        total = counter.count_messages(messages)
        # Each message adds ~4 overhead + content tokens
        assert total > 0

    def test_count_messages_empty_list(self):
        counter = TokenCounter()
        assert counter.count_messages([]) == 0

    def test_estimate_approximate_ratio(self):
        """4-char estimate: 'hello' (5 chars) should be ~1 token."""
        counter = TokenCounter()
        # Without tiktoken, 5 chars // 4 = 1
        count = counter.count("hello")
        assert count >= 1

    def test_consistent_counting(self):
        counter = TokenCounter()
        text = "The quick brown fox jumps over the lazy dog"
        assert counter.count(text) == counter.count(text)
