"""Integration tests for brainstorm router."""

from pathlib import Path
import sys

import pytest
from httpx import ASGITransport, AsyncClient

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app


@pytest.mark.asyncio
async def test_create_brainstorm_session_for_nonexistent_inspiration_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.post(
            '/api/inspirations/nonexistent-id/brainstorm-sessions',
            json={'title': 'Test Session'},
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_brainstorm_sessions_for_nonexistent_inspiration_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.get('/api/inspirations/nonexistent-id/brainstorm-sessions')

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_nonexistent_brainstorm_session_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.get('/api/brainstorm-sessions/nonexistent-id')

    assert response.status_code == 404
