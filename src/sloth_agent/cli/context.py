"""Conversation history and context management."""

from dataclasses import dataclass, field


@dataclass
class Message:
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class ConversationContext:
    max_turns: int = 20
    messages: list[Message] = field(default_factory=list)
    system_prompt: str = ""

    def set_system_prompt(self, prompt: str) -> None:
        self.system_prompt = prompt

    def add_message(self, role: str, content: str) -> None:
        self.messages.append(Message(role=role, content=content))

    def get_messages(self) -> list[dict]:
        """Get messages formatted for LLM API."""
        result = []
        if self.system_prompt:
            result.append({"role": "system", "content": self.system_prompt})
        # Keep last N turns (each turn = user + assistant = 2 messages)
        kept = self.messages[-self.max_turns * 2 :]
        for msg in kept:
            result.append({"role": msg.role, "content": msg.content})
        return result

    def clear(self) -> None:
        self.messages.clear()

    def summary(self) -> str:
        return f"{len(self.messages)} messages, system prompt: {'set' if self.system_prompt else 'default'}"
