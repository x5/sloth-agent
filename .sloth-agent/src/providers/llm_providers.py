"""LLM Providers - Multi-model provider support for Chinese LLMs."""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, AsyncIterator

import httpx
import yaml

logger = logging.getLogger("llm")


class LLMMessage:
    """Represents a message in a conversation."""

    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}


class LLMResponse:
    """Represents a response from LLM."""

    def __init__(self, content: str, model: str, usage: dict | None = None):
        self.content = content
        self.model = model
        self.usage = usage or {}


class BaseLLMProvider(ABC):
    """Base class for LLM providers."""

    name: str = ""

    @abstractmethod
    async def chat(
        self, messages: list[LLMMessage], model: str | None = None, **kwargs
    ) -> LLMResponse:
        """Send a chat request."""
        pass

    @abstractmethod
    async def chat_stream(
        self, messages: list[LLMMessage], model: str | None = None, **kwargs
    ) -> AsyncIterator[str]:
        """Send a streaming chat request."""
        pass


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek API provider."""

    name = "deepseek"

    def __init__(self, api_key: str, api_base: str = "https://api.deepseek.com/v1"):
        self.api_key = api_key
        self.api_base = api_base

    async def chat(
        self, messages: list[LLMMessage], model: str = "deepseek-chat", **kwargs
    ) -> LLMResponse:
        """Send chat request to DeepSeek."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": model,
                    "messages": [m.to_dict() for m in messages],
                    **kwargs,
                },
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()

            return LLMResponse(
                content=data["choices"][0]["message"]["content"],
                model=model,
                usage=data.get("usage", {}),
            )

    async def chat_stream(
        self, messages: list[LLMMessage], model: str = "deepseek-chat", **kwargs
    ) -> AsyncIterator[str]:
        """Send streaming chat request to DeepSeek."""
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.api_base}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": model,
                    "messages": [m.to_dict() for m in messages],
                    "stream": True,
                    **kwargs,
                },
                timeout=60,
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        import json
                        chunk = json.loads(data)
                        content = chunk["choices"][0]["delta"].get("content", "")
                        if content:
                            yield content


class QwenProvider(BaseLLMProvider):
    """Qwen (Aliyun) API provider."""

    name = "qwen"

    def __init__(self, api_key: str, api_base: str = "https://dashscope.aliyuncs.com/api/v1"):
        self.api_key = api_key
        self.api_base = api_base

    async def chat(
        self, messages: list[LLMMessage], model: str = "qwen-turbo", **kwargs
    ) -> LLMResponse:
        """Send chat request to Qwen."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base}/services/aicc/chat",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": model,
                    "input": {"messages": [{"role": m.role, "content": m.content} for m in messages]},
                    "parameters": kwargs,
                },
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()

            return LLMResponse(
                content=data["output"]["choices"][0]["message"]["content"],
                model=model,
                usage=data.get("usage", {}),
            )

    async def chat_stream(self, messages, model: str = "qwen-turbo", **kwargs) -> AsyncIterator[str]:
        """Streaming not implemented for Qwen yet."""
        response = await self.chat(messages, model, **kwargs)
        yield response.content


class KimiProvider(BaseLLMProvider):
    """Kimi (Moonshot) API provider."""

    name = "kimi"

    def __init__(self, api_key: str, api_base: str = "https://api.moonshot.cn/v1"):
        self.api_key = api_key
        self.api_base = api_base

    async def chat(
        self, messages: list[LLMMessage], model: str = "moonshot-v1-8k", **kwargs
    ) -> LLMResponse:
        """Send chat request to Kimi."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": model,
                    "messages": [m.to_dict() for m in messages],
                    **kwargs,
                },
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()

            return LLMResponse(
                content=data["choices"][0]["message"]["content"],
                model=model,
                usage=data.get("usage", {}),
            )

    async def chat_stream(self, messages, model: str = "moonshot-v1-8k", **kwargs) -> AsyncIterator[str]:
        """Send streaming chat request to Kimi."""
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.api_base}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": model,
                    "messages": [m.to_dict() for m in messages],
                    "stream": True,
                    **kwargs,
                },
                timeout=60,
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        import json
                        chunk = json.loads(data)
                        content = chunk["choices"][0]["delta"].get("content", "")
                        if content:
                            yield content


