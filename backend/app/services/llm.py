import json
from typing import AsyncGenerator

import httpx
from sqlalchemy import select

from ..database import async_session
from ..models import LLMConfig


async def _get_default_llm_config() -> LLMConfig | None:
    async with async_session() as db:
        result = await db.execute(select(LLMConfig).where(LLMConfig.is_default == True))
        return result.scalar_one_or_none()


async def _get_llm_config_for_model(model: str) -> LLMConfig | None:
    async with async_session() as db:
        result = await db.execute(select(LLMConfig).where(LLMConfig.model == model))
        return result.scalar_one_or_none()


import os


async def seed_default_llm():
    """Ensure there is a default LLM config (DeepSeek sample).

    Reads api_key from env SLOTH_DEEPSEEK_API_KEY if set, otherwise uses a placeholder.
    """
    async with async_session() as db:
        result = await db.execute(select(LLMConfig).limit(1))
        if result.scalar_one_or_none():
            return
        api_key = os.getenv("SLOTH_DEEPSEEK_API_KEY", "sk-your-deepseek-api-key")
        default_llm = LLMConfig(
            provider="DeepSeek",
            model="deepseek-v4-pro",
            api_key=api_key,
            base_url="https://api.deepseek.com/v1",
            api_format="openai",
            is_default=True,
        )
        db.add(default_llm)
        await db.commit()


class LLMService:
    """LLM call wrapper with OpenAI/Anthropic format routing."""

    async def chat(self, model: str, messages: list[dict]) -> str:
        config = await _get_llm_config_for_model(model) or await _get_default_llm_config()
        if not config:
            raise ValueError(f"No LLM config found for model: {model}")

        if config.api_format == "anthropic":
            return await self._chat_anthropic(config, messages)
        return await self._chat_openai(config, messages)

    async def chat_stream(self, model: str, messages: list[dict]) -> AsyncGenerator[str, None]:
        config = await _get_llm_config_for_model(model) or await _get_default_llm_config()
        if not config:
            raise ValueError(f"No LLM config found for model: {model}")

        if config.api_format == "anthropic":
            async for token in self._stream_anthropic(config, messages):
                yield token
        else:
            async for token in self._stream_openai(config, messages):
                yield token

    async def _chat_openai(self, config: LLMConfig, messages: list[dict]) -> str:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{config.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {config.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": config.model,
                    "messages": messages,
                    "stream": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def _stream_openai(self, config: LLMConfig, messages: list[dict]) -> AsyncGenerator[str, None]:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{config.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {config.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": config.model,
                    "messages": messages,
                    "stream": True,
                },
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue

    async def _chat_anthropic(self, config: LLMConfig, messages: list[dict]) -> str:
        system_msgs = [m for m in messages if m["role"] == "system"]
        chat_msgs = [m for m in messages if m["role"] != "system"]

        body = {
            "model": config.model,
            "max_tokens": 4096,
            "messages": chat_msgs,
        }
        if system_msgs:
            body["system"] = "\n".join(m["content"] for m in system_msgs)

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{config.base_url}/messages",
                headers={
                    "x-api-key": config.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["content"][0]["text"]

    async def _stream_anthropic(self, config: LLMConfig, messages: list[dict]) -> AsyncGenerator[str, None]:
        system_msgs = [m for m in messages if m["role"] == "system"]
        chat_msgs = [m for m in messages if m["role"] != "system"]

        body = {
            "model": config.model,
            "max_tokens": 4096,
            "messages": chat_msgs,
            "stream": True,
        }
        if system_msgs:
            body["system"] = "\n".join(m["content"] for m in system_msgs)

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{config.base_url}/messages",
                headers={
                    "x-api-key": config.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json=body,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        try:
                            event = json.loads(data_str)
                            if event.get("type") == "content_block_delta":
                                text = event.get("delta", {}).get("text", "")
                                if text:
                                    yield text
                        except json.JSONDecodeError:
                            continue
