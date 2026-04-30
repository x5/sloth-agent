import os
import shutil
from datetime import datetime, timezone

# Project root is two levels up from this file (backend/app/services/sandbox.py → project root)
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
BASE_DIR = os.path.join(_PROJECT_ROOT, "brainstorm-sessions")
ARCHIVE_DIR = os.path.join(BASE_DIR, ".archive")


class SandboxManager:

    @staticmethod
    def create_session_dir(session_id: str) -> str:
        """Create brainstorm-sessions/{session_id}/ and return absolute path."""
        session_dir = os.path.join(BASE_DIR, session_id)
        os.makedirs(session_dir, exist_ok=True)
        return os.path.abspath(session_dir)

    @staticmethod
    def get_session_path(session_id: str) -> str:
        return os.path.abspath(os.path.join(BASE_DIR, session_id))

    @staticmethod
    def get_file_tree(session_id: str) -> list[dict]:
        """Recursively list files in the sandbox directory."""
        session_dir = os.path.join(BASE_DIR, session_id)
        if not os.path.isdir(session_dir):
            return []
        entries = []
        for root, dirs, files in os.walk(session_dir):
            rel_root = os.path.relpath(root, session_dir)
            if rel_root == ".":
                rel_root = ""
            for name in sorted(dirs):
                entries.append({
                    "name": name,
                    "path": os.path.join(rel_root, name).replace("\\", "/"),
                    "type": "directory",
                    "size": 0,
                })
            for name in sorted(files):
                file_path = os.path.join(root, name)
                rel_path = os.path.join(rel_root, name).replace("\\", "/") if rel_root else name
                try:
                    size = os.path.getsize(file_path)
                except OSError:
                    size = 0
                entries.append({
                    "name": name,
                    "path": rel_path,
                    "type": "file",
                    "size": size,
                })
            dirs.clear()
        return entries

    @staticmethod
    def archive_session(session_id: str):
        session_dir = os.path.join(BASE_DIR, session_id)
        if not os.path.isdir(session_dir):
            return
        os.makedirs(ARCHIVE_DIR, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        dest = os.path.join(ARCHIVE_DIR, f"{session_id}-{ts}")
        shutil.move(session_dir, dest)

    @staticmethod
    def cleanup_archive(max_age_days: int = 7):
        if not os.path.isdir(ARCHIVE_DIR):
            return
        cutoff = datetime.now(timezone.utc).timestamp() - (max_age_days * 86400)
        for name in os.listdir(ARCHIVE_DIR):
            full = os.path.join(ARCHIVE_DIR, name)
            try:
                if os.path.isdir(full) and os.path.getmtime(full) < cutoff:
                    shutil.rmtree(full)
            except OSError:
                pass
