"""MemoryStore - Filesystem-based storage for sessions, scenarios, and shared knowledge."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class MemoryStore:
    """Filesystem storage layer managing sessions/ and scenarios/ directory structures."""

    def __init__(self, memory_root: Path):
        self.memory_root = memory_root
        self.sessions_dir = memory_root / "sessions"
        self.scenarios_dir = memory_root / "scenarios"
        self.shared_dir = memory_root / "shared"
        # Ensure directories exist
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.scenarios_dir.mkdir(parents=True, exist_ok=True)
        self.shared_dir.mkdir(parents=True, exist_ok=True)

    def save_session_message(self, session_id: str, role: str, content: str) -> None:
        """Append message to sessions/{session_id}/chat.jsonl."""
        chat_path = self.sessions_dir / session_id / "chat.jsonl"
        chat_path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "role": role,
            "content": content,
        }
        with chat_path.open("a") as f:
            f.write(json.dumps(entry) + "\n")

    def load_session_messages(self, session_id: str, limit: int | None = None) -> list[dict]:
        """Read chat.jsonl, optionally returning only the last n entries."""
        chat_path = self.sessions_dir / session_id / "chat.jsonl"
        if not chat_path.exists():
            return []
        lines = chat_path.read_text().strip().splitlines()
        entries = [json.loads(line) for line in lines if line.strip()]
        if limit is not None:
            return entries[-limit:]
        return entries

    def save_session_context(self, session_id: str, context: dict) -> None:
        """Save context summary to sessions/{session_id}/context.json."""
        path = self.sessions_dir / session_id / "context.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(context, indent=2))

    def load_session_context(self, session_id: str) -> dict | None:
        """Load context summary from sessions/{session_id}/context.json."""
        path = self.sessions_dir / session_id / "context.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def save_phase_input(self, scenario_id: str, phase_id: str, data: dict) -> None:
        """Save phase input to scenarios/{scenario}/{phase}/input.json."""
        path = self.scenarios_dir / scenario_id / phase_id / "input.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2))

    def save_phase_output(self, scenario_id: str, phase_id: str, data: dict) -> None:
        """Save phase output to scenarios/{scenario}/{phase}/output.json."""
        path = self.scenarios_dir / scenario_id / phase_id / "output.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2))

    def load_phase_input(self, scenario_id: str, phase_id: str) -> dict | None:
        """Load phase input from scenarios/{scenario}/{phase}/input.json."""
        path = self.scenarios_dir / scenario_id / phase_id / "input.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def load_phase_output(self, scenario_id: str, phase_id: str) -> dict | None:
        """Load phase output from scenarios/{scenario}/{phase}/output.json."""
        path = self.scenarios_dir / scenario_id / phase_id / "output.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def save_phase_message(
        self, scenario_id: str, phase_id: str, role: str, content: str
    ) -> None:
        """Append phase dialogue to scenarios/{scenario}/{phase}/chat.jsonl."""
        path = self.scenarios_dir / scenario_id / phase_id / "chat.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "role": role,
            "content": content,
        }
        with path.open("a") as f:
            f.write(json.dumps(entry) + "\n")

    def save_artifact(
        self, scenario_id: str, phase_id: str, filename: str, content: bytes
    ) -> None:
        """Save phase artifact to scenarios/{scenario}/{phase}/artifacts/{filename}."""
        path = self.scenarios_dir / scenario_id / phase_id / "artifacts" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def save_knowledge(self, key: str, content: dict) -> None:
        """Save shared knowledge to shared/knowledge/{key}.json."""
        path = self.shared_dir / "knowledge" / f"{key}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(content, indent=2))

    def load_knowledge(self, key: str) -> dict | None:
        """Load shared knowledge from shared/knowledge/{key}.json."""
        path = self.shared_dir / "knowledge" / f"{key}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())
