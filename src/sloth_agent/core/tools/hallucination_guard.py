"""HallucinationGuard — validates tool calls before execution.

Spec: architecture-overview §7.1.3
"""

from pathlib import Path
from typing import Any

from sloth_agent.core.tools.models import RejectedCall, ToolCallRequest

# Dangerous command patterns
COMMAND_BLACKLIST = [
    "rm -rf",
    "sudo",
    "chmod 777",
    "curl | sh",
    "curl|sh",
    "curl http",
    "wget | bash",
    "wget|bash",
    "wget http",
    "mkfs",
    "dd if=",
    "> /dev/",
    "shutdown",
    "reboot",
]

# Dangerous path patterns
PATH_DANGGER_PATTERNS = ["..", "~", "$(", "`"]

MAX_COMMAND_LENGTH = 2000
MAX_PATTERN_LENGTH = 200


class HallucinationGuard:
    """Validates tool call requests for safety and correctness."""

    def __init__(self, workspace: str | None = None):
        self.workspace = workspace

    def validate_tool_call(
        self, call: ToolCallRequest
    ) -> ToolCallRequest | RejectedCall:
        """Validate a tool call request. Returns validated call or rejection."""
        match call.tool_name:
            case "read_file" | "write_file" | "edit_file":
                return self._validate_file_path(call)
            case "run_command":
                return self._validate_command(call)
            case "glob" | "grep" | "search":
                return self._validate_pattern(call)
            case _:
                return call  # Unknown tool, let it through

    def _validate_file_path(
        self, call: ToolCallRequest
    ) -> ToolCallRequest | RejectedCall:
        path = call.params.get("path", "")

        # Check for dangerous patterns
        for pattern in PATH_DANGGER_PATTERNS:
            if pattern in path:
                return RejectedCall(
                    reason=f"Path contains dangerous pattern: {pattern}",
                    tool_name=call.tool_name,
                )

        # Check workspace boundary
        if not self._is_within_workspace(path):
            return RejectedCall(
                reason=f"Path is outside workspace: {path}",
                tool_name=call.tool_name,
            )

        # read_file / edit_file require file to exist
        if call.tool_name in ("read_file", "edit_file"):
            if not Path(path).exists():
                return RejectedCall(
                    reason=f"File does not exist: {path}",
                    tool_name=call.tool_name,
                )

        return call

    def _validate_command(
        self, call: ToolCallRequest
    ) -> ToolCallRequest | RejectedCall:
        cmd = call.params.get("command", "")

        if len(cmd) > MAX_COMMAND_LENGTH:
            return RejectedCall(
                reason=f"Command exceeds max length ({len(cmd)} > {MAX_COMMAND_LENGTH})",
                tool_name=call.tool_name,
            )

        cmd_lower = cmd.lower()
        for banned in COMMAND_BLACKLIST:
            if banned in cmd_lower:
                return RejectedCall(
                    reason=f"Command contains banned pattern: {banned}",
                    tool_name=call.tool_name,
                )

        return call

    def _validate_pattern(
        self, call: ToolCallRequest
    ) -> ToolCallRequest | RejectedCall:
        pattern = call.params.get("pattern", "")

        if len(pattern) > MAX_PATTERN_LENGTH:
            return RejectedCall(
                reason=f"Pattern exceeds max length ({len(pattern)} > {MAX_PATTERN_LENGTH})",
                tool_name=call.tool_name,
            )

        return call

    def _is_within_workspace(self, path: str) -> bool:
        """Check if a path is within the workspace boundary."""
        if not self.workspace:
            return True  # No workspace configured, allow all
        try:
            resolved = Path(path).resolve()
            workspace_resolved = Path(self.workspace).resolve()
            return str(resolved).startswith(str(workspace_resolved))
        except (OSError, ValueError):
            return False
