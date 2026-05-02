"""BrainstormEngine — Sequential conversational discussion engine.

Core flow:
  1. User sends a message → saved as human message
  2. Each agent responds ONE AT A TIME (streaming tokens to client in real-time)
  3. Each agent sees full conversation history including prior agents' responses
  4. Cooling timer: idle cooldown → cooling_down → confirmation → ended
  5. User can inject new messages at any time (resets timer)
  6. User can abort mid-stream (abort flag)
"""

import asyncio
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import AsyncIterator

from sqlalchemy import select, text

from ..database import async_session
from ..models import AgentTemplate, BrainstormSession, InspirationAgent, Message
from .llm import LLMService


# ---- Data types ----

@dataclass
class AgentInfo:
    id: str
    name: str
    role: str
    model: str
    system_prompt: str = ""


@dataclass
class SSEEvent:
    """Event yielded by BrainstormEngine, to be formatted as SSE by the endpoint."""
    event: str
    data: dict


# ---- CoolingTimer state machine ----

class TimerState(str, Enum):
    RUNNING = "running"
    COOLING_DOWN = "cooling_down"
    CONFIRMING = "confirming"
    ENDED = "ended"


class CoolingTimer:
    """Tracks discussion activity and determines when to end.

    State machine:
      RUNNING     ──(idle cooldown_seconds)──>  COOLING_DOWN
      COOLING_DOWN ──(new speech)──>             RUNNING
      COOLING_DOWN ──(confirmation_seconds)──>   CONFIRMING
      CONFIRMING   ──(new speech)──>             RUNNING
      CONFIRMING   ──(confirmation_seconds)──>   ENDED
      ANY          ──(max_messages)──>           ENDED
    """

    def __init__(
        self,
        cooldown_seconds: float = 5.0,
        confirmation_seconds: float = 3.0,
        max_messages: int = 1000,
    ):
        self.cooldown_seconds = cooldown_seconds
        self.confirmation_seconds = confirmation_seconds
        self.max_messages = max_messages
        self.state = TimerState.RUNNING
        self.message_count = 0
        self._last_activity = time.monotonic()
        self._state_changed_at = self._last_activity

    def heartbeat(self):
        """Call whenever a new agent speech is SAVED. Resets idle timer and increments count."""
        now = time.monotonic()
        self._last_activity = now
        self.message_count += 1
        if self.state in (TimerState.COOLING_DOWN, TimerState.CONFIRMING):
            self.state = TimerState.RUNNING
            self._state_changed_at = now

    def keep_alive(self):
        """Reset the idle timer without incrementing message count.

        Call at agent_start to prevent cooldown from triggering during LLM generation,
        since an LLM call can take 5-30s which would otherwise look like idle time.
        """
        now = time.monotonic()
        self._last_activity = now
        if self.state in (TimerState.COOLING_DOWN, TimerState.CONFIRMING):
            self.state = TimerState.RUNNING
            self._state_changed_at = now

    def check(self) -> TimerState:
        """Advance state machine based on elapsed time. Returns current state."""
        now = time.monotonic()
        idle = now - self._last_activity

        if self.message_count >= self.max_messages:
            self.state = TimerState.ENDED
            return self.state

        if self.state == TimerState.RUNNING:
            if idle >= self.cooldown_seconds:
                self.state = TimerState.COOLING_DOWN
                self._state_changed_at = now

        elif self.state == TimerState.COOLING_DOWN:
            if idle >= self.cooldown_seconds + self.confirmation_seconds:
                self.state = TimerState.CONFIRMING
                self._state_changed_at = now

        elif self.state == TimerState.CONFIRMING:
            time_in_confirming = now - self._state_changed_at
            if time_in_confirming >= self.confirmation_seconds:
                self.state = TimerState.ENDED

        return self.state

    def abort(self):
        """Immediately end the discussion."""
        self.state = TimerState.ENDED


# ---- BrainstormEngine ----

