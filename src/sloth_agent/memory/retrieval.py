"""Memory Retrieval - Search and retrieval from memory stores."""

from typing import Any

import chromadb
from sqlalchemy import or_

from sloth_agent.core.config import Config
from sloth_agent.memory.store import ExecutionLog, MemoryStore


class MemoryRetrieval:
    """Retrieves relevant memories using hybrid search."""

    def __init__(self, config: Config):
        self.config = config
        self.store = MemoryStore(config)

    def search_skills(self, query: str, top_k: int = 5) -> list[dict]:
        """Search for relevant skills using vector similarity."""
        # TODO: Use actual embedding model
        # For now, return from FTS search
        return self._fts_search(query, top_k)

    def _fts_search(self, query: str, top_k: int) -> list[dict]:
        """Full-text search using SQLite FTS5."""
        session = self.store.SessionLocal()
        try:
            # Simple LIKE search (replace with FTS5 when schema supports it)
            results = (
                session.query(ExecutionLog)
                .filter(
                    or_(
                        ExecutionLog.content.contains(query),
                        ExecutionLog.summary.contains(query),
                    )
                )
                .limit(top_k)
                .all()
            )

            return [
                {
                    "task_id": r.task_id,
                    "date": r.date,
                    "content": r.content,
                    "summary": r.summary,
                }
                for r in results
            ]
        finally:
            session.close()

    def search_execution_history(self, query: str, days: int = 7) -> list[dict]:
        """Search execution history within specified days."""
        # TODO: Implement with date filtering
        return []

    def get_context_for_task(self, task_description: str) -> dict[str, Any]:
        """Build context for a task from memory."""
        skills = self.search_skills(task_description, top_k=3)
        history = self.search_execution_history(task_description, days=7)

        return {
            "relevant_skills": skills,
            "execution_history": history,
        }
