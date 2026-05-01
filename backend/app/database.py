import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

DB_PATH = os.environ.get("SLOTH_DB_PATH", os.path.join(os.path.dirname(__file__), "..", "sloth.db"))
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def _migrate_db():
    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
        )
        if not result.first():
            return
        result = await conn.execute(text("PRAGMA table_info(messages)"))
        cols = {row[1] for row in result.fetchall()}
        if "mode" not in cols:
            await conn.execute(text("ALTER TABLE messages ADD COLUMN mode TEXT NOT NULL DEFAULT 'chat'"))
        if "brainstorm_session_id" not in cols:
            await conn.execute(text("ALTER TABLE messages ADD COLUMN brainstorm_session_id TEXT"))
        if "parent_message_id" not in cols:
            await conn.execute(text("ALTER TABLE messages ADD COLUMN parent_message_id TEXT"))
        if "round" not in cols:
            await conn.execute(text("ALTER TABLE messages ADD COLUMN round INTEGER NOT NULL DEFAULT 1"))
        if "intent" not in cols:
            await conn.execute(text("ALTER TABLE messages ADD COLUMN intent TEXT"))
        if "truncated" not in cols:
            await conn.execute(text("ALTER TABLE messages ADD COLUMN truncated INTEGER NOT NULL DEFAULT 0"))


async def init_db():
    await _migrate_db()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
