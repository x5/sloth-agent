"""Tests for SessionManager and ChatSession."""

import json
import tempfile
from pathlib import Path

import pytest

from sloth_agent.chat.session import ChatSession, SessionManager


class TestChatSession:
    def test_creates_with_auto_id(self):
        s = ChatSession()
        assert len(s.session_id) == 12

    def test_add_message(self):
        s = ChatSession()
        s.add_message("user", "hello")
        s.add_message("assistant", "hi there")
        assert len(s.messages) == 2
        assert s.messages[0].role == "user"

    def test_get_messages_for_llm(self):
        s = ChatSession()
        s.add_message("system", "You are an assistant")
        for i in range(30):
            s.add_message("user", f"msg {i}")
            s.add_message("assistant", f"reply {i}")

        msgs = s.get_messages_for_llm(max_turns=5)
        # System + last 10 messages (5 turns)
        assert msgs[0]["role"] == "system"
        assert len(msgs) == 11  # 1 system + 10 recent

    def test_to_dict_roundtrip(self):
        s = ChatSession(metadata={"plan": "test"})
        s.add_message("user", "hello")
        s.add_message("assistant", "hi")

        data = s.to_dict()
        s2 = ChatSession.from_dict(data)
        assert s2.session_id == s.session_id
        assert len(s2.messages) == 2
        assert s2.metadata["plan"] == "test"


class TestSessionManager:
    def _make_manager(self) -> SessionManager:
        tmp = tempfile.mkdtemp()
        return SessionManager(storage_dir=tmp)

    def test_create_session(self):
        mgr = self._make_manager()
        s = mgr.create_session()
        assert s.session_id in mgr._index

    def test_get_session_returns_same_object(self):
        mgr = self._make_manager()
        s = mgr.create_session(metadata={"key": "value"})
        loaded = mgr.get_session(s.session_id)
        assert loaded is not None
        assert loaded.metadata["key"] == "value"

    def test_list_sessions(self):
        mgr = self._make_manager()
        mgr.create_session()
        mgr.create_session()
        sessions = mgr.list_sessions()
        assert len(sessions) == 2

    def test_save_and_load_session(self):
        mgr = self._make_manager()
        s = mgr.create_session()
        s.add_message("user", "hello")
        s.add_message("assistant", "hi")
        mgr.save_session(s)

        # New manager from same storage
        mgr2 = SessionManager(storage_dir=mgr._storage)
        loaded = mgr2.get_session(s.session_id)
        assert loaded is not None
        assert len(loaded.messages) == 2
        assert loaded.messages[0].content == "hello"

    def test_delete_session(self):
        mgr = self._make_manager()
        s = mgr.create_session()
        mgr.save_session(s)
        path = mgr._session_file(s.session_id)
        assert path.exists()

        mgr.delete_session(s.session_id)
        assert not path.exists()
        assert s.session_id not in mgr._index

    def test_get_nonexistent_returns_none(self):
        mgr = self._make_manager()
        assert mgr.get_session("nonexistent") is None

    def test_persistence_file_format(self):
        mgr = self._make_manager()
        s = mgr.create_session()
        s.add_message("user", "test")
        mgr.save_session(s)

        path = mgr._session_file(s.session_id)
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["role"] == "user"
        assert data["content"] == "test"

    def test_index_file_created(self):
        mgr = self._make_manager()
        mgr.create_session()
        assert mgr._index_file.exists()
