"""Context window management for Builder Agent."""


class ContextWindowManager:
    """Manage agent context window with precise token counting."""

    def __init__(self, max_tokens: int = 128_000, output_reserve: int = 15_000):
        self.max_tokens = max_tokens
        self.output_reserve = output_reserve
        self.available = max_tokens - output_reserve

    def build_messages(
        self, system: str, history: list, tool_results: list, user_msg: str
    ) -> list:
        """Build message list within token budget."""
        budget = self.available
        sys_tokens = self._count_tokens(system)
        budget -= sys_tokens
        user_tokens = self._count_tokens(user_msg)
        budget -= user_tokens

        # Fit tool results (most recent first)
        fitted_tools, budget = self._fit_tool_results(tool_results, budget)
        # Fit history (most recent first)
        fitted_history = self._fit_history(history, budget)

        return [{"role": "system", "content": system}] + fitted_tools + fitted_history + [{"role": "user", "content": user_msg}]

    def _fit_tool_results(self, tool_results: list, budget: int) -> tuple[list, int]:
        fitted = []
        for tool_result in reversed(tool_results):
            tokens = self._count_tokens(tool_result)
            if budget - tokens > 0:
                fitted.insert(0, tool_result)
                budget -= tokens
            else:
                summary = self._compress_tool_result(tool_result)
                fitted.insert(0, summary)
                budget -= self._count_tokens(summary)
        return fitted, budget

    def _fit_history(self, history: list, budget: int) -> list:
        fitted = []
        for msg in reversed(history):
            content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
            tokens = self._count_tokens(content)
            if budget - tokens > 0:
                fitted.insert(0, msg)
                budget -= tokens
            else:
                break
        return fitted

    @staticmethod
    def _count_tokens(text: str) -> int:
        """Rough token estimate: ~4 chars per token."""
        try:
            import tiktoken
            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except ImportError:
            return len(text) // 4

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
