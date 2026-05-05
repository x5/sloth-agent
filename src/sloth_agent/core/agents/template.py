"""Pure AgentTemplate dataclass — no DB/HTTP dependencies."""

from dataclasses import dataclass, field


@dataclass
class AgentTemplate:
    """Represents an agent template. Pure data, no DB coupling."""

    id: str = ""
    name: str = ""
    role: str = ""
    tools: list[str] = field(default_factory=list)  # agent-specific extras beyond role tools
    system_prompt: str = ""