class MiniMaxProvider(BaseLLMProvider):
    """MiniMax API provider."""

    name = "minimax"

    def __init__(self, api_key: str, api_base: str = "https://api.minimax.chat/v1"):
        self.api_key = api_key
        self.api_base = api_base

    async def chat(
        self, messages: list[LLMMessage], model: str = "MiniMax-Text-01", **kwargs
    ) -> LLMResponse:
        """Send chat request to MiniMax."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base}/text/chatcompletion_v2",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": model,
                    "messages": [m.to_dict() for m in messages],
                    **kwargs,
                },
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()

            return LLMResponse(
                content=data["choices"][0]["message"]["content"],
                model=model,
                usage=data.get("usage", {}),
            )

    async def chat_stream(self, messages, model: str = "MiniMax-Text-01", **kwargs) -> AsyncIterator[str]:
        """Streaming not implemented for MiniMax yet."""
        response = await self.chat(messages, model, **kwargs)
        yield response.content


class GLMProvider(BaseLLMProvider):
    """GLM (Zhipu) API provider."""

    name = "glm"

    def __init__(self, api_key: str, api_base: str = "https://open.bigmodel.cn/api/paas/v4"):
        self.api_key = api_key
        self.api_base = api_base

    async def chat(
        self, messages: list[LLMMessage], model: str = "glm-4", **kwargs
    ) -> LLMResponse:
        """Send chat request to GLM."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": model,
                    "messages": [m.to_dict() for m in messages],
                    **kwargs,
                },
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()

            return LLMResponse(
                content=data["choices"][0]["message"]["content"],
                model=model,
                usage=data.get("usage", {}),
            )

    async def chat_stream(self, messages, model: str = "glm-4", **kwargs) -> AsyncIterator[str]:
        """Send streaming chat request to GLM."""
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.api_base}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": model,
                    "messages": [m.to_dict() for m in messages],
                    "stream": True,
                    **kwargs,
                },
                timeout=60,
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        import json
                        chunk = json.loads(data)
                        content = chunk["choices"][0]["delta"].get("content", "")
                        if content:
                            yield content


class LLMProviderManager:
    """Manages multiple LLM providers with fallback support."""

    def __init__(self, config_path: str | Path | None = None):
        if config_path is None:
            # Look for config in .sloth-agent/configs/
            config_path = Path(__file__).parent.parent.parent / "configs" / "llm_providers.yaml"

        self.config = self._load_config(config_path)
        self.providers: dict[str, BaseLLMProvider] = {}
        self._init_providers()

    def _load_config(self, config_path: Path) -> dict:
        """Load provider configuration."""
        if not Path(config_path).exists():
            return {"providers": [], "fallback": {"enabled": False}}

        with open(config_path) as f:
            import os
            content = os.path.expandvars(f.read())
            return yaml.safe_load(content)

    def _init_providers(self):
        """Initialize all configured providers."""
        import os

        provider_map = {
            "deepseek": DeepSeekProvider,
            "qwen": QwenProvider,
            "kimi": KimiProvider,
            "minimax": MiniMaxProvider,
            "glm": GLMProvider,
        }

        for provider_config in self.config.get("providers", []):
            name = provider_config["name"]
            if name in provider_map and provider_config.get("enabled", True):
                # Extract env var name from ${VAR_NAME}
                env_var = provider_config.get("api_key", "").replace("${", "").replace("}", "")
                api_key = os.environ.get(env_var, "")
                provider_class = provider_map[name]
                self.providers[name] = provider_class(
                    api_key=api_key,
                    api_base=provider_config["api_base"],
                )
                logger.info(f"Initialized provider: {name}")

    async def chat(
        self,
        messages: list[LLMMessage],
        provider: str | None = None,
        model: str | None = None,
        **kwargs
    ) -> LLMResponse:
        """Send chat request with automatic fallback."""
        if provider is None:
            provider = self.config.get("default_provider", "deepseek")

        fallback_order = self.config.get("fallback", {}).get("order", [provider])

        last_error = None
        for p in fallback_order:
            if p not in self.providers:
                continue

            try:
                return await self.providers[p].chat(messages, model, **kwargs)
            except Exception as e:
                logger.warning(f"Provider {p} failed: {e}")
                last_error = e
                continue

        raise RuntimeError(f"All providers failed. Last error: {last_error}")

    async def chat_stream(
        self,
        messages: list[LLMMessage],
        provider: str | None = None,
        model: str | None = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Send streaming chat request."""
        if provider is None:
            provider = self.config.get("default_provider", "deepseek")

        if provider in self.providers:
            async for chunk in self.providers[provider].chat_stream(messages, model, **kwargs):
                yield chunk
        else:
            raise ValueError(f"Unknown provider: {provider}")
