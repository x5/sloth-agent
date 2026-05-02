"""Integration tests for chat router."""

from pathlib import Path
import sys

import pytest
from httpx import ASGITransport, AsyncClient

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app


@pytest.mark.asyncio
async def test_get_messages_for_nonexistent_inspiration_returns_empty():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.get('/api/inspirations/nonexistent-id/messages')

    # Returns 200 with empty list (no 404 for messages endpoint)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_chat_without_lead_agent_returns_400():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.post(
            '/api/inspirations/nonexistent-id/chat',
            json={'content': 'Hello'},
        )

    assert response.status_code in (400, 404)


@pytest.mark.asyncio
async def test_chat_stream_without_lead_agent_returns_error():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.post(
            '/api/inspirations/nonexistent-id/chat/stream',
            json={'content': 'Hello'},
        )

    assert response.status_code in (400, 404)
