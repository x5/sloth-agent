"""ContextEngine — extended context management for agent conversations.

Extends ContextWindowManager with reply-chain protection,
three-phase context building, and diagnostics output.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sloth_agent.core.context_window import ContextWindowManager


@dataclass
class ContextPolicy:
    """Configuration for context building."""

    model: str = "gpt-4"
    max_tokens: int = 128_000
    output_reserve: int = 15_000
    max_history_turns: int = 20
    protect_threads: bool = True
    mode: str = "brainstorm"  # "brainstorm" | "chat" | "autonomous"


@dataclass
class ContextResult:
    """Three-phase context output."""

    system_prompt: str = ""
    model_visible_context: list[dict] = field(default_factory=list)
    runtime_only_context: list[dict] = field(default_factory=list)
    diagnostics: dict = field(default_factory=dict)


class ContextEngine(ContextWindowManager):
    """Extended context manager with thread protection and diagnostics.

    Extends ContextWindowManager (token budget, summary compression).
    Adds: reply-chain protection, three-phase build, diagnostics.
    """

    def __init__(self, policy: ContextPolicy | None = None):
        policy = policy or ContextPolicy()
        super().__init__(
            model=policy.model,
            max_tokens=policy.max_tokens,
            output_reserve=policy.output_reserve,
            max_history_turns=policy.max_history_turns,
        )
        self.policy = policy

    def build(
        self,
        system_prompt: str,
        messages: list[dict],
    ) -> ContextResult:
        """Build context: system prompt + user messages + tool results.

        Returns ContextResult with:
        - model_visible_context: what the LLM sees
        - runtime_only_context: diagnostic info not sent to LLM
        - diagnostics: token stats
        """
        working = list(messages)
        if self.policy.protect_threads:
            working = self._protect_reply_chains(working)

        history = [
            m
            for m in working
            if m.get("role") in ("user", "assistant", "agent", "human")
        ]
        tool_msgs = [m for m in working if m.get("role") == "tool"]

        user_msg = ""
        for m in reversed(history):
            if m.get("role") in ("user", "human"):
                user_msg = m.get("content", "")
                break

        fitted = self.build_messages(system_prompt, history, tool_msgs, user_msg)

        total_tokens = self.token_counter.count_messages(fitted)
        original_tokens = self.token_counter.count_messages(working)

        diagnostics = {
            "token_utilization": round(total_tokens / max(self.available, 1) * 100, 1),
            "total_tokens": total_tokens,
            "available_tokens": self.available,
            "compression_ratio": round(
                1 - total_tokens / max(original_tokens, 1), 3
            ),
            "truncation_ratio": round(1 - len(fitted) / max(len(working), 1), 3),
            "mode": self.policy.mode,
        }

        return ContextResult(
            system_prompt=system_prompt,
            model_visible_context=fitted,
            runtime_only_context=[],
            diagnostics=diagnostics,
        )

    def _protect_reply_chains(self, messages: list[dict]) -> list[dict]:
        """Ensure ancestor chains of reply messages are not truncated.

        Messages with parent_message_id indicate reply chains. We trace
        back and protect all ancestors by moving them to the end, so
        the parent's _fit_history doesn't cut them early.
        """
        id_map: dict[str, dict] = {}
        for m in messages:
            mid = m.get("id") or m.get("message_id")
            if mid:
                id_map[mid] = m

        protected_ids: set[str] = set()
        for m in messages:
            parent = m.get("parent_message_id")
            if parent:
                current = parent
                while current and current in id_map:
                    protected_ids.add(current)
                    current = id_map[current].get("parent_message_id") or ""

        regular = [
            m
            for m in messages
            if (m.get("id") or m.get("message_id")) not in protected_ids
        ]
        protected = [
            m
            for m in messages
            if (m.get("id") or m.get("message_id")) in protected_ids
        ]
        return regular + protected
