import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.sqlite import CHAR
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


class Inspiration(Base):
    __tablename__ = "inspirations"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=_new_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class LLMConfig(Base):
    __tablename__ = "llm_configs"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=_new_uuid)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    api_key: Mapped[str] = mapped_column(String(200), nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    api_format: Mapped[str] = mapped_column(String(20), nullable=False, default="openai")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AgentTemplate(Base):
    __tablename__ = "agent_templates"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=_new_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    default_model: Mapped[str] = mapped_column(String(100), nullable=False)
    auto_join: Mapped[bool] = mapped_column(Boolean, default=False)
    system_prompt: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class InspirationAgent(Base):
    __tablename__ = "inspiration_agents"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=_new_uuid)
    inspiration_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("inspirations.id", ondelete="CASCADE"), nullable=False)
    template_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("agent_templates.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="idle")
    joined_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=_new_uuid)
    inspiration_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("inspirations.id", ondelete="CASCADE"), nullable=False)
    agent_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("inspiration_agents.id", ondelete="SET NULL"), nullable=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(String(20), default="chat", nullable=False)
    brainstorm_session_id: Mapped[str | None] = mapped_column(
        CHAR(36), ForeignKey("brainstorm_sessions.id", ondelete="SET NULL"), nullable=True
    )
    parent_message_id: Mapped[str | None] = mapped_column(
        CHAR(36), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )
    round: Mapped[int] = mapped_column(Integer, default=1)
    intent: Mapped[str | None] = mapped_column(String(10), nullable=True)
    truncated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class BrainstormSession(Base):
    __tablename__ = "brainstorm_sessions"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=_new_uuid)
    inspiration_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("inspirations.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    sandbox_path: Mapped[str] = mapped_column(String(500), nullable=False)
    max_messages: Mapped[int] = mapped_column(Integer, default=1000)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, default=5)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_by: Mapped[str | None] = mapped_column(String(20), nullable=True)
    notification_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class BrainstormFile(Base):
    __tablename__ = "brainstorm_files"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=_new_uuid)
    session_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("brainstorm_sessions.id", ondelete="CASCADE"), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str] = mapped_column(CHAR(36), ForeignKey("inspiration_agents.id", ondelete="SET NULL"), nullable=True)
    file_type: Mapped[str] = mapped_column(String(20), default="other")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
