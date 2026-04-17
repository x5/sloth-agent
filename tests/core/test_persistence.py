"""Tests for RunState persistence in Runner."""

import json
from pathlib import Path

import pytest

from sloth_agent.core.runner import RunState, Runner


@pytest.fixture()
def sample_run_state() -> RunState:
    return RunState(
        run_id="test-run-1",
        current_agent="builder",
        current_phase="coding",
        phase="running",
        turn=5,
        tool_history=[{"tool": "read_file", "status": "ok"}],
        handoff_payload={"phase": "builder", "output": "done"},
    )


def test_persist_and_resume(tmp_path: Path, sample_run_state: RunState):
    """persist() writes state.json, resume_run_state() restores it."""
    persist_dir = tmp_path / "memory" / "sessions"
    Runner.persist_state(sample_run_state, persist_dir)

    state_file = persist_dir / "test-run-1" / "state.json"
    assert state_file.exists()

    restored = Runner.resume_run_state(persist_dir / "test-run-1")
    assert restored is not None
    assert restored.run_id == "test-run-1"
    assert restored.current_agent == "builder"
    assert restored.turn == 5


def test_persist_tool_history(tmp_path: Path):
    """persist() appends tool_history.jsonl when state has tool_history."""
    state = RunState(
        run_id="hist-run",
        turn=2,
        tool_history=[
            {"tool": "read_file", "status": "ok"},
            {"tool": "write_file", "status": "ok"},
        ],
    )
    persist_dir = tmp_path / "memory" / "sessions"
    Runner.persist_state(state, persist_dir)

    history_file = persist_dir / "hist-run" / "tool_history.jsonl"
    assert history_file.exists()
    lines = history_file.read_text().strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["tool"] == "read_file"
