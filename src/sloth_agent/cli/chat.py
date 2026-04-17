"""Interactive chat REPL."""

from sloth_agent.chat.repl import EnhancedChatSession


def chat(
    model: str | None = None,
    provider: str | None = None,
) -> None:
    """Enter interactive chat mode with tool execution and autonomous control."""
    session = EnhancedChatSession(model=model, provider=provider)
    session.loop()
