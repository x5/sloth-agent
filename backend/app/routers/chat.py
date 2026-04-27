"""Chat API + SSE streaming for Inspirations."""

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import async_session
from ..models import AgentTemplate, LLMConfig, Message
from ..services.agent import AgentService
from ..services.llm import LLMService, _get_default_llm_config

router = APIRouter(prefix="/api/inspirations", tags=["chat"])


class ChatRequest(BaseModel):
    content: str = Field(min_length=1, max_length=10000)


class MessageResponse(BaseModel):
    id: str
    inspiration_id: str
    agent_id: str | None
    role: str
    content: str
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


ROLE_MAP = {"human": "user", "agent": "assistant", "system": "system"}


def _map_role(role: str) -> str:
    return ROLE_MAP.get(role, role)


async def _get_default_agent_or_raise(inspiration_id: str, db: AsyncSession):
    agent = await AgentService.get_default_agent(inspiration_id)
    if not agent:
        raise HTTPException(status_code=400, detail="No Lead Agent found for this Inspiration")
    return agent


@router.post("/{inspiration_id}/chat", response_model=MessageResponse)
async def chat(inspiration_id: str, req: ChatRequest, db: AsyncSession = Depends(get_db)):
    agent = await _get_default_agent_or_raise(inspiration_id, db)

    # Update agent status to working
    agent.status = "working"
    await db.commit()

    # Save human message
    human_msg = Message(
        inspiration_id=inspiration_id,
        agent_id=agent.id,
        role="human",
        content=req.content,
    )
    db.add(human_msg)

    # Load template for system prompt
    tpl = await db.get(AgentTemplate, agent.template_id) if agent.template_id else None

    # Load history
    result = await db.execute(
        select(Message)
        .where(Message.inspiration_id == inspiration_id)
        .order_by(Message.created_at.desc())
        .limit(20)
    )
    history = list(result.scalars().all())[::-1]

    llm_messages = []
    if tpl and tpl.system_prompt:
        llm_messages.append({"role": "system", "content": tpl.system_prompt})
    llm_messages += [{"role": _map_role(m.role), "content": m.content} for m in history]
    llm_messages.append({"role": "user", "content": req.content})

    try:
        llm = LLMService()
        reply_content = await llm.chat(agent.model, llm_messages)
    except Exception as e:
        agent.status = "error"
        await db.commit()
        raise HTTPException(status_code=502, detail=f"LLM call failed: {str(e)}")

    # Save agent message
    agent_msg = Message(
        inspiration_id=inspiration_id,
        agent_id=agent.id,
        role="agent",
        content=reply_content,
    )
    db.add(agent_msg)
    agent.status = "idle"
    await db.commit()
    await db.refresh(agent_msg)

    return agent_msg


@router.post("/{inspiration_id}/chat/stream")
async def chat_stream(inspiration_id: str, req: ChatRequest, db: AsyncSession = Depends(get_db)):
    agent = await _get_default_agent_or_raise(inspiration_id, db)

    # Save human message
    human_msg = Message(
        inspiration_id=inspiration_id,
        agent_id=agent.id,
        role="human",
        content=req.content,
    )
    db.add(human_msg)
    agent.status = "working"
    await db.commit()

    # Load template for system prompt
    tpl = await db.get(AgentTemplate, agent.template_id) if agent.template_id else None

    # Load history
    result = await db.execute(
        select(Message)
        .where(Message.inspiration_id == inspiration_id)
        .order_by(Message.created_at.desc())
        .limit(20)
    )
    history = list(result.scalars().all())[::-1]

    llm_messages = []
    if tpl and tpl.system_prompt:
        llm_messages.append({"role": "system", "content": tpl.system_prompt})
    llm_messages += [{"role": _map_role(m.role), "content": m.content} for m in history]
    llm_messages.append({"role": "user", "content": req.content})

    async def event_stream():
        full_reply = ""
        try:
            llm = LLMService()
            async for token in llm.chat_stream(agent.model, llm_messages):
                full_reply += token
                yield f"data: {json.dumps({'token': token})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"
        finally:
            # Save full agent message
            async with async_session() as save_db:
                a = await save_db.get(type(agent), agent.id)
                if a:
                    agent_msg = Message(
                        inspiration_id=inspiration_id,
                        agent_id=agent.id,
                        role="agent",
                        content=full_reply,
                    )
                    save_db.add(agent_msg)
                    a.status = "idle" if full_reply else "error"
                    await save_db.commit()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/{inspiration_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    inspiration_id: str,
    limit: int = 50,
    before: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Message).where(Message.inspiration_id == inspiration_id)
    if before:
        result = await db.execute(
            select(Message.created_at).where(Message.id == before)
        )
        before_ts = result.scalar_one_or_none()
        if before_ts:
            stmt = stmt.where(Message.created_at < before_ts)
    stmt = stmt.order_by(Message.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    messages = list(result.scalars().all())[::-1]
    return messages
