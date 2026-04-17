"""Enhanced REPL with tool call execution, user confirmation, and autonomous mode."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.markdown import Markdown

from sloth_agent.chat.autonomous import AutonomousController, AutonomousState
from sloth_agent.chat.session import SessionManager
from sloth_agent.core.config import Config
from sloth_agent.core.config_manager import ConfigManager
from sloth_agent.core.tools.models import ToolCallRequest
from sloth_agent.core.tools.orchestrator import ToolOrchestrator
from sloth_agent.core.tools.tool_registry import ToolRegistry
from sloth_agent.memory.skills import SkillManager
from sloth_agent.providers.llm_providers import LLMMessage, LLMProviderManager

logger = logging.getLogger("sloth.repl")

_SLASH_COMMANDS = {
    "/clear": "Clear conversation history",
    "/context": "Show context usage",
    "/tools": "List available tools",
    "/skills": "List available skills",
    "/scenarios": "List workflow scenarios",
    "/skill <name>": "Execute a skill by name",
    "/start autonomous": "Start autonomous mode",
    "/stop": "Stop autonomous mode",
    "/status": "Show autonomous mode status",
    "/help": "Show this help",
    "/quit": "Exit chat mode",
}

_HIGH_RISK_TOOLS = {"run_command", "write_file", "edit_file", "delete_file"}


class EnhancedChatSession:
    """Interactive chat REPL with tool execution and autonomous mode."""

    def __init__(
        self,
        model: str | None = None,
        provider: str | None = None,
    ):
        self.console = Console()
        self.config_manager = ConfigManager()
        self._config = Config()
        self.tool_registry = ToolRegistry(self._config)
        self.llm_manager = LLMProviderManager()
        self.session_manager = SessionManager()
        self.autonomous = AutonomousController()
        self.skill_manager = SkillManager()
        self.current_model = model
        self.current_provider = provider
        self._session = None

    def loop(self) -> None:
        """Main REPL loop."""
        # Create or load a chat session
        workspace = self.config_manager.get("workspace", "./workspace")
        session_id = self.session_manager.create_session(
            name="chat",
            workspace=workspace,
        )
        self._session = self.session_manager.get_session(session_id)

        self.console.print("[bold green]Sloth Chat[/bold green] (type /help)")
        self.console.print(f"Session: {session_id}")
        self.console.print()

        while True:
            try:
                user_input = input("sloth> ").strip()
            except (EOFError, KeyboardInterrupt):
                self.console.print("\n[bold]Goodbye![/bold]")
                break

            if not user_input:
                continue

            if user_input.startswith("/"):
                if self._handle_slash(user_input):
                    break
                continue

            self._process_message(user_input)

    def _handle_slash(self, command: str) -> bool:
        """Handle slash command. Returns True to exit."""
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd in ("/quit", "/exit"):
            self.console.print("[bold]Goodbye![/bold]")
            return True

        if cmd == "/clear":
            if self._session:
                self._session.messages.clear()
            self.console.print("[dim]Conversation cleared[/dim]")

        elif cmd == "/context":
            if self._session:
                msg_count = len(self._session.messages)
                self.console.print(
                    f"[dim]Messages: {msg_count}, "
                    f"Session: {self._session.session_id}[/dim]"
                )

        elif cmd == "/tools":
            tools = self.tool_registry.list_tools()
            for t in tools:
                risk = t.get("risk_level", "?")
                self.console.print(
                    f"  {t['name']} (risk: {risk}) - {t['description']}"
                )

        elif cmd == "/skills":
            skills = self._list_skills()
            if skills:
                for s in skills:
                    self.console.print(f"  {s.get('name', '?')} - {s.get('description', '?')}")
            else:
                self.console.print("[dim]No skills found[/dim]")

        elif cmd == "/scenarios":
            self._list_scenarios()

        elif cmd == "/skill":
            if not args:
                self.console.print("[red]Usage: /skill <name>[/red]")
            else:
                self._execute_skill(args.strip())

        elif cmd == "/start":
            if args.lower().startswith("autonomous"):
                self._start_autonomous()
            else:
                self.console.print("[red]Usage: /start autonomous[/red]")

        elif cmd == "/stop":
            self._stop_autonomous()

        elif cmd == "/status":
            self._show_status()

        elif cmd == "/help":
            self.console.print("[bold]Slash commands:[/bold]")
            for cmd_name, desc in _SLASH_COMMANDS.items():
                self.console.print(f"  {cmd_name}: {desc}")

        else:
            self.console.print(f"[red]Unknown command: {cmd}[/red]")

        return False

    def _process_message(self, user_input: str) -> None:
        """Process a chat message, supporting tool calls with user confirmation."""
        # Save user message to session
        if self._session:
            self.session_manager.add_message(
                self._session.session_id,
                "user",
                user_input,
            )

        messages = self._build_messages(user_input)
        try:
            response = asyncio.run(
                self.llm_manager.chat(
                    messages,
                    model=self.current_model,
                    provider=self.current_provider,
                )
            )
        except Exception as e:
            logger.error(f"LLM error: {e}")
            self.console.print(f"[red]Error: {e}[/red]")
            return

        # Check if response contains tool calls
        if hasattr(response, "tool_calls") and response.tool_calls:
            self._handle_tool_calls(response)
        elif response.content:
            self.console.print(Markdown(response.content))
            if self._session:
                self.session_manager.add_message(
                    self._session.session_id,
                    "assistant",
                    response.content,
                )

    def _handle_tool_calls(self, response: Any) -> None:
        """Execute tool calls with user confirmation for high-risk tools."""
        for tc in response.tool_calls:
            tool_name = tc.get("function", {}).get("name", "unknown")
            tool_args = tc.get("function", {}).get("arguments", "{}")

            # Check if user confirmation is needed
            needs_confirm = tool_name in _HIGH_RISK_TOOLS
            if needs_confirm:
                self.console.print(
                    f"\n[yellow]Tool '{tool_name}' requires confirmation.[/yellow]"
                )
                try:
                    answer = input("Execute? (y/N) ").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    answer = "n"
                if answer not in ("y", "yes"):
                    self.console.print(f"[dim]Skipped: {tool_name}[/dim]")
                    continue

            # Execute the tool
            try:
                args_dict = json.loads(tool_args) if isinstance(tool_args, str) else tool_args
                request = ToolCallRequest(
                    id=tc.get("id", ""),
                    name=tool_name,
                    arguments=args_dict,
                )
                result = self.tool_registry.execute_tool(tool_name, **args_dict)
                self.console.print(
                    f"[dim]Tool {tool_name}: {str(result)[:200]}[/dim]"
                )

                # Save tool result to session
                if self._session:
                    self.session_manager.add_message(
                        self._session.session_id,
                        "tool",
                        f"[{tool_name}] {result}",
                    )
            except Exception as e:
                self.console.print(f"[red]Tool error ({tool_name}): {e}[/red]")

    def _build_messages(self, user_input: str) -> list:
        """Build message list for LLM."""
        messages = [LLMMessage(role="system", content="You are Sloth Agent.")]
        if self._session:
            for msg in self._session.messages[-20:]:  # Keep last 20 messages
                messages.append(
                    LLMMessage(role=msg.get("role", "user"), content=msg.get("content", ""))
                )
        else:
            messages.append(LLMMessage(role="user", content=user_input))
        return messages

    def _list_skills(self) -> list:
        """List available skills."""
        try:
            skills_dir = Path(__file__).parent.parent.parent.parent / "local_skills"
            if not skills_dir.exists():
                return []
            skills = []
            for skill_dir in skills_dir.iterdir():
                skill_file = skill_dir / "SKILL.md"
                if skill_file.exists():
                    content = skill_file.read_text()
                    name = skill_dir.name
                    desc = ""
                    for line in content.split("\n")[:20]:
                        if line.startswith("description:"):
                            desc = line.split(":", 1)[1].strip()
                            break
                    skills.append({"name": name, "description": desc})
            return skills
        except Exception:
            return []

    def _list_scenarios(self) -> None:
        """List available workflow scenarios."""
        try:
            from sloth_agent.workflow.registry import PhaseRegistry

            reg = PhaseRegistry()
            for sid in reg.list_scenarios():
                phases = reg.get_by_scenario(sid)
                names = ", ".join(p.name for p in phases)
                self.console.print(f"  {sid}: {names}")
        except ImportError:
            self.console.print("[dim]Scenario registry not yet available[/dim]")

    def _execute_skill(self, name: str) -> None:
        """Execute a skill by name."""
        try:
            skill = self.skill_manager.get_skill(name)
            if skill:
                self.console.print(f"[bold]Executing skill: {name}[/bold]")
                self.console.print(Markdown(skill.content))
            else:
                self.console.print(f"[red]Skill '{name}' not found[/red]")
        except Exception as e:
            self.console.print(f"[red]Error executing skill: {e}[/red]")

    def _start_autonomous(self) -> None:
        """Start autonomous mode."""
        if self.autonomous.is_running():
            self.console.print("[yellow]Autonomous mode is already running[/yellow]")
            return

        self.console.print("[bold green]Starting autonomous mode...[/bold green]")
        try:
            self.autonomous.start(
                task_id="chat-autonomous",
                description="Autonomous execution from chat",
                steps=["Parse plan", "Build", "Review", "Deploy"],
                executor=self._autonomous_executor,
            )
            self.console.print(
                "[dim]Autonomous mode started. Use /status to check progress.[/dim]"
            )
        except RuntimeError as e:
            self.console.print(f"[red]{e}[/red]")

    def _stop_autonomous(self) -> None:
        """Stop autonomous mode."""
        if not self.autonomous.is_running():
            self.console.print("[yellow]Autonomous mode is not running[/yellow]")
            return

        self.console.print("[bold yellow]Stopping autonomous mode...[/bold yellow]")
        self.autonomous.stop()
        self.console.print("[dim]Autonomous mode stopped[/dim]")

    def _show_status(self) -> None:
        """Show autonomous mode status."""
        status = self.autonomous.get_status()
        state = status.get("state", "idle")
        self.console.print("[bold]Autonomous Mode Status:[/bold]")
        self.console.print(f"  State: {state}")
        if status.get("task_id"):
            self.console.print(f"  Task: {status['task_id']}")
            self.console.print(f"  Description: {status.get('description', 'N/A')}")
            self.console.print(f"  Current step: {status.get('current_step', 'N/A')}")
            elapsed = status.get("elapsed_seconds", 0)
            self.console.print(f"  Elapsed: {elapsed:.0f}s")

    def _autonomous_executor(self, task_status: Any, stop_flag: Any) -> None:
        """Simple autonomous executor placeholder."""
        for step in task_status.steps:
            if stop_flag.is_set():
                break
            task_status.current_step = step
            logger.info(f"Autonomous step: {step}")
            import time
            time.sleep(0.5)  # Placeholder
