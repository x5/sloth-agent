"""Context window management for Builder Agent.

Supports token-based truncation, summary compression, and critical info protection.
"""

from __future__ import annotations

from sloth_agent.core.token_counter import TokenCounter


class ContextWindowManager:
    """Manage agent context window with token-based truncation and summary compression."""

    def __init__(
        self,
        model: str = "gpt-4",
        max_tokens: int = 128_000,
        output_reserve: int = 15_000,
        max_history_turns: int = 20,
    ):
        self.model = model
        self.max_tokens = max_tokens
        self.output_reserve = output_reserve
        self.max_history_turns = max_history_turns
        self.available = max_tokens - output_reserve
        self.token_counter = TokenCounter()

        # Summary compression state
        self._summary: str = ""
        self._summary_turns: int = 0

    def build_messages(
        self, system: str, history: list, tool_results: list, user_msg: str
    ) -> list:
        """Build message list within token budget."""
        budget = self.available

        # System prompt — always preserved (critical info)
        sys_tokens = self.token_counter.count(system)
        budget -= sys_tokens

        # User message — always preserved
        user_tokens = self.token_counter.count(user_msg)
        budget -= user_tokens

        # Fit tool results (most recent first, with compression)
        fitted_tools, budget = self._fit_tool_results(tool_results, budget)

        # Add summary of early conversation if it exists
        if self._summary:
            summary_tokens = self.token_counter.count(self._summary)
            if budget - summary_tokens > 0:
                fitted_tools.insert(0, {"role": "system", "content": f"[Earlier conversation summary: {self._summary}]"})
                budget -= summary_tokens

        # Fit history (most recent first)
        fitted_history = self._fit_history(history, budget)

        return (
            [{"role": "system", "content": system}]
            + fitted_tools
            + fitted_history
            + [{"role": "user", "content": user_msg}]
        )

    def generate_summary(self, early_messages: list[dict]) -> str:
        """Generate a text summary of early conversation turns.

        This is a rule-based summary — in production, an LLM could generate
        a richer summary. Here we concatenate truncated user/assistant pairs.
        """
        parts = []
        for msg in early_messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:200]
            parts.append(f"{role}: {content}")
        self._summary = " | ".join(parts)
        self._summary_turns = len(early_messages) // 2
        return self._summary

    def should_compress(self, messages: list[dict]) -> bool:
        """Check if messages exceed budget and need compression."""
        total = self.token_counter.count_messages(messages)
        return total > self.available

    def inject_skills(self, skill_ids: list[str], skill_manager) -> str:
        """Concatenate specified skills into an injectable prompt string."""
        parts = []
        for sid in skill_ids:
            content = skill_manager.get_skill_content(sid)
            if content:
                parts.append(f"## Skill: {sid}\n{content}")
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Internal: fitting logic
    # ------------------------------------------------------------------

    def _fit_tool_results(self, tool_results: list, budget: int) -> tuple[list, int]:
        fitted = []
        for tool_result in reversed(tool_results):
            tokens = self.token_counter.count(str(tool_result))
            if budget - tokens > 0:
                fitted.insert(0, tool_result)
                budget -= tokens
            else:
                summary = self._compress_tool_result(tool_result)
                fitted.insert(0, summary)
                budget -= self.token_counter.count(str(summary))
        return fitted, budget

    def _fit_history(self, history: list, budget: int) -> list:
        """Fit history within budget, preserving recent turns."""
        fitted = []
        for msg in reversed(history):
            content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
            tokens = self.token_counter.count(content)
            if budget - tokens > 0:
                fitted.insert(0, msg)
                budget -= tokens
            else:
                # If this is the first message we can't fit, generate summary
                # of all remaining messages and compress
                remaining = history[: len(history) - len(fitted)]
                if remaining and not self._summary:
                    self.generate_summary(remaining)
                break
        return fitted

    @staticmethod
    def _compress_tool_result(result) -> str:
        """Deterministic compression (no LLM)."""
        name = getattr(result, "tool_name", "unknown")
        match name:
            case "read_file":
                path = getattr(result, "path", "")
                lines = getattr(result, "line_count", 0)
                return {"role": "tool", "content": f"[已读取 {path} ({lines}行)]"}
            case "run_command":
                exit_code = getattr(result, "exit_code", -1)
                cmd = getattr(result, "command", "")
                if exit_code == 0:
                    return {"role": "tool", "content": f"[命令成功: {cmd}]"}
                stderr = getattr(result, "stderr", "")
                return {"role": "tool", "content": f"[命令失败(exit={exit_code}): {stderr[:200]}]"}
            case "grep" | "glob":
                pattern = getattr(result, "pattern", "")
                count = getattr(result, "match_count", 0)
                return {"role": "tool", "content": f"[搜索 {pattern}: {count} 个结果]"}
            case _:
                summary = getattr(result, "summary", "")
                return {"role": "tool", "content": f"[{name}: {summary[:100]}]"}
