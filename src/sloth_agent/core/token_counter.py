"""Token counter — estimate token counts for text.

Supports tiktoken (accurate) or a simple character-based fallback.
"""

from __future__ import annotations


class TokenCounter:
    """Count tokens in text.

    Uses tiktoken if available, falls back to character-ratio estimation.
    """

    def __init__(self, model: str = "cl100k_base"):
        self.model = model
        self._encoder = None
        self._try_init()

    def _try_init(self) -> None:
        """Try to load tiktoken encoder."""
        try:
            import tiktoken
            self._encoder = tiktoken.get_encoding(self.model)
        except ImportError:
            self._encoder = None

    def count(self, text: str) -> int:
        """Return token count for the given text."""
        if self._encoder is not None:
            return len(self._encoder.encode(text))
        return self._estimate(text)

    def count_messages(self, messages: list[dict]) -> int:
        """Count tokens for a list of OpenAI-format messages.

        Adds ~4 tokens per message for formatting overhead.
        """
        total = 0
        for msg in messages:
            total += self.count(msg.get("content", ""))
            total += 4  # per-message overhead
        return total

    @staticmethod
    def _estimate(text: str) -> int:
        """Simple character-based estimate (~4 chars/token)."""
        if not text:
            return 0
        return max(1, len(text) // 4)
