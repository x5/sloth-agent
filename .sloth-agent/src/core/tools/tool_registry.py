"""Tool Registry - Central registry for all available tools."""

import logging
from abc import ABC, abstractmethod
from typing import Any

from sloth_agent.core.config import Config

logger = logging.getLogger("tools")


class Tool(ABC):
    """Base class for all tools."""

    name: str = ""
    description: str = ""
    risk_level: int = 1  # 1=low, 4=extreme

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """Execute the tool."""
        pass


class FileReadTool(Tool):
    """Read files from the filesystem."""

    name = "read_file"
    description = "Read content from a file"
    risk_level = 1

    def execute(self, path: str, encoding: str = "utf-8") -> str:
        from pathlib import Path

        return Path(path).read_text(encoding=encoding)


class FileWriteTool(Tool):
    """Write content to files."""

    name = "write_file"
    description = "Write content to a file"
    risk_level = 2

    def execute(self, path: str, content: str, encoding: str = "utf-8") -> bool:
        from pathlib import Path

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(content, encoding=encoding)
        return True


class BashTool(Tool):
    """Execute bash commands."""

    name = "bash"
    description = "Execute bash/shell commands"
    risk_level = 3

    def execute(self, command: str, timeout: int = 300) -> dict:
        import subprocess

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        except subprocess.TimeoutExpired:
            return {"returncode": -1, "stdout": "", "stderr": "Command timed out"}


class GitTool(Tool):
    """Git operations."""

    name = "git"
    description = "Execute git commands"
    risk_level = 3

    def execute(self, command: str, timeout: int = 60) -> dict:
        import subprocess

        result = subprocess.run(
            f"git {command}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }


class SearchTool(Tool):
    """Search for patterns in files."""

    name = "search"
    description = "Search for text patterns in files"
    risk_level = 1

    def execute(self, pattern: str, path: str = ".") -> list[dict]:
        import re
        from pathlib import Path

        results = []
        path = Path(path)

        for file in path.rglob("*"):
            if file.is_file() and file.stat().st_size < 10_000_000:  # Skip >10MB
                try:
                    content = file.read_text(encoding="utf-8", errors="ignore")
                    for i, line in enumerate(content.splitlines(), 1):
                        if re.search(pattern, line):
                            results.append(
                                {"file": str(file), "line": i, "content": line.strip()}
                            )
                except Exception:
                    pass

        return results


class ToolRegistry:
    """Central registry for all available tools."""

    def __init__(self, config: Config):
        self.config = config
        self._tools: dict[str, Tool] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        """Register built-in tools."""
        self._tools["read_file"] = FileReadTool()
        self._tools["write_file"] = FileWriteTool()
        self._tools["bash"] = BashTool()
        self._tools["git"] = GitTool()
        self._tools["search"] = SearchTool()

    def get_tool(self, name: str) -> Tool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[dict]:
        """List all available tools."""
        return [
            {"name": t.name, "description": t.description, "risk_level": t.risk_level}
            for t in self._tools.values()
        ]

    def register_tool(self, tool: Tool):
        """Register a new tool."""
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def execute_tool(self, name: str, **kwargs) -> Any:
        """Execute a tool by name."""
        tool = self.get_tool(name)
        if not tool:
            raise ValueError(f"Unknown tool: {name}")

        return tool.execute(**kwargs)
