"""Tests for ContextWindowManager token-based truncation and summary compression."""

from dataclasses import dataclass

import pytest

from sloth_agent.core.context_window import ContextWindowManager


@dataclass
class MockToolResult:
    tool_name: str
    path: str = ""
    line_count: int = 0
    exit_code: int = 0
    command: str = ""
    stderr: str = ""
    pattern: str = ""
    match_count: int = 0
    summary: str = ""


class TestContextWindowBuilder:
    def test_build_messages_includes_system_and_user(self):
        mgr = ContextWindowManager(max_tokens=4000, output_reserve=1000)
        msgs = mgr.build_messages(
            system="You are a builder",
            history=[],
            tool_results=[],
            user_msg="Create a FastAPI app",
        )
        assert msgs[0]["role"] == "system"
        assert msgs[-1]["role"] == "user"
        assert msgs[-1]["content"] == "Create a FastAPI app"

    def test_build_messages_fits_tool_results(self):
        mgr = ContextWindowManager(max_tokens=8000, output_reserve=1000)
        tools = [
            {"role": "tool", "content": "file contents " * 10},
            {"role": "tool", "content": "another result " * 5},
        ]
        msgs = mgr.build_messages(
            system="system", history=[], tool_results=tools, user_msg="go"
        )
        # Should include tool results
        assert any("file contents" in str(m) for m in msgs)

    def test_build_messages_fits_history(self):
        mgr = ContextWindowManager(max_tokens=8000, output_reserve=1000)
        history = [
            {"role": "user", "content": f"Q{i}" * 10}
            for i in range(5)
        ]
        msgs = mgr.build_messages(
            system="system", history=history, tool_results=[], user_msg="go"
        )
        # Should include some history
        assert len(msgs) > 2  # system + some history + user


class TestTokenBudget:
    def test_small_budget_truncates(self):
        mgr = ContextWindowManager(max_tokens=500, output_reserve=100)
        history = [
            {"role": "user", "content": f"This is a longer message number {i} with lots of text"}
            for i in range(20)
        ]
        tools = [{"role": "tool", "content": "tool result " * 20}]
        msgs = mgr.build_messages(
            system="system prompt", history=history, tool_results=tools, user_msg="go"
        )
        # System and user should always be present
        assert msgs[0]["role"] == "system"
        assert msgs[-1]["role"] == "user"


class TestSummaryCompression:
    def test_generate_summary(self):
        mgr = ContextWindowManager()
        early = [
            {"role": "user", "content": "What is FastAPI?"},
            {"role": "assistant", "content": "FastAPI is a modern web framework"},
        ]
        summary = mgr.generate_summary(early)
        assert "What is FastAPI?" in summary
        assert mgr._summary_turns == 1

    def test_should_compress_when_over_budget(self):
        mgr = ContextWindowManager(max_tokens=200, output_reserve=50)
        msgs = [
            {"role": "system", "content": "system " * 100},
            {"role": "user", "content": "user " * 100},
        ]
        assert mgr.should_compress(msgs)

    def test_should_not_compress_when_under_budget(self):
        mgr = ContextWindowManager(max_tokens=10000, output_reserve=1000)
        msgs = [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "user"},
        ]
        assert not mgr.should_compress(msgs)


class TestSkillInjection:
    def test_inject_skills_returns_concatenated(self):
        mgr = ContextWindowManager()

        class MockSkillManager:
            def get_skill_content(self, sid):
                return f"Content of {sid}"

        sm = MockSkillManager()
        result = mgr.inject_skills(["skill1", "skill2"], sm)
        assert "skill1" in result
        assert "skill2" in result
        assert "## Skill:" in result

    def test_inject_skills_skips_empty(self):
        mgr = ContextWindowManager()

        class MockSkillManager:
            def get_skill_content(self, sid):
                return None

        result = mgr.inject_skills(["missing"], MockSkillManager())
        assert result == ""


class TestToolResultCompression:
    def test_read_file_compressed(self):
        mgr = ContextWindowManager()
        result = MockToolResult(tool_name="read_file", path="/app/main.py", line_count=100)
        compressed = mgr._compress_tool_result(result)
        assert "已读取" in compressed["content"]
        assert "100" in compressed["content"]

    def test_run_command_success_compressed(self):
        mgr = ContextWindowManager()
        result = MockToolResult(tool_name="run_command", command="pytest", exit_code=0)
        compressed = mgr._compress_tool_result(result)
        assert "命令成功" in compressed["content"]

    def test_run_command_failure_compressed(self):
        mgr = ContextWindowManager()
        result = MockToolResult(tool_name="run_command", command="pytest", exit_code=1, stderr="failed")
        compressed = mgr._compress_tool_result(result)
        assert "命令失败" in compressed["content"]
        assert "exit=1" in compressed["content"]

    def test_grep_compressed(self):
        mgr = ContextWindowManager()
        result = MockToolResult(tool_name="grep", pattern="def ", match_count=42)
        compressed = mgr._compress_tool_result(result)
        assert "搜索" in compressed["content"]
        assert "42" in compressed["content"]

    def test_unknown_tool_compressed(self):
        mgr = ContextWindowManager()
        result = MockToolResult(tool_name="custom_tool", summary="some custom result here")
        compressed = mgr._compress_tool_result(result)
        assert "custom_tool" in compressed["content"]
