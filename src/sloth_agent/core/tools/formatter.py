"""ResultFormatter — formats tool results for different consumers.

Spec: tools-invocation-spec §4.4
"""

from sloth_agent.core.tools.models import ToolResult


class ResultFormatter:
    """Formats ToolResult for human, LLM, and log consumers."""

    def for_human(self, result: ToolResult) -> str:
        """Human-readable format."""
        if result.success:
            header = f"[OK] {result.tool_name} ({result.duration_ms}ms)"
            if result.output:
                # Truncate long output
                output = result.output
                if len(output) > 5000:
                    output = output[:5000] + f"\n... ({len(result.output) - 5000} more chars)"
                return f"{header}\n{output}"
            return header
        else:
            return f"[FAIL] {result.tool_name}: {result.error}"

    def for_llm(self, result: ToolResult) -> str:
        """LLM context format — concise and structured."""
        if result.success:
            output = result.output
            if len(output) > 3000:
                output = output[:3000] + f"\n... truncated"
            return f"Tool '{result.tool_name}' succeeded:\n{output}"
        else:
            return f"Tool '{result.tool_name}' failed: {result.error}"

    def for_log(self, result: ToolResult) -> str:
        """Audit log format."""
        status = "OK" if result.success else "FAIL"
        return (
            f"{status} {result.tool_name} "
            f"duration={result.duration_ms}ms "
            f"retries={result.retries}"
            + (f" error={result.error}" if result.error else "")
        )
