"""Agent Pool (template) management — Sloth global Settings."""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sloth_agent.core.agents.role_tools import ROLE_BASE_TOOLS

from ..database import async_session
from ..models import AgentTemplate

router = APIRouter(prefix="/api/settings/agents", tags=["settings-agents"])


class UpdateAgentTemplateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    default_model: str | None = Field(default=None, max_length=100)
    system_prompt: str | None = Field(default=None, max_length=15000)
    auto_join: bool | None = None
    tools: str | None = None


class AgentTemplateResponse(BaseModel):
    id: str
    name: str
    role: str
    default_model: str
    auto_join: bool
    system_prompt: str
    tools: list[str] = []
    role_tools: list[str] = []
    agent_tools: list[str] = []
    effective_tools: list[str] = []
    created_at: str

    model_config = {"from_attributes": True}

    @field_validator("created_at", mode="before")
    @classmethod
    def serialize_created_at(cls, v: object) -> str:
        if isinstance(v, datetime):
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)
            return v.isoformat()
        return v


def _enrich_template_response(tmpl: AgentTemplate) -> dict:
    """Add computed role_tools, agent_tools, effective_tools fields."""
    agent_tools = json.loads(tmpl.tools or "[]")
    role_tools = ROLE_BASE_TOOLS.get(tmpl.role, [])
    effective = list(dict.fromkeys(role_tools + agent_tools))
    return {
        "id": tmpl.id,
        "name": tmpl.name,
        "role": tmpl.role,
        "default_model": tmpl.default_model,
        "auto_join": tmpl.auto_join,
        "system_prompt": tmpl.system_prompt,
        "tools": agent_tools,
        "role_tools": role_tools,
        "agent_tools": agent_tools,
        "effective_tools": effective,
        "created_at": tmpl.created_at,
    }


async def get_db():
    async with async_session() as session:
        yield session


@router.get("")
async def list_agent_templates(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AgentTemplate).order_by(AgentTemplate.created_at.asc())
    )
    templates = result.scalars().all()
    return [_enrich_template_response(t) for t in templates]


@router.patch("/{template_id}")
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
    return _enrich_template_response(tmpl)


@router.get("/{template_id}")
async def get_agent_template(template_id: str, db: AsyncSession = Depends(get_db)):
    tmpl = await db.get(AgentTemplate, template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Agent template not found")
    return _enrich_template_response(tmpl)
