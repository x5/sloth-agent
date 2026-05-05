"""LLMAdapter — wraps core BaseLLMProvider instances fed by DB LLMConfig."""

import json
from typing import Any, AsyncIterator

from sloth_agent.providers.llm_providers import (
    BaseLLMProvider,
    DeepSeekProvider,
    GLMProvider,
    KimiProvider,
    LLMMessage,
    MiniMaxProvider,
    QwenProvider,
)

from ..models import LLMConfig

_PROVIDER_MAP: dict[str, type[BaseLLMProvider]] = {
    "deepseek": DeepSeekProvider,
    "qwen": QwenProvider,
    "kimi": KimiProvider,
    "minimax": MiniMaxProvider,
    "glm": GLMProvider,
}


def _build_provider(config: LLMConfig) -> BaseLLMProvider:
    provider_cls = _PROVIDER_MAP.get(config.provider.lower())
    if not provider_cls:
        raise ValueError(f"Unsupported provider: {config.provider}")
    return provider_cls(api_key=config.api_key, api_base=config.base_url)


def _to_llm_messages(messages: list[dict]) -> list[LLMMessage]:
    return [LLMMessage(role=m["role"], content=m.get("content", "")) for m in messages]


class LLMAdapter:
    """Wraps core BaseLLMProvider, fed by DB LLMConfig.

    Provides a single unified async interface for the Desktop backend.
    """

    def __init__(self, config: LLMConfig):
        self._config = config
        self._provider = _build_provider(config)

    @property
    def model(self) -> str:
        return self._config.model

    async def chat(self, messages: list[dict]) -> str:
        """Non-streaming chat. Returns full response text."""
        llm_msgs = _to_llm_messages(messages)
        resp = await self._provider.chat(llm_msgs, model=self._config.model)
        return resp.content

    async def chat_stream(self, messages: list[dict]) -> AsyncIterator[str]:
        """Streaming chat. Yields text tokens."""
        llm_msgs = _to_llm_messages(messages)
        async for token in self._provider.chat_stream(
            llm_msgs, model=self._config.model
        ):
            yield token

    async def chat_with_tools(
        self, messages: list[dict], tools: list[dict] | None = None
    ) -> dict[str, Any]:
        """Non-streaming chat with optional tools. Returns dict with content and tool_calls.

        Returns:
            {"content": str, "tool_calls": [{"name": str, "arguments": dict}, ...]}
        """
        llm_msgs = _to_llm_messages(messages)
        kwargs = {}
        if tools:
            kwargs["tools"] = tools

        resp = await self._provider.chat(llm_msgs, model=self._config.model, **kwargs)

        # Try to extract tool_calls from the underlying response
        tool_calls: list[dict] = []
        content = resp.content

        # If the provider returned usage data with tool_calls, extract them
        if resp.usage and "tool_calls" in resp.usage:
            tool_calls = resp.usage["tool_calls"]

        return {"content": content, "tool_calls": tool_calls}
