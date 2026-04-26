from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import async_session
from ..models import Inspiration

router = APIRouter(prefix="/api/inspirations", tags=["inspirations"])


class CreateInspirationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class InspirationResponse(BaseModel):
    id: str
    name: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def ensure_utc(self):
        for field_name in ("created_at", "updated_at"):
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
    return inspiration


@router.get("", response_model=list[InspirationResponse])
async def list_inspirations(q: str | None = None, db: AsyncSession = Depends(get_db)):
    stmt = select(Inspiration).order_by(Inspiration.updated_at.desc())
    if q:
        stmt = stmt.where(Inspiration.name.ilike(f"%{q}%"))
    result = await db.execute(stmt)
    return result.scalars().all()


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
