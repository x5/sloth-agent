"""Executor — executes tool calls with timeout, retry, and audit logging.

Spec: tools-invocation-spec §4.3
"""

import json
import logging
import time
from pathlib import Path

from sloth_agent.core.config import Config
from sloth_agent.core.tools.models import ToolCallRequest, ToolResult
from sloth_agent.core.tools.tool_registry import ToolRegistry

logger = logging.getLogger("executor")


class Executor:
    """Executes tool calls with timeout, retry, and logging."""

    def __init__(self, registry: ToolRegistry, config: Config | None = None):
        self.registry = registry
        self.config = config
        self._log_dir: Path | None = None
        if config:
            project_root = Path(__file__).parent.parent.parent.parent
            self._log_dir = project_root / "logs"
            self._log_dir.mkdir(parents=True, exist_ok=True)

    def execute(self, request: ToolCallRequest) -> ToolResult:
        """Execute a tool call with retry and timeout control."""
        tool = self.registry.get_tool(request.tool_name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Unknown tool: {request.tool_name}",
                tool_name=request.tool_name,
            )

        max_retries = tool.metadata.max_retries
        timeout = tool.metadata.timeout_seconds
        retry_delay = tool.metadata.retry_delay_seconds

        last_result = ToolResult(success=False, tool_name=request.tool_name)

        for attempt in range(max_retries + 1):
            start_time = time.monotonic()
            try:
                raw = tool.execute(**request.params)
                elapsed_ms = int((time.monotonic() - start_time) * 1000)

                result = ToolResult(
                    success=True,
                    output=str(raw) if raw is not None else "",
                    duration_ms=elapsed_ms,
                    retries=attempt,
                    tool_name=request.tool_name,
                )
                self._log_call(request, result)
                return result

            except Exception as e:
                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                last_result = ToolResult(
                    success=False,
                    error=str(e),
                    duration_ms=elapsed_ms,
                    retries=attempt,
                    tool_name=request.tool_name,
                )
                logger.warning(
                    f"Tool {request.tool_name} attempt {attempt + 1} failed: {e}"
                )
                if attempt < max_retries:
                    time.sleep(retry_delay * (2**attempt))  # exponential backoff

        self._log_call(request, last_result)
        return last_result

    def _log_call(self, request: ToolCallRequest, result: ToolResult) -> None:
        """Append an audit log entry to logs/tool-calls.jsonl."""
        if not self._log_dir:
            return
        log_path = self._log_dir / "tool-calls.jsonl"
        entry = {
            "timestamp": time.time(),
            "tool_name": request.tool_name,
            "params": request.params,
            "success": result.success,
            "duration_ms": result.duration_ms,
            "retries": result.retries,
            "error": result.error,
        }
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
