"""Tests for Builder Agent (plan Task 10)."""

from sloth_agent.core.builder import Builder, BuilderOutput, ReplanResult, BuildFailure


def test_builder_basic():
    builder = Builder()
    assert builder is not None


def test_build_with_replan_signature():
    builder = Builder()
    assert hasattr(builder, "build_with_replan")


def test_builder_output_model():
    output = BuilderOutput(
        branch="test-branch",
        changed_files=["src/main.py"],
        diff_summary="Added function",
        test_results={"passed": 5, "failed": 0},
        coverage=85.0,
    )
    assert output.branch == "test-branch"
    assert len(output.changed_files) == 1
    assert output.coverage == 85.0


def test_replan_result_model():
    replan = ReplanResult(new_tasks=[], should_abort=False)
    assert not replan.should_abort
    assert replan.new_tasks == []


def test_build_failure_exception():
    try:
        raise BuildFailure(task="task1", reason="failed")
    except BuildFailure as e:
        assert e.task == "task1"
        assert "failed" in str(e)
