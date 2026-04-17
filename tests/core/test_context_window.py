"""Tests for ContextWindowManager (plan Task 8)."""

from sloth_agent.core.context_window import ContextWindowManager


def test_build_messages_basic():
    mgr = ContextWindowManager(max_tokens=128_000, output_reserve=15_000)
    msgs = mgr.build_messages(
        system="You are an assistant.",
        history=[],
        tool_results=[],
        user_msg="Hello",
    )
    assert len(msgs) > 0


def test_tool_result_compression():
    mgr = ContextWindowManager(max_tokens=128_000, output_reserve=15_000)
    summary = ContextWindowManager._compress_tool_result(
        type("ToolResult", (), {
            "tool_name": "read_file",
            "path": "src/main.py",
            "line_count": 42,
        })()
    )
    assert "42" in summary["content"]
    assert "已读取" in summary["content"]


def test_context_fits_within_budget():
    mgr = ContextWindowManager(max_tokens=4000, output_reserve=500)
    msgs = mgr.build_messages(
        system="Short system prompt",
        history=[],
        tool_results=[],
        user_msg="Short user message",
    )
    # Should not raise
    assert len(msgs) >= 2


def test_truncates_history_when_over_budget():
    mgr = ContextWindowManager(max_tokens=200, output_reserve=50)
    long_history = [{"role": "user", "content": "x" * 100} for _ in range(10)]
    msgs = mgr.build_messages(
        system="sys",
        history=long_history,
        tool_results=[],
        user_msg="go",
    )
    # Should fit within budget — fewer messages than full history
    assert len(msgs) < 12  # system + user + truncated history
