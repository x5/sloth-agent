"""Integration tests for brainstorm router."""

import asyncio
from pathlib import Path
import sys
import uuid

import pytest
from httpx import ASGITransport, AsyncByteStream, AsyncClient, Response

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app
from app.services.brainstorm import AgentInfo, BrainstormEngine, SSEEvent


# ──────────────────────────────────────────────
# Streaming ASGI transport (SSE-compatible)
# ──────────────────────────────────────────────


class StreamingASGITransport:
    """ASGI transport that supports SSE streaming.

    httpx's built-in ASGITransport buffers ALL body parts and only returns the
    Response after ``app()`` completes (line 170 in httpx 0.28.1 asgi.py).  For
    persistent SSE connections the ASGI app never returns, so ``client.stream()``
    blocks forever and ``aiter_lines()`` is never reached.

    This transport runs ``app()`` in a background task and returns the Response
    immediately after ``http.response.start``, with body parts streamed through
    an asyncio.Queue.
    """

    def __init__(self, app, raise_app_exceptions=True, root_path="", client=("127.0.0.1", 123)):
        self.app = app
        self.raise_app_exceptions = raise_app_exceptions
        self.root_path = root_path
        self.client = client

    async def handle_async_request(self, request):
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": request.method,
            "headers": [(k.lower(), v) for (k, v) in request.headers.raw],
            "scheme": request.url.scheme,
            "path": request.url.path,
            "raw_path": request.url.raw_path.split(b"?")[0],
            "query_string": request.url.query,
            "server": (request.url.host, request.url.port),
            "client": self.client,
            "root_path": self.root_path,
        }

        request_body_chunks = request.stream.__aiter__()
        request_complete = False

        body_queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        start_message = asyncio.Event()
        response_complete = asyncio.Event()
        status_code = None
        response_headers = None
        app_error: Exception | None = None
        stream_ended = False

        async def receive():
            nonlocal request_complete
            if request_complete:
                await response_complete.wait()
                return {"type": "http.disconnect"}
            try:
                body = await request_body_chunks.__anext__()
            except StopAsyncIteration:
                request_complete = True
                return {"type": "http.request", "body": b"", "more_body": False}
            return {"type": "http.request", "body": body, "more_body": True}

        async def send(message):
            nonlocal status_code, response_headers, stream_ended
            if message["type"] == "http.response.start":
                status_code = message["status"]
                response_headers = message.get("headers", [])
                start_message.set()
            elif message["type"] == "http.response.body":
                body = message.get("body", b"")
                more_body = message.get("more_body", False)
                if body and request.method != "HEAD":
                    await body_queue.put(body)
                if not more_body:
                    stream_ended = True
                    await body_queue.put(None)
                    response_complete.set()

        async def run_app():
            nonlocal app_error
            try:
                await self.app(scope, receive, send)
            except Exception as e:
                app_error = e
            finally:
                start_message.set()
                if not stream_ended:
                    await body_queue.put(None)
                response_complete.set()

        asyncio.create_task(run_app())

        await start_message.wait()

        if app_error and self.raise_app_exceptions:
            raise app_error

        class _QueueStream(AsyncByteStream):
            def __init__(self, queue):
                self._queue = queue

            async def __aiter__(self):
                while True:
                    chunk = await self._queue.get()
                    if chunk is None:
                        break
                    yield chunk

        return Response(status_code, headers=response_headers, stream=_QueueStream(body_queue))

    async def aclose(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.aclose()


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


@pytest.mark.asyncio
async def test_disconnect_idle_session_persists_end_divider_and_marks_ended():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        insp_id = await _create_inspiration(client, "bs-disconnect-divider-test")
        sess = await _create_session(client, insp_id, "Divider Session")

        r = await client.delete(f"/api/brainstorm-sessions/{sess['id']}/connect")
        assert r.status_code == 200

        session_resp = await client.get(f"/api/brainstorm-sessions/{sess['id']}")
        assert session_resp.status_code == 200
        session_data = session_resp.json()
        assert session_data["status"] == "ended"
        assert session_data["ended_at"] is not None

        msgs_resp = await client.get(f"/api/inspirations/{insp_id}/messages?limit=200")
        assert msgs_resp.status_code == 200
        msgs = msgs_resp.json()
        assert any(
            m.get("role") == "system"
            and m.get("intent") == "divider_end"
            and m.get("brainstorm_session_id") == sess["id"]
            for m in msgs
        )


@pytest.mark.asyncio
async def test_interrupt_idle_session_returns_200_without_ending_mode():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        insp_id = await _create_inspiration(client, "bs-interrupt-idle-test")
        sess = await _create_session(client, insp_id)

        r = await client.delete(f"/api/brainstorm-sessions/{sess['id']}/interrupt")
        assert r.status_code == 200
        assert r.json()["status"] == "idle"

        session_resp = await client.get(f"/api/brainstorm-sessions/{sess['id']}")
        assert session_resp.status_code == 200
        assert session_resp.json()["status"] == "active"


@pytest.mark.asyncio
async def test_persistent_connect_inject_streams_user_and_agent_events(monkeypatch: pytest.MonkeyPatch):
    async def fake_load_agents(self):
        return [
            AgentInfo(
                id="agent-test-1",
                name="Lead Agent",
                role="lead",
                model="fake-model",
                system_prompt="You are a test agent.",
            )
        ]

    async def fake_run_persistent(self):
        """Mock run_persistent — emits fixed events directly."""
        agents = await self._load_agents()
        agent_indices = {a.id: (i + 1) for i, a in enumerate(agents)}
        msg_id = str(uuid.uuid4())

        yield SSEEvent(event="user_message", data={
            "message_id": msg_id,
            "content": "What should we build first?",
        })

        for agent in agents:
            yield SSEEvent(event="agent_start", data={
                "agent_id": agent.id,
                "agent_name": agent.name,
                "agent_number": agent_indices.get(agent.id),
            })
            for token in ("Hello", " world"):
                yield SSEEvent(event="agent_token", data={
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                    "token": token,
                })
                await asyncio.sleep(0)
            yield SSEEvent(event="message_done", data={
                "agent_id": agent.id,
                "agent_name": agent.name,
                "full_content": "Hello world",
            })

        yield SSEEvent(event="round_end", data={"round": 1, "speeches": len(agents)})
        yield SSEEvent(event="discussion_end", data={"summary": None, "message_count": 1})

    monkeypatch.setattr(BrainstormEngine, "_load_agents", fake_load_agents)
    monkeypatch.setattr(BrainstormEngine, "run_persistent", fake_run_persistent)

    transport = StreamingASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        insp_id = await _create_inspiration(client, "bs-persistent-happy-path-test")
        sess = await _create_session(client, insp_id)

        seen_events: list[tuple[str, dict]] = []
        discussion_ended = asyncio.Event()
        stream_closed = asyncio.Event()

        # The SSE stream reader runs as a background task.  aiter_lines() is an
        # async generator that blocks between each line waiting for the server
        # generator to produce more data.  Running it in a separate task allows
        # the main coroutine to call inject/disconnect while the reader is blocked,
        # which in turn lets the event loop drive the ASGI generator forward.
        async def stream_reader():
            current_event = ""
            async with client.stream(
                "POST",
                f"/api/brainstorm-sessions/{sess['id']}/connect",
            ) as response:
                assert response.status_code == 200
                async for line in response.aiter_lines():
                    if line.startswith("event: "):
                        current_event = line[7:].strip()
                    elif line.startswith("data: ") and current_event:
                        payload = __import__("json").loads(line[6:])
                        seen_events.append((current_event, payload))
                        if current_event == "discussion_end":
                            discussion_ended.set()
                            # Keep reading — the loop exits naturally once abort()
                            # injects a sentinel and run_persistent() returns.
            stream_closed.set()

        reader_task = asyncio.create_task(stream_reader())

        # fake_run_persistent emits all events immediately on connect.
        # Wait for discussion_end (stream will close naturally when generator is exhausted).
        await asyncio.wait_for(discussion_ended.wait(), timeout=10.0)

        # Give the stream a moment to close after the generator is exhausted.
        await asyncio.wait_for(stream_closed.wait(), timeout=5.0)

        if not reader_task.done():
            reader_task.cancel()
            try:
                await reader_task
            except asyncio.CancelledError:
                pass

    # Verify all expected SSE events were received
    event_names = [name for name, _ in seen_events]
    assert "user_message" in event_names
    assert "agent_start" in event_names
    assert "message_done" in event_names
    assert "round_end" in event_names
    assert "discussion_end" in event_names

    user_event = next(payload for name, payload in seen_events if name == "user_message")
    assert user_event["content"] == "What should we build first?"

    done_event = next(payload for name, payload in seen_events if name == "message_done")
    assert done_event["agent_name"] == "Lead Agent"
    assert done_event["full_content"] == "Hello world"
