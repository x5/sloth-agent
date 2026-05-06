"""Tests for LLMResponse tool_calls extraction and _extract_tool_calls contract."""

import pytest
from sloth_agent.providers.llm_providers import LLMResponse, _extract_tool_calls


class TestLLMResponse:
    def test_default_tool_calls_is_empty_list(self):
        resp = LLMResponse(content="hello", model="test-model")
        assert resp.tool_calls == []

    def test_tool_calls_stored_explicitly(self):
        tc = [{"name": "echo", "arguments": {"text": "hi"}}]
        resp = LLMResponse(content="", model="t", tool_calls=tc)
        assert resp.tool_calls == tc

    def test_none_tool_calls_becomes_empty_list(self):
        resp = LLMResponse(content="x", model="m", tool_calls=None)
        assert resp.tool_calls == []


class TestExtractToolCalls:
    def test_standard_openai_format(self):
        data = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_123",
                                "type": "function",
                                "function": {
                                    "name": "grep_repo",
                                    "arguments": '{"pattern": "def test"}',
                                },
                            }
                        ],
                    }
                }
            ]
        }
        result = _extract_tool_calls(data)
        assert len(result) == 1
        assert result[0]["name"] == "grep_repo"
        assert result[0]["arguments"] == {"pattern": "def test"}
        assert result[0]["id"] == "call_123"

    def test_multiple_tool_calls(self):
        data = {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "id": "c1",
                                "function": {
                                    "name": "read",
                                    "arguments": '{"path": "a.py"}',
                                },
                            },
                            {
                                "id": "c2",
                                "function": {
                                    "name": "grep",
                                    "arguments": '{"pattern": "x"}',
                                },
                            },
                        ]
                    }
                }
            ]
        }
        result = _extract_tool_calls(data)
        assert len(result) == 2
        assert result[0]["name"] == "read"
        assert result[1]["name"] == "grep"

    def test_no_tool_calls_returns_empty_list(self):
        data = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Hello!",
                    }
                }
            ]
        }
        result = _extract_tool_calls(data)
        assert result == []

    def test_malformed_json_arguments_graceful(self):
        data = {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "id": "c1",
                                "function": {
                                    "name": "bad",
                                    "arguments": "not valid json",
                                },
                            }
                        ]
                    }
                }
            ]
        }
        result = _extract_tool_calls(data)
        assert len(result) == 1
        # Arguments should be left as-is (string) when JSON parse fails
        assert result[0]["arguments"] == "not valid json"

    def test_empty_data_returns_empty(self):
        assert _extract_tool_calls({}) == []

    def test_missing_choices_returns_empty(self):
        assert _extract_tool_calls({"other": "data"}) == []

    def test_arguments_already_dict(self):
        data = {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "id": "c1",
                                "function": {
                                    "name": "ls_dir",
                                    "arguments": {"path": "."},
                                },
                            }
                        ]
                    }
                }
            ]
        }
        result = _extract_tool_calls(data)
        assert len(result) == 1
        assert result[0]["arguments"] == {"path": "."}
