from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import async_session
from ..models import Inspiration, InspirationAgent, Message
from ..services.agent import AgentService

router = APIRouter(prefix="/api/inspirations", tags=["inspirations"])


class CreateInspirationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class InspirationResponse(BaseModel):
    id: str
    name: str
    agent_count: int = 0
    latest_message_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def ensure_utc(self):
        for field_name in ("created_at", "updated_at", "latest_message_at"):
            dt = getattr(self, field_name)
            if dt is not None and dt.tzinfo is None:
                setattr(self, field_name, dt.replace(tzinfo=timezone.utc))
        return self


async def get_db():
    async with async_session() as session:
        yield session


@router.post("", response_model=InspirationResponse, status_code=201)
async def create_inspiration(req: CreateInspirationRequest, db: AsyncSession = Depends(get_db)):
    inspiration = Inspiration(name=req.name)
    db.add(inspiration)
    await db.commit()
    await db.refresh(inspiration)
    await AgentService.join_auto_agents(inspiration.id)
    return inspiration


@router.get("", response_model=list[InspirationResponse])
async def list_inspirations(q: str | None = None, db: AsyncSession = Depends(get_db)):
    stmt = select(Inspiration).order_by(Inspiration.updated_at.desc())
    if q:
        stmt = stmt.where(Inspiration.name.ilike(f"%{q}%"))
    result = await db.execute(stmt)
    inspirations = list(result.scalars().all())

    # Attach agent_count and latest_message_at
    out = []
    for insp in inspirations:
        # Agent count
        count_result = await db.execute(
            select(InspirationAgent).where(InspirationAgent.inspiration_id == insp.id)
        )
        agent_count = len(count_result.scalars().all())

        # Latest message time
        msg_result = await db.execute(
            select(Message.created_at)
            .where(Message.inspiration_id == insp.id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        latest_msg = msg_result.scalar_one_or_none()

        out.append(InspirationResponse(
            id=insp.id,
            name=insp.name,
            agent_count=agent_count,
            latest_message_at=latest_msg,
            created_at=insp.created_at,
            updated_at=insp.updated_at,
        ))

    return out


@router.get("/{inspiration_id}", response_model=InspirationResponse)
async def get_inspiration(inspiration_id: str, db: AsyncSession = Depends(get_db)):
    inspiration = await db.get(Inspiration, inspiration_id)
    if not inspiration:
        raise HTTPException(status_code=404, detail="Inspiration not found")
    return inspiration


@router.delete("/{inspiration_id}", status_code=204)
async def delete_inspiration(inspiration_id: str, db: AsyncSession = Depends(get_db)):
    inspiration = await db.get(Inspiration, inspiration_id)
    if not inspiration:
        raise HTTPException(status_code=404, detail="Inspiration not found")
    await db.delete(inspiration)
    await db.commit()
