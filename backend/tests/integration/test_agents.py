"""Integration tests for agents router (team member management)."""

from pathlib import Path
import sys

import pytest
from httpx import ASGITransport, AsyncClient

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app


@pytest.mark.asyncio
async def test_list_agents_for_nonexistent_inspiration_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.get('/api/inspirations/nonexistent-id/agents')

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_add_agent_to_nonexistent_inspiration_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.post(
            '/api/inspirations/nonexistent-id/agents',
            json={'template_id': 'nonexistent-template'},
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_nonexistent_agent_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.patch(
            '/api/agents/nonexistent-id',
            json={'model': 'gpt-4'},
        )

    assert response.status_code == 404
