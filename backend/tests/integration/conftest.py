"""Integration test fixtures — sets up an in-memory SQLite database per test session."""

import sys
from pathlib import Path

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Import models so all table metadata is registered on Base before create_all
import app.models  # noqa: F401
from app.database import Base
from app.main import app
from app.routers import agents, agent_templates, brainstorm, chat, inspirations, llm

TEST_DATABASE_URL = "sqlite+aiosqlite://"  # shared in-memory DB for the whole session


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_database():
    """
    Create all tables in an in-memory SQLite DB and wire it into the app via
    FastAPI dependency_overrides — the only approach that works when routers do
    `from ..database import async_session` (module-level binding).
    """
    test_engine = create_async_engine(TEST_DATABASE_URL)
    test_session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def get_test_db():
        async with test_session_factory() as session:
            yield session

    # Override every router's get_db with the test DB session
    for router_module in (agents, agent_templates, brainstorm, chat, inspirations, llm):
        app.dependency_overrides[router_module.get_db] = get_test_db

    yield

    app.dependency_overrides.clear()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()
