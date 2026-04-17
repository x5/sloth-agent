"""Tests for NextStep protocol (plan Task 8)."""

from sloth_agent.core.nextstep import NextStep, NextStepType, ToolRequest


def test_nextstep_final_output():
    step = NextStep(type=NextStepType.final_output, output="Done.")
    assert step.type == NextStepType.final_output
    assert step.output == "Done."


def test_nextstep_phase_handoff():
    step = NextStep(
        type=NextStepType.phase_handoff,
        next_phase="phase-2",
        next_agent="planner",
        reason="Phase 1 completed",
    )
    assert step.type == NextStepType.phase_handoff
    assert step.next_phase == "phase-2"
    assert step.next_agent == "planner"


def test_nextstep_retry_same():
    step = NextStep(type=NextStepType.retry_same, reason="Minor tweak needed")
    assert step.type == NextStepType.retry_same


def test_nextstep_abort():
    step = NextStep(type=NextStepType.abort, reason="Unrecoverable error")
    assert step.type == NextStepType.abort


def test_nextstep_tool_call():
    step = NextStep(
        type=NextStepType.tool_call,
        request=ToolRequest(tool_name="read_file", params={"path": "src/main.py"}),
    )
    assert step.type == NextStepType.tool_call
    assert step.request.tool_name == "read_file"


def test_nextstep_serialization():
    step = NextStep(type=NextStepType.final_output, output="hello")
    dumped = step.model_dump()
    restored = NextStep.model_validate(dumped)
    assert restored.type == NextStepType.final_output
    assert restored.output == "hello"
