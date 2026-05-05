"""Convert DB Message rows to core-compatible dict format."""

from typing import Any

from sloth_agent.core.context.engine import ContextEngine, ContextPolicy, ContextResult


def db_messages_to_dicts(db_messages: list[Any]) -> list[dict]:
    """Convert SQLAlchemy Message rows to plain dicts for ContextEngine."""
    return [
        {
            "id": getattr(m, "id", ""),
            "role": getattr(m, "role", "user"),
            "content": getattr(m, "content", ""),
            "parent_message_id": getattr(m, "parent_message_id", None),
            "agent_id": getattr(m, "agent_id", None),
            "agent_name": (
                getattr(m, "agent_name", "Unknown")
                if hasattr(m, "agent_name")
                else None
            ),
            "round": getattr(m, "round", 1),
        }
        for m in db_messages
    ]


def build_brainstorm_context(
    system_prompt: str,
    history: list[dict],
    model: str = "deepseek-v4-pro",
) -> ContextResult:
    """Build context for a brainstorm agent turn."""
    policy = ContextPolicy(
        model=model,
        max_tokens=128_000,
        output_reserve=15_000,
        protect_threads=True,
        mode="brainstorm",
    )
    engine = ContextEngine(policy)
    return engine.build(system_prompt, history)