SPEECH_PROMPT_TEMPLATE = (
    "{system_prompt}\n\n"
    "## Live Brainstorm Discussion\n\n"
    "You are {agent_name}, in an active multi-agent debate.\n"
    "Other participants: {other_agents}\n\n"
    "Conversation so far:\n{context}\n\n"
    "Your job right now:\n"
    "1. React to the LATEST points made — agree, disagree, or challenge.\n"
    "2. If you disagree, say so directly and explain why.\n"
    "3. If someone made a point you want to build on, name them and extend it.\n"
    "4. Ask a sharp follow-up question if you want elaboration.\n"
    "5. Keep it under 120 words. Be direct, not diplomatic.\n"
    "6. If the latest points already cover your perspective completely and "
    "you have nothing genuinely new to add, reply with exactly: PASS\n\n"
    "IMPORTANT: Always respond in the same language as the user's latest message."
)


def _build_context_text(history: list[dict]) -> str:
    """Format message history into readable context for LLM prompts."""
    lines = []
    truncated = len(history) > 50
    for msg in history[-50:]:
        role = msg.get("role", "unknown")
        name = msg.get("agent_name") or ("User" if role == "human" else "Agent")
        content = msg.get("content", "")
        lines.append(f"[{name}]: {content}")
    result = "\n".join(lines) if lines else "(No messages yet)"
    if truncated:
        result = "[Context truncated: showing last 50 messages]\n" + result
    return result


