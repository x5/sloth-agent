"""SessionManager — create/load/save chat sessions with filesystem persistence."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class SessionMessage:
    """One message in a chat session."""

    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: float = 0
    tokens: int = 0

    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time()


@dataclass
class ChatSession:
    """A single chat session."""

    session_id: str = ""
    created_at: float = 0
    updated_at: float = 0
    messages: list[SessionMessage] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.session_id:
            self.session_id = uuid.uuid4().hex[:12]
        if self.created_at == 0:
            self.created_at = time.time()
        self.updated_at = time.time()

    def add_message(self, role: str, content: str) -> SessionMessage:
        msg = SessionMessage(role=role, content=content)
        self.messages.append(msg)
        self.updated_at = time.time()
        return msg

    def get_messages_for_llm(self, max_turns: int = 20) -> list[dict]:
        """Return messages formatted for LLM API, with truncation."""
        messages = self.messages
        # Keep system prompt + last N turns
        system_msgs = [m for m in messages if m.role == "system"]
        other_msgs = [m for m in messages if m.role != "system"]
        recent = other_msgs[-(max_turns * 2):]  # 2 msgs per turn
        result = []
        for m in system_msgs:
            result.append({"role": m.role, "content": m.content})
        for m in recent:
            result.append({"role": m.role, "content": m.content})
        return result

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
            "messages": [
                {"role": m.role, "content": m.content, "timestamp": m.timestamp, "tokens": m.tokens}
                for m in self.messages
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> ChatSession:
        messages = [
            SessionMessage(
                role=m["role"], content=m["content"],
                timestamp=m.get("timestamp", 0), tokens=m.get("tokens", 0),
            )
            for m in data.get("messages", [])
        ]
        return cls(
            session_id=data["session_id"],
            created_at=data.get("created_at", 0),
            updated_at=data.get("updated_at", 0),
            messages=messages,
            metadata=data.get("metadata", {}),
        )


class SessionManager:
    """Manage chat session lifecycle with filesystem persistence.

    Sessions are stored under <storage_dir>/sessions/chat/<session_id>.jsonl.
    A sessions index is kept at <storage_dir>/sessions/index.json.
    """

    def __init__(self, storage_dir: Path | str | None = None):
        self._storage = Path(storage_dir) if storage_dir else Path.cwd() / ".sloth" / "sessions"
        self._chat_dir = self._storage / "chat"
        self._chat_dir.mkdir(parents=True, exist_ok=True)
        self._index_file = self._storage / "index.json"
        self._sessions: dict[str, ChatSession] = {}
        self._load_index()

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def create_session(self, metadata: dict | None = None) -> ChatSession:
        """Create a new chat session."""
        session = ChatSession(metadata=metadata or {})
        self._sessions[session.session_id] = session
        self._index[session.session_id] = {
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "message_count": 0,
        }
        self._save_index()
        return session

    def get_session(self, session_id: str) -> ChatSession | None:
        """Get an existing session."""
        if session_id in self._sessions:
            return self._sessions[session_id]

        # Try loading from disk
        session = self._load_session(session_id)
        if session:
            self._sessions[session_id] = session
        return session

    def list_sessions(self) -> list[dict]:
        """List all sessions with basic info."""
        sessions = []
        for sid, meta in self._index.items():
            sessions.append({
                "id": sid,
                "created_at": meta.get("created_at"),
                "updated_at": meta.get("updated_at"),
                "message_count": meta.get("message_count", 0),
            })
        return sorted(sessions, key=lambda s: s["updated_at"], reverse=True)

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and its file."""
        self._sessions.pop(session_id, None)
        self._index.pop(session_id, None)
        path = self._session_file(session_id)
        if path.exists():
            path.unlink()
        self._save_index()
        return True

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_session(self, session: ChatSession) -> None:
        """Persist session to JSONL file."""
        path = self._session_file(session.session_id)
        with path.open("w", encoding="utf-8") as f:
            for msg in session.messages:
                f.write(json.dumps({
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp,
                    "tokens": msg.tokens,
                }) + "\n")

        # Update index
        self._index[session.session_id] = {
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "message_count": len(session.messages),
        }
        self._save_index()

    def _load_session(self, session_id: str) -> ChatSession | None:
        """Load a session from JSONL file."""
        path = self._session_file(session_id)
        if not path.exists():
            return None

        messages = []
        metadata = {}
        created_at = 0
        updated_at = 0

        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            if "_meta" in data:
                metadata = data["_meta"]
                created_at = data.get("created_at", 0)
                updated_at = data.get("updated_at", 0)
            else:
                messages.append(SessionMessage(
                    role=data["role"], content=data["content"],
                    timestamp=data.get("timestamp", 0), tokens=data.get("tokens", 0),
                ))

        # Read metadata from index
        idx = self._index.get(session_id, {})
        if created_at == 0:
            created_at = idx.get("created_at", time.time())
        if updated_at == 0:
            updated_at = idx.get("updated_at", time.time())

        return ChatSession(
            session_id=session_id,
            created_at=created_at,
            updated_at=updated_at,
            messages=messages,
            metadata=metadata,
        )

    def _session_file(self, session_id: str) -> Path:
        return self._chat_dir / f"{session_id}.jsonl"

    # ------------------------------------------------------------------
    # Index
    # ------------------------------------------------------------------

    @property
    def _index(self) -> dict:
        """Lazy-load index."""
        if not hasattr(self, "_index_cache"):
            self._index_cache = {}
            if self._index_file.exists():
                try:
                    self._index_cache = json.loads(
                        self._index_file.read_text(encoding="utf-8")
                    )
                except (json.JSONDecodeError, IOError):
                    self._index_cache = {}
        return self._index_cache

    def _load_index(self) -> None:
        """Trigger index load."""
        _ = self._index

    def _save_index(self) -> None:
        """Save index to disk."""
        self._index_file.write_text(
            json.dumps(self._index, indent=2), encoding="utf-8"
        )
