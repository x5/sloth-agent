"""Integration tests for LLM config router."""

from pathlib import Path
import sys

import pytest
from httpx import ASGITransport, AsyncClient

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app


@pytest.mark.asyncio
async def test_list_llm_configs_returns_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.get('/api/settings/llm')

    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_create_llm_config_with_short_key_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.post('/api/settings/llm', json={
            'provider': 'openai',
            'model': 'gpt-4',
            'api_key': 'short',
            'base_url': 'https://api.openai.com/v1',
        })

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_nonexistent_llm_config_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.patch(
            '/api/settings/llm/nonexistent-id',
            json={'model': 'gpt-4-turbo'},
        )

    assert response.status_code == 404
