"""Tests for MemoryStore filesystem storage layer."""

import json
from pathlib import Path

import pytest

from sloth_agent.memory.store import MemoryStore


@pytest.fixture()
def store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(tmp_path)


def test_save_load_session_message(store: MemoryStore):
    store.save_session_message("s1", "user", "hello")
    store.save_session_message("s1", "assistant", "hi back")
    msgs = store.load_session_messages("s1")
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["content"] == "hi back"


def test_save_load_session_message_with_limit(store: MemoryStore):
    for i in range(5):
        store.save_session_message("s1", "user", f"msg-{i}")
    msgs = store.load_session_messages("s1", limit=2)
    assert len(msgs) == 2
    assert msgs[0]["content"] == "msg-3"


def test_save_load_phase_output(store: MemoryStore):
    data = {"status": "completed", "issues": []}
    store.save_phase_output("standard", "phase-5", data)
    loaded = store.load_phase_output("standard", "phase-5")
    assert loaded == data


def test_save_artifact(store: MemoryStore):
    store.save_artifact("standard", "phase-5", "output.py", b"print('hi')")
    artifact_path = store.scenarios_dir / "standard" / "phase-5" / "artifacts" / "output.py"
    assert artifact_path.exists()
    assert artifact_path.read_bytes() == b"print('hi')"


def test_save_load_knowledge(store: MemoryStore):
    data = {"key": "tdd", "tags": ["testing"]}
    store.save_knowledge("tdd", data)
    loaded = store.load_knowledge("tdd")
    assert loaded == data
