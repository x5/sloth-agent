"""Tool Registry — Tool base class + Registry.

Canonical spec: docs/specs/20260416-02-tools-invocation-spec.md §10
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from sloth_agent.core.config import Config
from sloth_agent.core.tools.models import ToolCategory

logger = logging.getLogger("tools")


class ToolMetadata(BaseModel):
    timeout_seconds: int = 60
    max_retries: int = 0
    retry_delay_seconds: float = 1.0
    requires_approval: bool = False
    rollback_strategy: str = "none"  # "none" | "auto" | "manual"


class Tool(ABC):
    """Base class for all tools.

    Canonical spec: 20260416-02-tools-invocation-spec.md §10.4.1
    """

    name: str = ""
    description: str = ""
    group: str = ""                          # "fs" | "runtime" | "code" | "task" | "web" | "sloth" | "interaction"
    risk_level: int = 1                      # 1-4
    permission: str = "auto"                 # "auto" | "plan_approval" | "explicit_approval" | "high_risk"
    category: ToolCategory = ToolCategory.READ
    inherit_from: str | None = None          # "Claude Code" | "Open Claw" | "Sloth" | None
    metadata: ToolMetadata = Field(default_factory=ToolMetadata)
    params: dict = Field(default_factory=dict)

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """Execute the tool."""
        pass

    def get_schema(self) -> dict:
        """Generate OpenAI-compatible function calling schema."""
        raise NotImplementedError("Subclasses should implement get_schema()")


class FileReadTool(Tool):
    """Read files from the filesystem."""

    name = "read_file"
    description = "Read content from a file"
    group = "fs"
    risk_level = 1
    permission = "auto"
    category = ToolCategory.READ
    inherit_from = "Claude Code"
    metadata = ToolMetadata(timeout_seconds=30, max_retries=1)

    def execute(self, path: str, encoding: str = "utf-8") -> str:
        from pathlib import Path
        return Path(path).read_text(encoding=encoding)

    @staticmethod
    def read_lines(path: str, start: int = 1, end: int | None = None, encoding: str = "utf-8") -> list[str]:
        """Read lines from a file. start is 1-based. end=None reads to EOF."""
        from pathlib import Path
        lines = Path(path).read_text(encoding=encoding).splitlines()
        start_idx = max(0, start - 1)
        if end is None:
            return lines[start_idx:]
        return lines[start_idx:end]

    def get_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to read"},
                    "encoding": {"type": "string", "default": "utf-8"},
                },
                "required": ["path"],
            },
        }


class FileWriteTool(Tool):
    """Write content to files."""

    name = "write_file"
    description = "Write content to a file"
    group = "fs"
    risk_level = 2
    permission = "plan_approval"
    category = ToolCategory.WRITE
    inherit_from = "Claude Code"
    metadata = ToolMetadata(timeout_seconds=30, max_retries=1)

    def execute(self, path: str, content: str, encoding: str = "utf-8") -> str:
        from pathlib import Path
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding=encoding)
        return f"Written {len(content)} bytes to {path}"

    def get_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to write"},
                    "content": {"type": "string", "description": "Content to write"},
                    "encoding": {"type": "string", "default": "utf-8"},
                },
                "required": ["path", "content"],
            },
        }


class BashTool(Tool):
    """Execute bash/shell commands."""

    name = "run_command"
    description = "Execute bash/shell commands"
    group = "runtime"
    risk_level = 3
    permission = "explicit_approval"
    category = ToolCategory.EXECUTE
    inherit_from = "Claude Code"
    metadata = ToolMetadata(timeout_seconds=300, max_retries=0)

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

    def get_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute"},
                    "timeout": {"type": "integer", "default": 300},
                },
                "required": ["command"],
            },
        }


class GitTool(Tool):
    """Git operations."""

    name = "git"
    description = "Execute git commands"
    group = "runtime"
    risk_level = 3
    permission = "explicit_approval"
    category = ToolCategory.VCS
    inherit_from = "Claude Code"
    metadata = ToolMetadata(timeout_seconds=60, max_retries=0)

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

    def get_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Git command arguments"},
                    "timeout": {"type": "integer", "default": 60},
                },
                "required": ["command"],
            },
        }


class SearchTool(Tool):
    """Search for patterns in files."""

    name = "search"
    description = "Search for text patterns in files"
    group = "fs"
    risk_level = 1
    permission = "auto"
    category = ToolCategory.SEARCH
    inherit_from = "Claude Code"
    metadata = ToolMetadata(timeout_seconds=120, max_retries=0)

    def execute(self, pattern: str, path: str = ".") -> list[dict]:
        import re
        from pathlib import Path
        results = []
        search_path = Path(path)
        for file in search_path.rglob("*"):
            if file.is_file() and file.stat().st_size < 10_000_000:
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

    def get_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Regex pattern to search for"},
                    "path": {"type": "string", "default": "."},
                },
                "required": ["pattern"],
            },
        }


class ToolRegistry:
    """Central registry for all available tools.

    Canonical spec: 20260416-02-tools-invocation-spec.md §10.4.2
    """

    def __init__(self, config: Config):
        self.config = config
        self._tools: dict[str, Tool] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        """Register built-in tools."""
        for tool_cls in (FileReadTool, FileWriteTool, BashTool, GitTool, SearchTool):
            tool = tool_cls()
            self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Tool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[dict]:
        """List all available tools."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "group": t.group,
                "risk_level": t.risk_level,
                "permission": t.permission,
                "category": t.category.value,
            }
            for t in self._tools.values()
        ]

    def list_by_group(self, group: str) -> list[Tool]:
        """List tools by group."""
        return [t for t in self._tools.values() if t.group == group]

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
