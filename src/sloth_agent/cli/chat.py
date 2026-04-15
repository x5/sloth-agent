"""Interactive chat REPL."""

import asyncio
import logging
from rich.console import Console
from rich.markdown import Markdown

from sloth_agent.cli.context import ConversationContext, Message
from sloth_agent.providers.llm_providers import LLMProviderManager, LLMMessage
from sloth_agent.core.tools.tool_registry import ToolRegistry

logger = logging.getLogger("sloth.chat")

_SYSTEM_PROMPT = """You are Sloth Agent, an AI development assistant.
You can help with coding, debugging, code review, and project planning.
Use available tools when needed. Be concise and helpful."""

_SLASH_COMMANDS = {
    "/clear": "Clear conversation history",
    "/context": "Show context usage",
    "/tools": "List available tools",
    "/skills": "List available skills",
    "/scenarios": "List workflow scenarios",
    "/help": "Show this help",
    "/quit": "Exit chat mode",
}


class ChatSession:
    """Interactive chat REPL."""

    def __init__(self, model: str | None = None, provider: str | None = None):
        self.console = Console()
        self.ctx = ConversationContext()
        self.ctx.set_system_prompt(_SYSTEM_PROMPT)
        self.tool_registry = ToolRegistry()
        self.llm_manager = LLMProviderManager()
        self.current_model = model
        self.current_provider = provider

    def loop(self) -> None:
        """Main REPL loop."""
        self.console.print("[bold green]Sloth Chat[/bold green] (type /help)")
        self.console.print()

        while True:
            try:
                user_input = input("sloth> ").strip()
            except (EOFError, KeyboardInterrupt):
                self.console.print("\n[bold]Goodbye![/bold]")
                break

            if not user_input:
                continue

            # Handle slash commands
            if user_input.startswith("/"):
                if self._handle_slash(user_input):
                    break
                continue

            # Process chat message
            self._process_message(user_input)

    def _handle_slash(self, command: str) -> bool:
        """Handle slash command. Returns True to exit."""
        parts = command.split()
        cmd = parts[0].lower()

        if cmd in ("/quit", "/exit"):
            self.console.print("[bold]Goodbye![/bold]")
            return True
        elif cmd == "/clear":
            self.ctx.clear()
            self.console.print("[dim]Conversation cleared[/dim]")
        elif cmd == "/context":
            self.console.print(f"[dim]{self.ctx.summary()}[/dim]")
        elif cmd == "/tools":
            tools = self.tool_registry.list_tools()
            for t in tools:
                self.console.print(f"  {t['name']} (risk: {t['risk_level']}) - {t['description']}")
        elif cmd == "/skills":
            try:
                from sloth_agent.workflow.registry import SkillRegistry

                skills = SkillRegistry.get_all()
                for s in skills:
                    self.console.print(f"  /{s.id} - {s.description}")
            except ImportError:
                self.console.print("[dim]Skill registry not yet available[/dim]")
        elif cmd == "/scenarios":
            try:
                from sloth_agent.workflow.registry import PhaseRegistry

                reg = PhaseRegistry()
                for sid in reg.list_scenarios():
                    phases = reg.get_by_scenario(sid)
                    names = ", ".join(p.name for p in phases)
                    self.console.print(f"  {sid}: {names}")
            except ImportError:
                self.console.print("[dim]Scenario registry not yet available[/dim]")
        elif cmd == "/help":
            self.console.print("[bold]Slash commands:[/bold]")
            for cmd_name, desc in _SLASH_COMMANDS.items():
                self.console.print(f"  {cmd_name}: {desc}")
        else:
            self.console.print(f"[red]Unknown command: {cmd}[/red]")

        return False

    def _process_message(self, user_input: str) -> None:
        """Process a chat message through the LLM."""
        self.ctx.add_message("user", user_input)

        # Get LLM response
        messages = self.ctx.get_messages()
        llm_messages = [LLMMessage(role=m["role"], content=m["content"]) for m in messages]

        try:
            response = asyncio.run(
                self.llm_manager.chat(
                    llm_messages,
                    model=self.current_model,
                    provider=self.current_provider,
                )
            )
        except Exception as e:
            logger.error(f"LLM error: {e}")
            self.console.print(f"[red]Error: {e}[/red]")
            return

        # Display and store response
        self.ctx.add_message("assistant", response.content)
        if response.content.strip():
            self.console.print(Markdown(response.content))
