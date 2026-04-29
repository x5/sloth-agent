"""Team member management — per-Inspiration agent instances."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import async_session
from ..models import AgentTemplate, Inspiration, InspirationAgent

router = APIRouter(tags=["agents"])


class AddAgentRequest(BaseModel):
    template_id: str = Field(min_length=1, max_length=36)


class UpdateAgentRequest(BaseModel):
    model: str | None = Field(default=None, max_length=100)


class AgentResponse(BaseModel):
    id: str
    inspiration_id: str
    template_id: str | None
    name: str
    role: str = ""
    model: str
    status: str
    joined_at: str

    model_config = {"from_attributes": True}

    @field_validator("joined_at", mode="before")
    @classmethod
    def serialize_joined_at(cls, v: object) -> str:
        if isinstance(v, datetime):
            return v.isoformat()
        return v


async def get_db():
    async with async_session() as session:
        yield session


@router.get(
    "/api/inspirations/{inspiration_id}/agents",
    response_model=list[AgentResponse],
)
async def list_agents(inspiration_id: str, db: AsyncSession = Depends(get_db)):
    insp = await db.get(Inspiration, inspiration_id)
    if not insp:
        raise HTTPException(status_code=404, detail="Inspiration not found")

    result = await db.execute(
        select(InspirationAgent)
        .where(InspirationAgent.inspiration_id == inspiration_id)
        .order_by(InspirationAgent.joined_at.asc())
    )
    agents = result.scalars().all()

    out = []
    for a in agents:
        role = ""
        if a.template_id:
            tmpl = await db.get(AgentTemplate, a.template_id)
            if tmpl:
                role = tmpl.role
        out.append(AgentResponse(
            id=a.id,
            inspiration_id=a.inspiration_id,
            template_id=a.template_id,
            name=a.name,
            role=role,
            model=a.model,
            status=a.status,
            joined_at=a.joined_at.isoformat() if isinstance(a.joined_at, datetime) else str(a.joined_at),
        ))
    return out


@router.post(
    "/api/inspirations/{inspiration_id}/agents",
    response_model=AgentResponse,
    status_code=201,
)
async def add_agent(
    inspiration_id: str,
    req: AddAgentRequest,
    db: AsyncSession = Depends(get_db),
):
    insp = await db.get(Inspiration, inspiration_id)
    if not insp:
        raise HTTPException(status_code=404, detail="Inspiration not found")

    tmpl = await db.get(AgentTemplate, req.template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Agent template not found")

    existing = await db.execute(
        select(InspirationAgent).where(
            InspirationAgent.inspiration_id == inspiration_id,
            InspirationAgent.template_id == req.template_id,
        )
    )
    if existing.scalar():
        raise HTTPException(status_code=409, detail="Agent already in team")

    agent = InspirationAgent(
        inspiration_id=inspiration_id,
        template_id=tmpl.id,
        name=tmpl.name,
        model=tmpl.default_model,
        status="idle",
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    return AgentResponse(
        id=agent.id,
        inspiration_id=agent.inspiration_id,
        template_id=agent.template_id,
        name=agent.name,
        role=tmpl.role,
        model=agent.model,
        status=agent.status,
        joined_at=agent.joined_at.isoformat() if isinstance(agent.joined_at, datetime) else str(agent.joined_at),
    )


@router.patch("/api/agents/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    req: UpdateAgentRequest,
    db: AsyncSession = Depends(get_db),
):
    agent = await db.get(InspirationAgent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if req.model is not None:
        agent.model = req.model

    await db.commit()
    await db.refresh(agent)

    role = ""
    if agent.template_id:
        tmpl = await db.get(AgentTemplate, agent.template_id)
        if tmpl:
            role = tmpl.role

    return AgentResponse(
        id=agent.id,
        inspiration_id=agent.inspiration_id,
        template_id=agent.template_id,
        name=agent.name,
        role=role,
        model=agent.model,
        status=agent.status,
        joined_at=agent.joined_at.isoformat() if isinstance(agent.joined_at, datetime) else str(agent.joined_at),
    )


@router.delete("/api/inspirations/{inspiration_id}/agents/{agent_id}", status_code=204)
async def remove_agent(
    inspiration_id: str,
    agent_id: str,
    db: AsyncSession = Depends(get_db),
):
    insp = await db.get(Inspiration, inspiration_id)
    if not insp:
        raise HTTPException(status_code=404, detail="Inspiration not found")

    agent = await db.get(InspirationAgent, agent_id)
    if not agent or agent.inspiration_id != inspiration_id:
        raise HTTPException(status_code=404, detail="Agent not found in this team")

    if agent.template_id:
        tmpl = await db.get(AgentTemplate, agent.template_id)
        if tmpl and tmpl.role == "lead":
            raise HTTPException(status_code=403, detail="Cannot remove Lead Agent from team")

    await db.delete(agent)
    await db.commit()
