"""CLI User Experience helpers — welcome screen, natural help, confirm cards, progress."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table


# ---------------------------------------------------------------------------
# ASCII banner
# ---------------------------------------------------------------------------

BANNER = r"""
  __ _                   _
 / _(_)                 | |
| |_ _ _ __   __ _ _ __ | |_
|  _| | '_ \ / _` | '_ \| __|
| | | | | | | (_| | | | | |_
|_| |_|_| |_|\__,_|_| |_|\__|
"""


class ChatUX:
    """CLI user experience helpers for non-technical users."""

    def __init__(self, console: Console):
        self.console = console

    # ------------------------------------------------------------------
    # Welcome screen
    # ------------------------------------------------------------------

    def show_welcome(
        self,
        workspace: Path,
        model_info: str = "",
        skill_count: int = 0,
        suggested_questions: list[str] | None = None,
    ) -> None:
        """显示欢迎信息。"""
        self.console.print(f"[bold cyan]{BANNER}[/bold cyan]")

        questions = suggested_questions or self.generate_suggested_questions(workspace)

        # Project info
        info_lines = []
        if model_info:
            info_lines.append(f"模型: {model_info}")
        info_lines.append(f"技能: {skill_count} 已加载")
        info_lines.append(f"目录: {workspace}")

        self.console.print(Panel(
            "\n".join(info_lines),
            title="Sloth Chat",
            border_style="green",
        ))

        # Suggested questions
        self.console.print("[bold]预设问题:[/bold]")
        for i, q in enumerate(questions, 1):
            self.console.print(f"  [cyan]{i}.[/cyan] {q}")
        self.console.print()
        self.console.print("[dim]输入数字选择问题，或直接输入问题。输入 /help 查看帮助。[/dim]")
        self.console.print()

    # ------------------------------------------------------------------
    # Dynamic question generation
    # ------------------------------------------------------------------

    def generate_suggested_questions(self, workspace: Path) -> list[str]:
        """根据工作目录内容动态生成预设问题。"""
        questions: list[str] = []

        # Detect plan files
        for name in ["plan.md", "PLAN.md", "开发计划.md"]:
            if (workspace / name).exists():
                questions.append(f"执行 {name} 中的开发计划")
                break

        # Detect code files
        code_exts = {".py", ".ts", ".js", ".go", ".rs"}
        has_code = any(
            f.suffix in code_exts
            for f in workspace.iterdir()
            if f.is_file()
        )
        if has_code:
            questions.append("审查当前代码质量")

        # Detect test files
        has_tests = any(
            f.name.startswith("test_")
            for f in workspace.iterdir()
            if f.is_file()
        )
        if has_tests:
            questions.append("运行测试并分析报告")

        # Detect TODO
        if (workspace / "TODO.md").exists():
            questions.append("查看当前任务清单")

        # Default question
        if not questions:
            questions.append("帮我写一个需求文档")

        return questions[:4]

    # ------------------------------------------------------------------
    # Natural language help
    # ------------------------------------------------------------------

    def show_natural_help(
        self,
        common_commands: dict[str, str] | None = None,
        advanced_commands: dict[str, str] | None = None,
        session_id: str = "",
        skill_count: int = 0,
    ) -> None:
        """显示自然语言帮助。"""
        # Capabilities
        caps = [
            ("💬", "聊天对话", "用自然语言描述需求，AI 会帮你生成代码"),
            ("🔧", "执行命令", "运行测试、lint、部署脚本等"),
            ("📝", "编辑文件", "读取、修改、创建代码文件"),
            ("🎯", "技能触发", "使用 /skill 激活专业工作流"),
            ("🤖", "自主模式", "输入 /start autonomous 启动自动流水线"),
        ]

        self.console.print("[bold]你可以让我做这些事情:[/bold]")
        for emoji, title, desc in caps:
            self.console.print(f"  {emoji} {title} — {desc}")

        self.console.print()
        self.console.print("[bold]常用命令:[/bold]")

        common = common_commands or {
            "/help": "显示帮助",
            "/clear": "清空对话",
            "/status": "查看状态",
            "/skills": "查看技能",
            "/quit": "退出",
        }
        for cmd, desc in common.items():
            self.console.print(f"  [cyan]{cmd}[/cyan]  {desc}")

        self.console.print()
        self.console.print("[dim]── 高级命令 ──[/dim]")
        advanced = advanced_commands or {
            "/context": "查看上下文",
            "/tools": "查看工具列表",
            "/scenarios": "查看工作流场景",
            "/skill <name>": "执行指定技能",
            "/start autonomous": "启动自主模式",
            "/stop": "停止自主模式",
        }
        for cmd, desc in advanced.items():
            self.console.print(f"  [dim]{cmd}[/dim]  [dim]{desc}[/dim]")

        if session_id or skill_count:
            self.console.print()
            status_parts = []
            if session_id:
                status_parts.append(f"会话: {session_id}")
            if skill_count:
                status_parts.append(f"技能: {skill_count}")
            self.console.print(f"[dim]当前状态: {', '.join(status_parts)}[/dim]")

    # ------------------------------------------------------------------
    # Structured output
    # ------------------------------------------------------------------

    def show_structured_result(
        self, title: str, rows: list[tuple], headers: list[str],
    ) -> None:
        """用 Rich table 呈现结构化信息。"""
        table = Table(title=title, border_style="blue")
        for h in headers:
            table.add_column(h)
        for row in rows:
            table.add_row(*[str(c) for c in row])
        self.console.print(table)

    def show_diff_preview(
        self, filepath: str, diff_lines: list[str],
    ) -> None:
        """显示文件修改预览。"""
        content = "\n".join(diff_lines)
        self.console.print(
            Panel(content, title=f"Diff: {filepath}", border_style="yellow"),
        )

    # ------------------------------------------------------------------
    # Confirmation cards
    # ------------------------------------------------------------------

    def show_confirm(
        self,
        file_changes: list[dict],
        commands: list[str],
    ) -> bool:
        """显示确认卡片，返回用户选择。

        Args:
            file_changes: [{"file": "path", "lines": 17, "type": "modify|new"}]
            commands: 即将运行的命令列表

        Returns:
            True = 用户确认执行，False = 取消
        """
        self.console.print("[bold yellow]即将执行:[/bold yellow]")

        if file_changes:
            table = Table(border_style="yellow")
            table.add_column("文件")
            table.add_column("变更")
            table.add_column("类型")
            for change in file_changes:
                table.add_row(
                    change.get("file", "?"),
                    str(change.get("lines", "?")),
                    change.get("type", "?"),
                )
            self.console.print(table)

        if commands:
            self.console.print("[bold]命令:[/bold]")
            for cmd in commands:
                self.console.print(f"  [yellow]{cmd}[/yellow]")

        try:
            answer = input("\n确认执行？[Y/n]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            answer = "n"

        # Empty input = default Y
        return answer in ("", "y", "yes")

    def show_delete_confirm(
        self, filepath: str, content_preview: str = "",
    ) -> bool:
        """删除文件二次确认，需输入 DELETE 确认。"""
        self.console.print(
            f"[bold red]即将删除: {filepath}[/bold red]",
        )
        if content_preview:
            preview = content_preview[:200]
            self.console.print(f"[dim]内容预览: {preview}[/dim]")

        try:
            answer = input('输入 "DELETE" 确认删除: ').strip()
        except (EOFError, KeyboardInterrupt):
            answer = ""

        return answer == "DELETE"

    # ------------------------------------------------------------------
    # Progress indicators
    # ------------------------------------------------------------------

    def create_progress(self, description: str = "处理中…") -> Progress:
        """创建 spinner 进度指示器。"""
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        )

    def show_status_panel(
        self,
        phase: str,
        progress_pct: int,
        completed: list[str],
        current: str,
        pending: list[str],
        elapsed: str,
    ) -> None:
        """显示自主模式状态面板。"""
        lines: list[str] = []
        lines.append(f"阶段: {phase}  |  进度: {progress_pct}%  |  用时: {elapsed}")
        if completed:
            lines.append(f"已完成: {', '.join(completed)}")
        if current:
            lines.append(f"当前: {current}")
        if pending:
            lines.append(f"待执行: {', '.join(pending)}")

        self.console.print(
            Panel("\n".join(lines), title="自主模式", border_style="blue"),
        )

    def show_error(self, message: str, retry_count: int = 0) -> None:
        """显示错误状态指示。"""
        extra = f" (重试 {retry_count})" if retry_count > 0 else ""
        self.console.print(f"[bold red]错误:{extra}[/bold red] {message}")
