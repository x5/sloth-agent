"""File operations: read_file, write_file, edit_file.

Canonical spec: docs/specs/20260416-02-tools-invocation-spec.md §10.5.1
"""

from pathlib import Path

from sloth_agent.core.tools.models import ToolCategory
from sloth_agent.core.tools.tool_registry import Tool, ToolMetadata


class ReadFileTool(Tool):
    """Read content from a file."""

    name = "read_file"
    description = "Read content from a file"
    group = "fs"
    risk_level = 1
    permission = "auto"
    category = ToolCategory.READ
    inherit_from = "Claude Code"
    metadata = ToolMetadata(timeout_seconds=30, max_retries=1)

    def execute(self, path: str, encoding: str = "utf-8") -> str:
        return Path(path).read_text(encoding=encoding)

    @staticmethod
    def read_lines(path: str, start: int = 1, end: int | None = None, encoding: str = "utf-8") -> list[str]:
        """按行读取。start 从 1 开始，end=None 读到末尾。"""
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


class WriteFileTool(Tool):
    """Write content to a file."""

    name = "write_file"
    description = "Write content to a file"
    group = "fs"
    risk_level = 2
    permission = "plan_approval"
    category = ToolCategory.WRITE
    inherit_from = "Claude Code"
    metadata = ToolMetadata(timeout_seconds=30, max_retries=1)

    def execute(self, path: str, content: str, encoding: str = "utf-8") -> str:
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


class EditFileTool(Tool):
    """Precise string replacement in a file."""

    name = "edit_file"
    description = "Precisely replace a unique string occurrence in a file"
    group = "fs"
    risk_level = 2
    permission = "plan_approval"
    category = ToolCategory.EDIT
    inherit_from = "Claude Code"
    metadata = ToolMetadata(timeout_seconds=30, max_retries=1)

    def execute(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        encoding: str = "utf-8",
    ) -> str:
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        content = p.read_text(encoding=encoding)

        if old_string not in content:
            raise ValueError(
                f"old_string not found in {file_path}. "
                f"The string must appear exactly once in the file."
            )

        count = content.count(old_string)
        if count > 1:
            raise ValueError(
                f"old_string appears {count} times in {file_path}. "
                f"It must appear exactly once."
            )

        new_content = content.replace(old_string, new_string, 1)
        p.write_text(new_content, encoding=encoding)
        return f"Edited {file_path}: replaced {len(old_string)} chars with {len(new_string)} chars"

    def get_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to the file to edit"},
                    "old_string": {"type": "string", "description": "The exact string to replace (must appear once)"},
                    "new_string": {"type": "string", "description": "The replacement string"},
                    "encoding": {"type": "string", "default": "utf-8"},
                },
                "required": ["file_path", "old_string", "new_string"],
            },
        }
