"""Enhanced REPL with tool call execution, user confirmation, and autonomous mode."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.markdown import Markdown

from sloth_agent.chat.autonomous import AutonomousController, AutonomousState
from sloth_agent.chat.session import SessionManager
from sloth_agent.cli.chat_ux import ChatUX
from sloth_agent.core.config import Config
from sloth_agent.core.config_manager import ConfigManager
from sloth_agent.core.tools.models import ToolCallRequest
from sloth_agent.core.tools.orchestrator import ToolOrchestrator
from sloth_agent.core.tools.tool_registry import ToolRegistry
from sloth_agent.memory.skill_registry import SkillRegistry
from sloth_agent.memory.skills import SkillManager
from sloth_agent.providers.llm_providers import LLMMessage, LLMProviderManager

logger = logging.getLogger("sloth.repl")

_SLASH_COMMANDS = {
    "/clear": "清空对话历史",
    "/context": "查看上下文使用量",
    "/tools": "列出可用工具",
    "/skills": "列出可用技能",
    "/scenarios": "列出工作流场景",
    "/skill <name>": "按名称执行技能",
    "/start autonomous": "启动自主模式",
    "/stop": "停止自主模式",
    "/status": "查看自主模式状态",
    "/help": "显示帮助",
    "/quit": "退出聊天",
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
        self.skill_registry = self._init_skill_registry()
        self.current_model = model
        self.current_provider = provider
        self._session = None
        self.ux = ChatUX(self.console)

    def loop(self) -> None:
        """Main REPL loop."""
        # Create or load a chat session
        workspace = self.config_manager.get("workspace", "./workspace")
        session_id = self.session_manager.create_session(
            name="chat",
            workspace=workspace,
        )
        self._session = self.session_manager.get_session(session_id)

        # Show welcome screen
        ws = Path(workspace) if workspace else Path.cwd()
        skill_count = 0
        if self.skill_registry:
            skill_count = len(self.skill_registry.get_all())
        self.ux.show_welcome(
            workspace=ws,
            model_info=self.current_model or "default",
            skill_count=skill_count,
        )

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

        # Save session on exit
        self._save_current_session()

    def _init_skill_registry(self) -> SkillRegistry:
        """Initialize SkillRegistry with builtin + local skills."""
        try:
            builtin_dir = Path(__file__).parent.parent.parent.parent / "skills" / "builtin"
            local_dir = Path(__file__).parent.parent.parent.parent / "local_skills"
            return SkillRegistry(
                builtin_dir=builtin_dir if builtin_dir.exists() else None,
                local_dir=local_dir if local_dir.exists() else None,
            )
        except Exception:
            return None

    def _save_current_session(self) -> None:
        """Persist current session to disk."""
        if self._session:
            self.session_manager.save_session(self._session)

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
            self.console.print("[dim]对话已清空[/dim]")

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
                    self.console.print(f"  {s.get('id', '?')} - {s.get('description', '?')}")
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
            skill_count = 0
            try:
                skills = self.skill_manager.list_skills()
                skill_count = len(skills) if skills else 0
            except Exception:
                pass
            session_id = self._session.session_id if self._session else ""
            self.ux.show_natural_help(
                session_id=session_id,
                skill_count=skill_count,
            )

        else:
                self.console.print(f"[red]未知命令: {cmd}[/red]")

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
            self.console.print(f"[red]错误: {e}[/red]")
            return

        # Check if response contains tool calls
        if hasattr(response, "tool_calls") and response.tool_calls:
            self._handle_tool_calls(response)
            if self._session:
                self.session_manager.add_message(
                    self._session.session_id,
                    "assistant",
                    response.content or "",
                )
                self._save_current_session()
        elif response.content:
            self.console.print(Markdown(response.content))
            if self._session:
                self.session_manager.add_message(
                    self._session.session_id,
                    "assistant",
                    response.content,
                )
                self._save_current_session()

    def _handle_tool_calls(self, response: Any) -> None:
        """Execute tool calls with user confirmation for high-risk tools."""
        for tc in response.tool_calls:
            tool_name = tc.get("function", {}).get("name", "unknown")
            tool_args = tc.get("function", {}).get("arguments", "{}")

            # Check if user confirmation is needed
            needs_confirm = tool_name in _HIGH_RISK_TOOLS
            if needs_confirm:
                file_changes = []
                if tool_name in ("write_file", "edit_file"):
                    file_changes.append({
                        "file": str(tool_args.get("path", "unknown")),
                        "lines": "?",
                        "type": "modify" if tool_name == "edit_file" else "new",
                    })
                confirmed = self.ux.show_confirm(
                    file_changes=file_changes,
                    commands=[f"{tool_name}({tool_args})"],
                )
                if not confirmed:
                    self.console.print(f"[dim]已跳过: {tool_name}[/dim]")
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
                    self._save_current_session()
            except Exception as e:
                self.console.print(f"[red]工具错误 ({tool_name}): {e}[/red]")

    def _build_messages(self, user_input: str) -> list:
        """Build message list for LLM."""
        messages = [LLMMessage(
            role="system",
            content="你是 Sloth Agent，一个 AI 开发助手。请用中文回答用户的问题。如果用户输入英文，你可以跟随用户的语言。",
        )]
        if self._session:
            for msg in self._session.messages[-20:]:  # Keep last 20 messages
                messages.append(
                    LLMMessage(role=msg.get("role", "user"), content=msg.get("content", ""))
                )
        else:
            messages.append(LLMMessage(role="user", content=user_input))
        return messages

    def _list_skills(self) -> list:
        """List available skills from SkillRegistry."""
        if self.skill_registry:
            return [
                {"id": sid, "description": desc}
                for sid, desc, enabled in self.skill_registry.list_all()
                if enabled
            ]
        # Fallback to old SkillManager
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
                    skills.append({"id": name, "description": desc})
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
        """Execute a skill by name via SkillRegistry."""
        try:
            skill = None
            if self.skill_registry:
                skill = self.skill_registry.get(name)
            # Fallback to SkillManager
            if skill is None:
                content = self.skill_manager.get_skill_content(name)
                if content:
                    skill = type("MockSkill", (), {"name": name, "content": content})()
            if skill:
                self.console.print(f"[bold]Executing skill: {skill.name}[/bold]")
                self.console.print(Markdown(skill.content))
            else:
                self.console.print(f"[red]Skill '{name}' not found[/red]")
        except Exception as e:
            self.console.print(f"[red]Error executing skill: {e}[/red]")

    def _start_autonomous(self) -> None:
        """Start autonomous mode — runs the real Runner pipeline."""
        if self.autonomous.is_running():
            self.console.print("[yellow]自主模式已在运行[/yellow]")
            return

        # Resolve plan path from workspace
        workspace = self.config_manager.get("workspace", "./workspace")
        ws = Path(workspace)
        plan_path = None
        for name in ["plan.md", "PLAN.md", "开发计划.md"]:
            if (ws / name).exists():
                plan_path = str((ws / name).resolve())
                break

        if not plan_path:
            self.console.print("[red]未找到 plan 文件。请先在工作目录创建 plan.md。[/red]")
            return

        self.console.print(f"[bold green]启动自主模式: {plan_path}[/bold green]")
        try:
            self.autonomous.start(
                task_id=f"chat-autonomous-{uuid.uuid4().hex[:8]}",
                description=f"执行 plan: {plan_path}",
                steps=["解析计划", "构建代码", "审查", "部署"],
                executor=lambda task_status, stop_flag: self._autonomous_pipeline(
                    task_status, stop_flag, plan_path,
                ),
            )
            self.console.print(
                "[dim]自主模式已启动。使用 /status 查看进度。[/dim]"
            )
        except RuntimeError as e:
            self.console.print(f"[red]{e}[/red]")

    def _autonomous_pipeline(
        self, task_status: Any, stop_flag: Any, plan_path: str,
    ) -> None:
        """Real Runner pipeline execution in background thread."""
        from sloth_agent.core.config import load_config
        from sloth_agent.core.runner import Runner, RunState

        task_status.current_step = "初始化"
        config = load_config()
        runner = Runner(config, self.tool_registry, self.llm_manager)

        state = RunState(
            run_id=f"autonomous-{uuid.uuid4().hex[:8]}",
            current_agent="builder",
            current_phase="build",
            phase="running",
            metadata={"plan_path": plan_path},
        )

        # Hook progress updates into task_status
        def _on_turn_end(data):
            task_status.current_step = f"回合 {data.get('turn', '?')}"
            if stop_flag.is_set():
                state.phase = "aborted"
                state.errors.append("用户中止")

        runner.hooks.on("turn.end", _on_turn_end)

        try:
            task_status.current_step = "构建中"
            final_state = runner.run(state)

            if final_state.phase == "completed":
                task_status.result = final_state.output or "Pipeline completed"
                task_status.current_step = "完成"
            else:
                task_status.error = "; ".join(final_state.errors) or f"Phase: {final_state.phase}"
        except Exception as e:
            task_status.error = str(e)
            logger.error(f"Autonomous pipeline error: {e}")

    def _stop_autonomous(self) -> None:
        """Stop autonomous mode."""
        if not self.autonomous.is_running():
            self.console.print("[yellow]自主模式未运行[/yellow]")
            return

        self.console.print("[bold yellow]停止自主模式...[/bold yellow]")
        self.autonomous.stop()
        self.console.print("[dim]自主模式已停止[/dim]")

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
