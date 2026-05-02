"""Integration tests for agent_templates router (GET /api/settings/agents)."""

from pathlib import Path
import sys

import pytest
from httpx import ASGITransport, AsyncClient

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app


@pytest.mark.asyncio
async def test_list_agent_templates_returns_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.get('/api/settings/agents')

    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_nonexistent_template_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.get('/api/settings/agents/nonexistent-id')

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_nonexistent_template_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.patch(
            '/api/settings/agents/nonexistent-id',
            json={'name': 'Updated'},
        )

    assert response.status_code == 404
