from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import async_session
from ..models import BrainstormFile, BrainstormSession, Inspiration
from ..services.sandbox import SandboxManager

router = APIRouter(prefix="/api", tags=["brainstorm"])


class CreateBrainstormSessionRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class UpdateBrainstormSessionRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    status: str | None = Field(default=None, pattern=r"^(active|cooling_down|ended|summarized)$")


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