class BrainstormEngine:
    """Sequential conversational brainstorm engine.

    Usage (persistent, Iter-6):
        engine = BrainstormEngine(session_id, inspiration_id)
        async for event in engine.run_persistent():
            ...
        # inject user messages at any time:
        await engine.inject(content, reply_to_message_id)

    Usage (one-shot, deprecated Iter-7):
        async for event in engine.run(user_content):
            ...
    """

    def __init__(
        self,
        session_id: str,
        inspiration_id: str,
        cooldown_seconds: float = 5.0,
        confirmation_seconds: float = 3.0,
        max_messages: int = 1000,
    ):
        self.session_id = session_id
        self.inspiration_id = inspiration_id
        self.llm = LLMService()
        self.timer = CoolingTimer(
            cooldown_seconds=cooldown_seconds,
            confirmation_seconds=confirmation_seconds,
            max_messages=max_messages,
        )
        self._abort = False
        self._abort_round = False
        self._queue: asyncio.Queue[tuple[str, str | None]] | None = None

    def _get_queue(self) -> asyncio.Queue[tuple[str, str | None]]:
        """Lazy-init the queue (needs running event loop)."""
        if self._queue is None:
            self._queue = asyncio.Queue()
        return self._queue

    def abort(self):
        """Signal the engine to stop. Checked between agents and during streaming."""
        self._abort = True

    def interrupt_round(self):
        """Stop only the current round, keeping the persistent connection alive."""
        self._abort_round = True

    async def inject(self, content: str, reply_to: str | None = None) -> None:
        """Put a user message into the persistent discussion queue."""
        await self._get_queue().put((content, reply_to))

    async def _load_agents(self) -> list[AgentInfo]:
        """Load team agents with their template system prompts."""
        async with async_session() as db:
            result = await db.execute(
                select(InspirationAgent, AgentTemplate)
                .outerjoin(AgentTemplate, InspirationAgent.template_id == AgentTemplate.id)
                .where(InspirationAgent.inspiration_id == self.inspiration_id)
            )
            rows = result.all()

        return [
            AgentInfo(
                id=agent.id,
                name=agent.name,
                role=template.role if template else "expert",
                model=agent.model,
                system_prompt=template.system_prompt if template else "",
            )
            for agent, template in rows
        ]

    async def _load_history(self) -> list[dict]:
        """Load recent messages for context, with real agent names resolved via JOIN."""
        async with async_session() as db:
            result = await db.execute(
                select(Message, InspirationAgent)
                .outerjoin(InspirationAgent, Message.agent_id == InspirationAgent.id)
                .where(Message.brainstorm_session_id == self.session_id)
                .order_by(Message.created_at.desc())
                .limit(50)
            )
            rows = list(reversed(result.all()))

        return [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "agent_name": (
                    agent.name if agent is not None
                    else ("User" if m.role == "human" else "Agent")
                ),
                "agent_id": m.agent_id,
            }
            for m, agent in rows
        ]

    async def _save_message(
        self,
        role: str,
        content: str,
        agent_id: str | None = None,
        agent_name: str | None = None,
        parent_message_id: str | None = None,
        round_num: int = 1,
    ) -> str:
        """Persist a message to the database. Returns message ID."""
        msg = Message(
            id=str(uuid.uuid4()),
            inspiration_id=self.inspiration_id,
            agent_id=agent_id,
            role=role,
            content=content,
            mode="brainstorm",
            brainstorm_session_id=self.session_id,
            parent_message_id=parent_message_id,
            round=round_num,
            truncated=False,
        )
        async with async_session() as db:
            db.add(msg)
            await db.commit()
        return msg.id

    async def _increment_message_count(self):
        """Atomically increment the session's message_count (no read-modify-write race)."""
        async with async_session() as db:
            await db.execute(
                text("UPDATE brainstorm_sessions SET message_count = message_count + 1 WHERE id = :id"),
                {"id": self.session_id},
            )
            await db.commit()

    async def _get_current_round(self) -> int:
        """Get the current round number for this session."""
        async with async_session() as db:
            result = await db.execute(
                select(Message.round)
                .where(Message.brainstorm_session_id == self.session_id)
                .order_by(Message.round.desc())
                .limit(1)
            )
            row = result.scalar_one_or_none()
            return (row or 0) + 1

    async def _run_rounds(
        self,
        user_msg_id: str,
        user_content: str,
        current_round: int,
        agents: list[AgentInfo],
        agent_indices: dict[str, int],
        agent_names: list[str],
    ) -> AsyncIterator[SSEEvent]:
        """Run multi-round agent loop for one user topic. Yields SSEEvents.

        Emits agent_start / agent_token / message_done / agent_pass per agent,
        round_end after each sub-round, and discussion_end / max_reached at the end.
        """
        MAX_ROUNDS = 8
        sub_round = 0

        while not self._abort and sub_round < MAX_ROUNDS:
            if self._abort_round:
                break

            sub_round += 1
            round_num = current_round + sub_round - 1

            if self.timer.check() == TimerState.ENDED:
                break

            speeches_this_round = 0

            for agent in agents:
                if self._abort or self._abort_round or self.timer.check() == TimerState.ENDED:
                    break

                yield SSEEvent(event="agent_start", data={
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                    "agent_number": agent_indices.get(agent.id),
                    "parent_message_id": user_msg_id,
                })

                # Reset idle timer — LLM generation can take 5-30s, which would
                # otherwise look like idle time and incorrectly trigger cooldown.
                self.timer.keep_alive()

                history = await self._load_history()
                context_text = _build_context_text(history)
                other = [n for n in agent_names if n != agent.name]
                other_str = ", ".join(other) if other else "None"

                prompt = SPEECH_PROMPT_TEMPLATE.format(
                    system_prompt=agent.system_prompt or "You are a helpful expert.",
                    agent_name=agent.name,
                    other_agents=other_str,
                    context=context_text,
                )
                messages = [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_content},
                ]

                full_content = ""
                try:
                    async for token in self.llm.chat_stream(agent.model, messages):
                        if self._abort or self._abort_round:
                            break
                        full_content += token
                        yield SSEEvent(event="agent_token", data={
                            "agent_id": agent.id,
                            "agent_name": agent.name,
                            "token": token,
                        })
                except Exception as e:
                    full_content = f"[Error: {agent.name} failed — {str(e)[:100]}]"
                    yield SSEEvent(event="agent_token", data={
                        "agent_id": agent.id,
                        "agent_name": agent.name,
                        "token": full_content,
                    })

                if self._abort or self._abort_round:
                    break

                is_pass = full_content.strip().upper() == "PASS" or not full_content.strip()

                if is_pass:
                    yield SSEEvent(event="agent_pass", data={
                        "agent_id": agent.id,
                        "agent_name": agent.name,
                        "agent_number": agent_indices.get(agent.id),
                    })
                else:
                    speeches_this_round += 1
                    msg_id = await self._save_message(
                        role="agent",
                        content=full_content,
                        agent_id=agent.id,
                        agent_name=agent.name,
                        parent_message_id=user_msg_id,
                        round_num=round_num,
                    )
                    await self._increment_message_count()
                    self.timer.heartbeat()

                    yield SSEEvent(event="message_done", data={
                        "agent_id": agent.id,
                        "agent_name": agent.name,
                        "agent_number": agent_indices.get(agent.id),
                        "message_id": msg_id,
                        "full_content": full_content,
                        "parent_message_id": user_msg_id,
                        "round": round_num,
                    })

            yield SSEEvent(event="round_end", data={
                "round": round_num,
                "speeches": speeches_this_round,
            })

            if self._abort_round:
                break

            if speeches_this_round == 0:
                break

            if not self._abort:
                await asyncio.sleep(0.3)

        if self.timer.message_count >= self.timer.max_messages:
            yield SSEEvent(event="max_reached", data={"limit": self.timer.max_messages})

        yield SSEEvent(event="discussion_end", data={
            "summary": None,
            "message_count": self.timer.message_count,
            "round": current_round,
        })
        self._abort_round = False

    async def run(
        self,
        user_content: str,
        reply_to_message_id: str | None = None,
    ) -> AsyncIterator[SSEEvent]:
        """[DEPRECATED — remove in Iter-7] One-shot discussion run.

        Processes a single user message, runs agent rounds until natural end or abort,
        then the stream closes. Each call is a separate SSE connection.

        Use run_persistent() + inject() for the Iter-6+ persistent connection model.
        """
        current_round = await self._get_current_round()

        # Save user message
        user_msg_id = await self._save_message(
            role="human",
            content=user_content,
            parent_message_id=reply_to_message_id,
            round_num=current_round,
        )
        await self._increment_message_count()
        self.timer.heartbeat()

        # Load agents
        agents = await self._load_agents()
        if not agents:
            yield SSEEvent(event="error", data={"error": "No agents in team. Add agents first."})
            return

        agent_names = [a.name for a in agents]
        agent_indices = {a.id: (i + 1) for i, a in enumerate(agents)}

        async for event in self._run_rounds(
            user_msg_id, user_content, current_round, agents, agent_indices, agent_names
        ):
            yield event

    async def run_persistent(self) -> AsyncIterator[SSEEvent]:
        """Persistent queue-driven discussion loop.

        Waits for messages injected via inject(). Runs agent rounds for each
        message, then loops back to wait. Emits heartbeat every 30s when idle.
        Stream only ends when abort() is called.

        Agents are reloaded before each message's rounds, so adding/removing
        agents during an active session takes effect on the next inject.
        """
        # Initial check: refuse to start if team has no agents at all
        if not await self._load_agents():
            yield SSEEvent(event="error", data={"error": "No agents in team. Add agents first."})
            return

        queue = self._get_queue()

        while not self._abort:
            # Wait for a user message, or emit heartbeat on timeout
            try:
                content, reply_to = await asyncio.wait_for(queue.get(), timeout=30.0)
            except asyncio.TimeoutError:
                yield SSEEvent(event="heartbeat", data={})
                continue

            if self._abort:
                break

            self._abort_round = False

            # Reload agents for each message — picks up any adds/removes since last round
            agents = await self._load_agents()
            if not agents:
                yield SSEEvent(event="error", data={"error": "No agents in team. Add agents first."})
                continue

            agent_names = [a.name for a in agents]
            agent_indices = {a.id: (i + 1) for i, a in enumerate(agents)}
            current_round = await self._get_current_round()

            # Save user message and notify frontend immediately
            user_msg_id = await self._save_message(
                role="human",
                content=content,
                parent_message_id=reply_to,
                round_num=current_round,
            )
            await self._increment_message_count()
            self.timer.heartbeat()

            yield SSEEvent(event="user_message", data={
                "message_id": user_msg_id,
                "content": content,
                "parent_message_id": reply_to,
            })

            # Run agent rounds for this topic
            async for event in self._run_rounds(
                user_msg_id, content, current_round, agents, agent_indices, agent_names
            ):
                yield event
                if self._abort:
                    break
