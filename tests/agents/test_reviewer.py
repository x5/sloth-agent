"""Tests for ReviewerAgent (plan Task 15)."""

from sloth_agent.agents.reviewer import ReviewerAgent, ReviewerOutput
from sloth_agent.core.builder import BuilderOutput, CoverageReport


def test_reviewer_basic():
    agent = ReviewerAgent()
    assert agent is not None


def test_reviewer_detects_bug():
    """输入有明显 bug 的代码，验证 blocking_issues 非空。"""
    agent = ReviewerAgent()
    builder_out = BuilderOutput(
        branch="test",
        changed_files=["src/foo.py"],
        diff_summary="add a function",
        test_results=CoverageReport(total=2, passed=2, failed=0),
        coverage=85.0,
    )
    buggy_code = """
def divide(a, b):
    return a / b  # no zero check
"""
    result = agent.review(builder_out, code_map={"src/foo.py": buggy_code})
    assert len(result.blocking_issues) > 0


def test_reviewer_approves_clean_code():
    """输入干净的代码，验证 approved=True。"""
    agent = ReviewerAgent()
    builder_out = BuilderOutput(
        branch="test",
        changed_files=["src/bar.py"],
        diff_summary="add safe function",
        test_results=CoverageReport(total=1, passed=1, failed=0),
        coverage=90.0,
    )
    clean_code = """
def add(a, b):
    return a + b
"""
    result = agent.review(builder_out, code_map={"src/bar.py": clean_code})
    assert result.approved is True
    assert len(result.blocking_issues) == 0
