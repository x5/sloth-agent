"""Integration tests for brainstorm router."""

from pathlib import Path
import sys

import pytest
from httpx import ASGITransport, AsyncClient

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

async def _create_inspiration(client: AsyncClient, name: str = "brainstorm-test") -> str:
    r = await client.post("/api/inspirations", json={"name": name})
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _create_session(client: AsyncClient, inspiration_id: str, title: str = "Test Session") -> dict:
    r = await client.post(
        f"/api/inspirations/{inspiration_id}/brainstorm-sessions",
        json={"title": title},
    )
    assert r.status_code == 201, r.text
    return r.json()


# ──────────────────────────────────────────────
# Error path (original tests)
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_brainstorm_session_for_nonexistent_inspiration_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/inspirations/nonexistent-id/brainstorm-sessions",
            json={"title": "Test Session"},
        )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_brainstorm_sessions_for_nonexistent_inspiration_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/inspirations/nonexistent-id/brainstorm-sessions")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_nonexistent_brainstorm_session_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/brainstorm-sessions/nonexistent-id")
    assert response.status_code == 404


# ──────────────────────────────────────────────
# Create / Read happy paths
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_brainstorm_session_returns_201_with_required_fields():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        insp_id = await _create_inspiration(client, "bs-create-test")
        sess = await _create_session(client, insp_id, "My Session")

    assert sess["id"]
    assert sess["inspiration_id"] == insp_id
    assert sess["title"] == "My Session"
    assert sess["status"] == "active"
    assert sess["sandbox_path"]
    assert sess["max_messages"] == 1000
    assert sess["cooldown_seconds"] == 5
    assert sess["message_count"] == 0


@pytest.mark.asyncio
async def test_list_brainstorm_sessions_returns_created_session():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        insp_id = await _create_inspiration(client, "bs-list-test")
        sess = await _create_session(client, insp_id, "Listed Session")
        r = await client.get(f"/api/inspirations/{insp_id}/brainstorm-sessions")

    assert r.status_code == 200
    ids = [s["id"] for s in r.json()]
    assert sess["id"] in ids


@pytest.mark.asyncio
async def test_get_brainstorm_session_by_id():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        insp_id = await _create_inspiration(client, "bs-get-test")
        sess = await _create_session(client, insp_id)
        r = await client.get(f"/api/brainstorm-sessions/{sess['id']}")

    assert r.status_code == 200
    assert r.json()["id"] == sess["id"]


# ──────────────────────────────────────────────
# Patch (update) tests
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_patch_brainstorm_session_title():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        insp_id = await _create_inspiration(client, "bs-patch-title-test")
        sess = await _create_session(client, insp_id, "Original Title")
        r = await client.patch(
            f"/api/brainstorm-sessions/{sess['id']}",
            json={"title": "Updated Title"},
        )

    assert r.status_code == 200
    assert r.json()["title"] == "Updated Title"


@pytest.mark.asyncio
async def test_patch_brainstorm_session_status_to_ended():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        insp_id = await _create_inspiration(client, "bs-patch-status-test")
        sess = await _create_session(client, insp_id)
        r = await client.patch(
            f"/api/brainstorm-sessions/{sess['id']}",
            json={"status": "ended"},
        )

    assert r.status_code == 200
    assert r.json()["status"] == "ended"


@pytest.mark.asyncio
async def test_patch_nonexistent_session_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.patch(
            "/api/brainstorm-sessions/00000000-0000-0000-0000-000000000000",
            json={"title": "New"},
        )
    assert r.status_code == 404


# ──────────────────────────────────────────────
# Discuss endpoint guard tests
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_discuss_on_ended_session_returns_400():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        insp_id = await _create_inspiration(client, "bs-ended-discuss-test")
        sess = await _create_session(client, insp_id)
        await client.patch(
            f"/api/brainstorm-sessions/{sess['id']}",
            json={"status": "ended"},
        )
        r = await client.post(
            f"/api/brainstorm-sessions/{sess['id']}/discuss",
            json={"content": "hello"},
        )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_abort_discuss_on_idle_session_returns_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        insp_id = await _create_inspiration(client, "bs-abort-test")
        sess = await _create_session(client, insp_id)
        r = await client.delete(f"/api/brainstorm-sessions/{sess['id']}/discuss")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_discuss_on_nonexistent_session_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post(
            "/api/brainstorm-sessions/00000000-0000-0000-0000-000000000000/discuss",
            json={"content": "hello"},
        )
    assert r.status_code == 404


# ──────────────────────────────────────────────
# Persistent connection endpoints (Iter-6)
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_connect_nonexistent_session_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post(
            "/api/brainstorm-sessions/nonexistent-id/connect",
        )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_connect_ended_session_returns_400():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        insp_id = await _create_inspiration(client, "bs-connect-ended-test")
        sess = await _create_session(client, insp_id)
        await client.patch(
            f"/api/brainstorm-sessions/{sess['id']}",
            json={"status": "ended"},
        )
        r = await client.post(f"/api/brainstorm-sessions/{sess['id']}/connect")
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_inject_without_connection_returns_400():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        insp_id = await _create_inspiration(client, "bs-inject-no-conn-test")
        sess = await _create_session(client, insp_id)
        r = await client.post(
            f"/api/brainstorm-sessions/{sess['id']}/inject",
            json={"content": "hello"},
        )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_inject_nonexistent_session_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post(
            "/api/brainstorm-sessions/nonexistent-id/inject",
            json={"content": "hello"},
        )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_disconnect_idle_session_returns_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        insp_id = await _create_inspiration(client, "bs-disconnect-idle-test")
        sess = await _create_session(client, insp_id)
        r = await client.delete(f"/api/brainstorm-sessions/{sess['id']}/connect")
    assert r.status_code == 200
    assert r.json()["status"] == "disconnected"
