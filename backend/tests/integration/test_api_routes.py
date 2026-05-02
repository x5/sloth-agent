from pathlib import Path
import sys

import pytest
from httpx import ASGITransport, AsyncClient


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app


@pytest.mark.asyncio
async def test_health_route_returns_ok():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.get('/api/health')

    assert response.status_code == 200
    payload = response.json()
    assert payload['status'] == 'ok'
    assert payload['version']


@pytest.mark.asyncio
async def test_echo_route_success_and_validation_error():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        ok_response = await client.post('/api/echo', json={'message': 'hello'})
        invalid_response = await client.post('/api/echo', json={})

    assert ok_response.status_code == 200
    assert ok_response.json() == {'echo': 'Backend received: hello'}
    assert invalid_response.status_code == 422
