"""Shell execution: run_command.

Canonical spec: docs/specs/20260416-02-tools-invocation-spec.md §10.5.2
"""

import subprocess

from sloth_agent.core.tools.models import ToolCategory
from sloth_agent.core.tools.tool_registry import Tool, ToolMetadata


class RunCommandTool(Tool):
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
