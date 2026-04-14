"""Memory Store - SQLite based storage for short and long term memory."""

import json
from datetime import datetime, timedelta
from pathlib import Path

import chromadb
from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from sloth_agent.core.config import Config

Base = declarative_base()


class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    id = Column(Integer, primary_key=True)
    task_id = Column(String)
    date = Column(String)
    content = Column(Text)
    summary = Column(Text, nullable=True)
    embedding = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class MemoryStore:
    """Manages short-term and long-term memory storage."""

    def __init__(self, config: Config):
        self.config = config
        self._init_sqlite()
        self._init_vector_db()

    def _init_sqlite(self):
        """Initialize SQLite database."""
        db_path = self.config.memory.sqlite_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self.engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def _init_vector_db(self):
        """Initialize Chroma vector database."""
        vector_path = self.config.memory.vector_db_path
        Path(vector_path).parent.mkdir(parents=True, exist_ok=True)

        self.chroma_client = chromadb.PersistentClient(path=vector_path)
        self.collection = self.chroma_client.get_or_create_collection(
            "memory_embeddings"
        )

    def save_execution_log(self, task_id: str, date: str, content: dict):
        """Save execution log to both SQLite and vector DB."""
        session = self.SessionLocal()

        try:
            # Save to SQLite
            log = ExecutionLog(
                task_id=task_id,
                date=date,
                content=json.dumps(content),
            )
            session.add(log)
            session.commit()

            # Generate embedding and save to Chroma
            # TODO: Use embedding model
            embedding = [0.0] * 768  # Placeholder

            self.collection.add(
                ids=[str(log.id)],
                embeddings=[embedding],
                documents=json.dumps(content),
                metadatas=[{"task_id": task_id, "date": date}],
            )

        finally:
            session.close()

    def load_report(self, date: str) -> dict | None:
        """Load report for a specific date."""
        session = self.SessionLocal()
        try:
            log = (
                session.query(ExecutionLog)
                .filter(ExecutionLog.date == date)
                .order_by(ExecutionLog.id.desc())
                .first()
            )
            if log:
                return json.loads(log.content)
            return None
        finally:
            session.close()

    def cleanup_old_logs(self):
        """Remove logs older than retention period."""
        session = self.SessionLocal()
        try:
            cutoff = datetime.now() - timedelta(
                days=self.config.memory.short_term_retention_days
            )
            session.query(ExecutionLog).filter(
                ExecutionLog.created_at < cutoff
            ).delete()
            session.commit()
        finally:
            session.close()
