"""Chat API + SSE streaming for Inspirations."""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import async_session
from ..models import AgentTemplate, InspirationAgent, LLMConfig, Message
from ..services.agent import AgentService
from ..services.llm import LLMService, _get_default_llm_config

router = APIRouter(prefix="/api/inspirations", tags=["chat"])


class ChatRequest(BaseModel):
    content: str = Field(min_length=1, max_length=10000)
    mode: str = "chat"
    brainstorm_session_id: str | None = None


class MessageResponse(BaseModel):
    id: str
    inspiration_id: str
    agent_id: str | None
    role: str
    content: str
    created_at: str
    agent_name: str | None = None
    agent_number: int | None = None
    agent_model: str | None = None
    mode: str = "chat"
    brainstorm_session_id: str | None = None
    parent_message_id: str | None = None
    round: int = 1
    intent: str | None = None
    truncated: bool = False

    model_config = {"from_attributes": True}

    @field_validator("created_at", mode="before")
    @classmethod
    def serialize_created_at(cls, v: object) -> str:
        if isinstance(v, datetime):
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)
            return v.isoformat()
        return v


async def get_db():
    async with async_session() as session:
        yield session


ROLE_MAP = {"human": "user", "agent": "assistant", "system": "system"}


def _map_role(role: str) -> str:
    return ROLE_MAP.get(role, role)


def _build_message_query(inspiration_id: str, brainstorm_session_id: str | None = None):
    """Return filtered message query with session context isolation.

    When brainstorm_session_id is set: chat-mode messages (shared base) +
    only the current session's brainstorm messages. Other sessions are excluded.
    When brainstorm_session_id is None: chat-mode messages only.
    """
    conditions = [Message.inspiration_id == inspiration_id]
    if brainstorm_session_id:
        conditions.append(
            (Message.mode == "chat") |
            ((Message.mode == "brainstorm") & (Message.brainstorm_session_id == brainstorm_session_id))
        )
    else:
        conditions.append(Message.mode == "chat")
    return select(Message).where(*conditions)


async def _get_default_agent_or_raise(inspiration_id: str, db: AsyncSession):
    agent = await AgentService.get_default_agent(inspiration_id)
    if not agent:
        raise HTTPException(status_code=400, detail="No Lead Agent found for this Inspiration")
    return agent


async def _build_agent_map(inspiration_id: str, db: AsyncSession) -> dict[str, tuple[str, int, str]]:
    """Return {agent_id: (name, number, model)} for all agents in an inspiration."""
    result = await db.execute(
        select(InspirationAgent)
        .where(InspirationAgent.inspiration_id == inspiration_id)
        .order_by(InspirationAgent.joined_at)
    )
    agents = list(result.scalars().all())

    # Resolve default model name for agents without an explicit model
    default_model = None
    for a in agents:
        if a.model:
            default_model = a.model
            break
    if not default_model:
        llm_result = await db.execute(
            select(LLMConfig.model).where(LLMConfig.is_default == True)
        )
        default_model = llm_result.scalar_one_or_none()

    agent_map = {}
    for i, a in enumerate(agents):
        model = a.model or default_model or ""
        agent_map[a.id] = (a.name, i + 1, model)
    return agent_map


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
        mode=req.mode,
        brainstorm_session_id=req.brainstorm_session_id,
    )
    db.add(human_msg)

    # Load template for system prompt
    tpl = await db.get(AgentTemplate, agent.template_id) if agent.template_id else None

    # Load history with session context isolation
    result = await db.execute(
        _build_message_query(inspiration_id, req.brainstorm_session_id)
        .order_by(Message.created_at.desc())
        .limit(1000)
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
        mode=req.mode,
        brainstorm_session_id=req.brainstorm_session_id,
    )
    db.add(agent_msg)
    agent.status = "idle"
    await db.commit()
    await db.refresh(agent_msg)

    # Enrich with agent info
    agent_map = await _build_agent_map(inspiration_id, db)
    name, num, model = agent_map.get(agent.id, (None, None, None))
    return MessageResponse(
        id=agent_msg.id,
        inspiration_id=agent_msg.inspiration_id,
        agent_id=agent_msg.agent_id,
        role=agent_msg.role,
        content=agent_msg.content,
        created_at=agent_msg.created_at,
        agent_name=name,
        agent_number=num,
        agent_model=model,
        mode=agent_msg.mode,
        brainstorm_session_id=agent_msg.brainstorm_session_id,
    )


@router.post("/{inspiration_id}/chat/stream")
async def chat_stream(inspiration_id: str, req: ChatRequest, db: AsyncSession = Depends(get_db)):
    agent = await _get_default_agent_or_raise(inspiration_id, db)

    # Save human message
    human_msg = Message(
        inspiration_id=inspiration_id,
        agent_id=agent.id,
        role="human",
        content=req.content,
        mode=req.mode,
        brainstorm_session_id=req.brainstorm_session_id,
    )
    db.add(human_msg)
    agent.status = "working"
    await db.commit()

    # Load template for system prompt
    tpl = await db.get(AgentTemplate, agent.template_id) if agent.template_id else None

    # Load history with session context isolation
    result = await db.execute(
        _build_message_query(inspiration_id, req.brainstorm_session_id)
        .order_by(Message.created_at.desc())
        .limit(1000)
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
                        mode=req.mode,
                        brainstorm_session_id=req.brainstorm_session_id,
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
    brainstorm_session_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = _build_message_query(inspiration_id, brainstorm_session_id)
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

    agent_map = await _build_agent_map(inspiration_id, db)
    out = []
    for m in messages:
        name, num, model = agent_map.get(m.agent_id, (None, None, None))
        out.append(MessageResponse(
            id=m.id,
            inspiration_id=m.inspiration_id,
            agent_id=m.agent_id,
            role=m.role,
            content=m.content,
            created_at=m.created_at,
            agent_name=name,
            agent_number=num,
            agent_model=model,
            mode=m.mode,
            brainstorm_session_id=m.brainstorm_session_id,
        ))
    return out
