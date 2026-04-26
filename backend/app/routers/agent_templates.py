"""Agent Pool (template) management — Sloth global Settings."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import async_session
from ..models import AgentTemplate

router = APIRouter(prefix="/api/settings/agents", tags=["settings-agents"])


class UpdateAgentTemplateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    default_model: str | None = Field(default=None, max_length=100)
    system_prompt: str | None = Field(default=None, max_length=5000)
    auto_join: bool | None = None


class AgentTemplateResponse(BaseModel):
    id: str
    name: str
    role: str
    default_model: str
    auto_join: bool
    system_prompt: str
    created_at: str

    model_config = {"from_attributes": True}

    @field_validator("created_at", mode="before")
    @classmethod
    def serialize_created_at(cls, v: object) -> str:
        if isinstance(v, datetime):
            return v.isoformat()
        return v


async def get_db():
    async with async_session() as session:
        yield session


@router.get("", response_model=list[AgentTemplateResponse])
async def list_agent_templates(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AgentTemplate).order_by(AgentTemplate.created_at.asc())
    )
    return result.scalars().all()


@router.patch("/{template_id}", response_model=AgentTemplateResponse)
async def update_agent_template(
    template_id: str,
    req: UpdateAgentTemplateRequest,
    db: AsyncSession = Depends(get_db),
):
    tmpl = await db.get(AgentTemplate, template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Agent template not found")

    update_data = req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(tmpl, key, value)

    await db.commit()
    await db.refresh(tmpl)
    return tmpl


@router.get("/{template_id}", response_model=AgentTemplateResponse)
async def get_agent_template(template_id: str, db: AsyncSession = Depends(get_db)):
    tmpl = await db.get(AgentTemplate, template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Agent template not found")
    return tmpl
