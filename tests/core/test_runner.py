"""Unit tests for Task 1: Runtime Kernel & RunState.

Covers: NextStep, RunState, Runner.resolve(), HookManager, ProductOrchestrator
"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sloth_agent.core.config import Config
from sloth_agent.core.orchestrator import ProductOrchestrator
from sloth_agent.core.runner import (
    HookManager,
    NextStep,
    NextStepType,
    RunState,
    Runner,
    ToolRequest,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_state(**kwargs) -> RunState:
    return RunState(run_id="test-run", **kwargs)


def _make_step(step_type: NextStepType, **kwargs) -> NextStep:
    return NextStep(type=step_type, **kwargs)


# ---------------------------------------------------------------------------
# NextStep serialization / deserialization
# ---------------------------------------------------------------------------

class TestNextStepSerialization:
    def test_all_types_roundtrip(self):
        for st in NextStepType:
            step = NextStep(type=st, reason="test", output="out")
            dumped = step.model_dump_json()
            restored = NextStep.model_validate_json(dumped)
            assert restored.type == st
            assert restored.reason == "test"
            assert restored.output == "out"

    def test_with_tool_request(self):
        req = ToolRequest(tool_name="read_file", params={"path": "foo.py"})
        step = NextStep(type=NextStepType.tool_call, request=req)
        dumped = step.model_dump_json()
        restored = NextStep.model_validate_json(dumped)
        assert restored.request.tool_name == "read_file"
        assert restored.request.params == {"path": "foo.py"}

    def test_with_phase_handoff(self):
        step = NextStep(
            type=NextStepType.phase_handoff,
            next_agent="reviewer",
            next_phase="review",
            output="done",
        )
        dumped = step.model_dump_json()
        restored = NextStep.model_validate_json(dumped)
        assert restored.next_agent == "reviewer"
        assert restored.next_phase == "review"


# ---------------------------------------------------------------------------
# RunState
# ---------------------------------------------------------------------------

class TestRunState:
    def test_is_finished_completed(self):
        assert _make_state(phase="completed").is_finished is True

    def test_is_finished_aborted(self):
        assert _make_state(phase="aborted").is_finished is True

    def test_is_finished_not_finished(self):
        for p in ("initializing", "running", "paused"):
            assert _make_state(phase=p).is_finished is False, f"phase={p}"

    def test_serialization_roundtrip(self):
        state = _make_state(
            session_id="s1",
            current_agent="builder",
            current_phase="coding",
            output="hello",
        )
        dumped = state.model_dump_json()
        restored = RunState.model_validate_json(dumped)
        assert restored.run_id == state.run_id
        assert restored.session_id == "s1"
        assert restored.current_agent == "builder"
        assert restored.output == "hello"

    def test_persist_and_resume(self, tmp_path: Path):
        """RunState 持久化后可正确恢复。"""
        state = _make_state(current_agent="builder", output="test")
        run_dir = tmp_path / "memory" / "sessions" / state.run_id
        run_dir.mkdir(parents=True)
        (run_dir / "state.json").write_text(state.model_dump_json(indent=2))

        # 模拟 ProductOrchestrator.resume_run_state
        restored = RunState.model_validate_json(
            (run_dir / "state.json").read_text()
        )
        assert restored.run_id == state.run_id
        assert restored.current_agent == "builder"
        assert restored.output == "test"


# ---------------------------------------------------------------------------
# Runner.resolve() — 8 types
# ---------------------------------------------------------------------------

class TestRunnerResolve:
    @pytest.fixture
    def runner(self):
        return Runner(Config())

    def test_final_output(self, runner: Runner):
        state = _make_state()
        step = _make_step(NextStepType.final_output, output="done")
        result = runner.resolve(state, step)
        assert result.phase == "completed"
        assert result.output == "done"

    def test_tool_call(self, runner: Runner, tmp_path: Path):
        state = _make_state()
        # Create a real temp file so HallucinationGuard allows it
        f = tmp_path / "x.py"
        f.write_text("# test")
        req = ToolRequest(tool_name="read_file", params={"path": str(f)})
        step = _make_step(NextStepType.tool_call, request=req)
        result = runner.resolve(state, step)
        assert len(result.tool_history) == 1
        # tool should succeed
        assert result.tool_history[0]["success"] is True

    def test_phase_handoff(self, runner: Runner):
        state = _make_state(current_agent="builder", current_phase="coding")
        step = _make_step(
            NextStepType.phase_handoff,
            next_agent="reviewer",
            next_phase="review",
            output="builder output",
        )
        result = runner.resolve(state, step)
        assert result.current_agent == "reviewer"
        assert result.current_phase == "review"
        assert result.turn == 0
        assert result.handoff_payload["output"] == "builder output"

    def test_retry_same(self, runner: Runner):
        state = _make_state()
        step = _make_step(NextStepType.retry_same)
        result = runner.resolve(state, step)
        assert result.phase == state.phase  # no change

    def test_retry_different(self, runner: Runner):
        state = _make_state()
        step = _make_step(NextStepType.retry_different, reason="wrong approach")
        result = runner.resolve(state, step)
        assert "wrong approach" in result.errors

    def test_replan(self, runner: Runner):
        state = _make_state()
        step = _make_step(NextStepType.replan, reason="plan invalid")
        result = runner.resolve(state, step)
        assert result.phase == "aborted"
        assert "plan invalid" in result.errors

    def test_interruption(self, runner: Runner):
        state = _make_state()
        req = ToolRequest(tool_name="run_command", params={"cmd": "deploy"})
        step = _make_step(
            NextStepType.interruption,
            request=req,
            reason="needs approval",
        )
        result = runner.resolve(state, step)
        assert result.phase == "paused"
        assert len(result.pending_interruptions) == 1
        assert result.pending_interruptions[0]["tool_name"] == "run_command"

    def test_abort(self, runner: Runner):
        state = _make_state()
        step = _make_step(NextStepType.abort, reason="fatal error")
        result = runner.resolve(state, step)
        assert result.phase == "aborted"
        assert "fatal error" in result.errors


# ---------------------------------------------------------------------------
# HookManager
# ---------------------------------------------------------------------------

class TestHookManager:
    def test_on_and_emit(self):
        hm = HookManager()
        calls = []
        hm.on("test.event", lambda d: calls.append(d))
        hm.on("test.event", lambda d: calls.append(d * 2))
        hm.emit("test.event", "hello")
        assert calls == ["hello", "hellohello"]

    def test_emit_no_handlers(self):
        hm = HookManager()
        hm.emit("nonexistent", "data")  # should not raise

    def test_hook_points(self):
        hm = HookManager()
        points = hm.hook_points()
        assert "run.start" in points
        assert "run.end" in points
        assert "handoff" in points
        assert len(points) == 15


# ---------------------------------------------------------------------------
# ProductOrchestrator
# ---------------------------------------------------------------------------

class TestProductOrchestrator:
    def test_create_run_state(self):
        config = Config()
        orch = ProductOrchestrator(config)
        state = orch.create_run_state(run_id="abc123", session_id="sess-1")
        assert state.run_id == "abc123"
        assert state.session_id == "sess-1"
        assert state.phase == "initializing"

    def test_resume_run_state_not_found(self):
        config = Config()
        orch = ProductOrchestrator(config)
        result = orch.resume_run_state("nonexistent-run-id")
        assert result is None

    def test_resume_run_state_found(self, tmp_path: Path):
        """写入 state.json 后能正确恢复。"""
        config = Config()
        orch = ProductOrchestrator(config)

        run_id = "mock-run-123"
        state_data = RunState(
            run_id=run_id,
            current_agent="builder",
            phase="running",
            turn=5,
        )

        # Mock _memory_dir to use tmp_path
        memory_dir = tmp_path / "memory" / "sessions" / run_id
        memory_dir.mkdir(parents=True)
        (memory_dir / "state.json").write_text(state_data.model_dump_json())

        with patch.object(orch, "_memory_dir", return_value=memory_dir):
            restored = orch.resume_run_state(run_id)
            assert restored is not None
            assert restored.run_id == run_id
            assert restored.current_agent == "builder"
            assert restored.turn == 5


# ---------------------------------------------------------------------------
# Runner.run() with mocked LLM
# ---------------------------------------------------------------------------

class TestRunnerRun:
    def test_run_completes_with_final_output(self):
        """mock think() 直接返回 final_output，run() 应一次退出。"""
        config = Config()
        runner = Runner(config)

        call_count = 0

        def mock_think(state):
            nonlocal call_count
            call_count += 1
            return NextStep(type=NextStepType.final_output, output="done")

        runner.think = mock_think
        state = _make_state(phase="running")
        result = runner.run(state)

        assert result.phase == "completed"
        assert result.output == "done"
        assert call_count == 1

    def test_run_with_tool_then_final(self, tmp_path: Path):
        """mock think() 先返回 tool_call 再返回 final_output。"""
        config = Config()
        runner = Runner(config)

        # Create a real temp file so HallucinationGuard allows it
        f = tmp_path / "x.py"
        f.write_text("# test")

        calls = []

        def mock_think(state):
            calls.append(state.turn)
            if state.turn == 1:
                return NextStep(
                    type=NextStepType.tool_call,
                    request=ToolRequest(tool_name="read_file", params={"path": str(f)}),
                )
            return NextStep(type=NextStepType.final_output, output="finished")

        runner.think = mock_think
        state = _make_state(phase="running")
        result = runner.run(state)

        assert result.phase == "completed"
        assert result.output == "finished"
        assert calls == [1, 2]
        # turn 1 执行了一次 tool_call
        assert len(result.tool_history) == 1

    def test_run_aborts_after_replan(self):
        """mock think() 返回 replan，run() 应在一次 turn 后退出。"""
        config = Config()
        runner = Runner(config)
        runner.think = lambda state: NextStep(
            type=NextStepType.replan, reason="needs replan"
        )
        state = _make_state(phase="running")
        result = runner.run(state)
        assert result.phase == "aborted"
