import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import async_session
from ..models import BrainstormFile, BrainstormSession, Inspiration, Message
from ..services.brainstorm import BrainstormEngine
from ..services.sandbox import SandboxManager

router = APIRouter(prefix="/api", tags=["brainstorm"])

# Track active engines for abort support
# DEPRECATED: used only by /discuss endpoints (one-shot SSE). Remove in Iter-7.
_active_engines: dict[str, BrainstormEngine] = {}

# Track persistent connections for /connect endpoints (Iter-6+)
_active_connections: dict[str, BrainstormEngine] = {}


class CreateBrainstormSessionRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class UpdateBrainstormSessionRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    status: str | None = Field(default=None, pattern=r"^(active|cooling_down|ended|summarized)$")


class DiscussRequest(BaseModel):
    content: str = Field(min_length=1)
    reply_to_message_id: str | None = None


class InjectRequest(BaseModel):
    content: str = Field(min_length=1)
    reply_to_message_id: str | None = None


class BrainstormSessionResponse(BaseModel):
    id: str
    inspiration_id: str
    title: str
    status: str
    sandbox_path: str
    max_messages: int
    cooldown_seconds: int
    message_count: int
    summary: str | None
    started_by: str | None
    notification_sent: bool
    created_at: datetime
    ended_at: datetime | None
    file_tree: list[dict] = []

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def ensure_utc(self):
        for field_name in ("created_at", "ended_at"):
            dt = getattr(self, field_name)
            if dt is not None and dt.tzinfo is None:
                setattr(self, field_name, dt.replace(tzinfo=timezone.utc))
        return self


async def get_db():
    async with async_session() as session:
        yield session


@router.post(
    "/inspirations/{inspiration_id}/brainstorm-sessions",
    response_model=BrainstormSessionResponse,
    status_code=201,
)
async def create_brainstorm_session(
    inspiration_id: str,
    req: CreateBrainstormSessionRequest,
    db: AsyncSession = Depends(get_db),
):
    inspiration = await db.get(Inspiration, inspiration_id)
    if not inspiration:
        raise HTTPException(status_code=404, detail="Inspiration not found")

    session = BrainstormSession(
        inspiration_id=inspiration_id,
        title=req.title,
        sandbox_path="",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    sandbox_path = SandboxManager.create_session_dir(session.id)
    session.sandbox_path = sandbox_path

    # Persist a timeline divider as a system message.
    db.add(
        Message(
            inspiration_id=inspiration_id,
            role="system",
            content=f"{session.title} Started",
            mode="brainstorm",
            brainstorm_session_id=session.id,
            intent="divider_start",
            round=1,
            truncated=False,
        )
    )
    await db.commit()
    await db.refresh(session)

    return _session_to_response(session)


@router.get(
    "/inspirations/{inspiration_id}/brainstorm-sessions",
    response_model=list[BrainstormSessionResponse],
)
async def list_brainstorm_sessions(
    inspiration_id: str,
    db: AsyncSession = Depends(get_db),
):
    inspiration = await db.get(Inspiration, inspiration_id)
    if not inspiration:
        raise HTTPException(status_code=404, detail="Inspiration not found")

    result = await db.execute(
        select(BrainstormSession)
        .where(BrainstormSession.inspiration_id == inspiration_id)
        .order_by(BrainstormSession.created_at.desc())
    )
    sessions = list(result.scalars().all())
    return [_session_to_response(s) for s in sessions]


@router.get(
    "/brainstorm-sessions/{session_id}",
    response_model=BrainstormSessionResponse,
)
async def get_brainstorm_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    session = await db.get(BrainstormSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Brainstorm session not found")
    return _session_to_response(session)


@router.patch(
    "/brainstorm-sessions/{session_id}",
    response_model=BrainstormSessionResponse,
)
async def update_brainstorm_session(
    session_id: str,
    req: UpdateBrainstormSessionRequest,
    db: AsyncSession = Depends(get_db),
):
    session = await db.get(BrainstormSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Brainstorm session not found")

    if req.title is not None:
        session.title = req.title
    if req.status is not None:
        session.status = req.status
        if req.status == "ended":
            session.ended_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(session)
    return _session_to_response(session)


def _session_to_response(session: BrainstormSession) -> BrainstormSessionResponse:
    file_tree = SandboxManager.get_file_tree(session.id)
    return BrainstormSessionResponse(
        id=session.id,
        inspiration_id=session.inspiration_id,
        title=session.title,
        status=session.status,
        sandbox_path=session.sandbox_path,
        max_messages=session.max_messages,
        cooldown_seconds=session.cooldown_seconds,
        message_count=session.message_count,
        summary=session.summary,
        started_by=session.started_by,
        notification_sent=session.notification_sent,
        created_at=session.created_at,
        ended_at=session.ended_at,
        file_tree=file_tree,
    )


@router.post("/brainstorm-sessions/{session_id}/discuss")
async def brainstorm_discuss(
    session_id: str,
    req: DiscussRequest,
    db: AsyncSession = Depends(get_db),
):
    """[DEPRECATED — remove in Iter-7] One-shot SSE discussion endpoint.

    Each call creates a new engine, streams one round of agent responses,
    then closes. Replaced by POST /connect + POST /inject (persistent connection).
    """
    session = await db.get(BrainstormSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Brainstorm session not found")

    if session.status == "ended":
        raise HTTPException(status_code=400, detail="Brainstorm session has ended")

    engine = BrainstormEngine(
        session_id=session_id,
        inspiration_id=session.inspiration_id,
        cooldown_seconds=session.cooldown_seconds,
        max_messages=session.max_messages,
    )

    # Register engine for abort support
    _active_engines[session_id] = engine

    async def event_stream():
        try:
            async for sse_event in engine.run(
                user_content=req.content,
                reply_to_message_id=req.reply_to_message_id,
            ):
                data_str = json.dumps(sse_event.data, ensure_ascii=False)
                yield f"event: {sse_event.event}\ndata: {data_str}\n\n"
        except Exception as e:
            error_data = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"event: error\ndata: {error_data}\n\n"
        finally:
            # Only remove if this engine is still the registered one (avoid evicting a newer engine)
            if _active_engines.get(session_id) is engine:
                _active_engines.pop(session_id, None)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.delete("/brainstorm-sessions/{session_id}/discuss")
async def abort_discussion(session_id: str):
    """[DEPRECATED — remove in Iter-7] Abort a one-shot discussion. Use DELETE /connect instead."""
    engine = _active_engines.get(session_id)
    if engine:
        engine.abort()
    return {"status": "aborted"}


# ---- Persistent connection endpoints (Iter-6) ----

@router.post("/brainstorm-sessions/{session_id}/connect")
async def brainstorm_connect(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Establish a persistent SSE connection for brainstorm discussions.

    The stream stays open indefinitely, emitting events as agents speak.
    Use POST /inject to push user messages, DELETE /connect to close.
    """
    session = await db.get(BrainstormSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Brainstorm session not found")

    if session.status == "ended":
        raise HTTPException(status_code=400, detail="Brainstorm session has ended")

    # Disconnect any existing persistent connection for this session
    existing = _active_connections.get(session_id)
    if existing:
        existing.abort()

    engine = BrainstormEngine(
        session_id=session_id,
        inspiration_id=session.inspiration_id,
        cooldown_seconds=session.cooldown_seconds,
        max_messages=session.max_messages,
    )
    _active_connections[session_id] = engine

    async def event_stream():
        try:
            async for sse_event in engine.run_persistent():
                data_str = json.dumps(sse_event.data, ensure_ascii=False)
                yield f"event: {sse_event.event}\ndata: {data_str}\n\n"
        except Exception as e:
            error_data = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"event: error\ndata: {error_data}\n\n"
        finally:
            # Only remove if this engine is still the registered one (avoid evicting a newer engine on reconnect)
            if _active_connections.get(session_id) is engine:
                _active_connections.pop(session_id, None)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/brainstorm-sessions/{session_id}/inject", status_code=202)
async def brainstorm_inject(
    session_id: str,
    req: InjectRequest,
    db: AsyncSession = Depends(get_db),
):
    """Inject a user message into an active persistent connection (non-blocking).

    Returns 202 immediately; message is processed asynchronously by the engine.
    """
    session = await db.get(BrainstormSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Brainstorm session not found")

    if session.status == "ended":
        raise HTTPException(status_code=400, detail="Brainstorm session has ended")

    engine = _active_connections.get(session_id)
    if not engine:
        raise HTTPException(
            status_code=400,
            detail="No active connection for this session. Call POST /connect first.",
        )

    await engine.inject(req.content, req.reply_to_message_id)
    return {"status": "injected"}


@router.delete("/brainstorm-sessions/{session_id}/connect")
async def brainstorm_disconnect(session_id: str, db: AsyncSession = Depends(get_db)):
    """Close the persistent SSE connection for a brainstorm session."""
    engine = _active_connections.pop(session_id, None)
    if engine:
        engine.abort()

    # Persist ended state and divider_end regardless of whether the connection
    # is still active. This keeps timeline events consistent when clients abort early.
    session = await db.get(BrainstormSession, session_id)
    if session:
        if session.status != "ended":
            session.status = "ended"
            session.ended_at = datetime.now(timezone.utc)

        existing_end = await db.execute(
            select(Message.id)
            .where(
                Message.brainstorm_session_id == session.id,
                Message.role == "system",
                Message.intent == "divider_end",
            )
            .limit(1)
        )
        if existing_end.scalar_one_or_none() is None:
            db.add(
                Message(
                    inspiration_id=session.inspiration_id,
                    role="system",
                    content=f"{session.title} Ended",
                    mode="brainstorm",
                    brainstorm_session_id=session.id,
                    intent="divider_end",
                    round=1,
                    truncated=False,
                )
            )
        await db.commit()
    return {"status": "disconnected"}


@router.delete("/brainstorm-sessions/{session_id}/interrupt")
async def brainstorm_interrupt(session_id: str, db: AsyncSession = Depends(get_db)):
    """Interrupt only the current brainstorm round without ending the session."""
    session = await db.get(BrainstormSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Brainstorm session not found")

    engine = _active_connections.get(session_id)
    if engine:
        engine.interrupt_round()
        return {"status": "interrupted"}

    engine = _active_engines.get(session_id)
    if engine:
        engine.interrupt_round()
        return {"status": "interrupted"}

    return {"status": "idle"}
