"""LLM service — DB config lookups and adapter creation."""

from typing import AsyncGenerator

from sqlalchemy import select

from ..database import async_session
from ..models import LLMConfig
from ..shared.llm_adapter import LLMAdapter

import os


async def _get_default_llm_config() -> LLMConfig | None:
    async with async_session() as db:
        result = await db.execute(
            select(LLMConfig).where(LLMConfig.is_default == True)
        )
        return result.scalar_one_or_none()


async def _get_llm_config_for_model(model: str) -> LLMConfig | None:
    async with async_session() as db:
        result = await db.execute(
            select(LLMConfig).where(LLMConfig.model == model)
        )
        return result.scalar_one_or_none()


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
    """LLM call wrapper — delegates to core providers via LLMAdapter."""

    async def get_adapter(self, model: str) -> LLMAdapter:
        config = await _get_llm_config_for_model(model) or await _get_default_llm_config()
        if not config:
            raise ValueError(f"No LLM config found for model: {model}")
        return LLMAdapter(config)

    async def chat(self, model: str, messages: list[dict]) -> str:
        adapter = await self.get_adapter(model)
        return await adapter.chat(messages)

    async def chat_stream(
        self, model: str, messages: list[dict]
    ) -> AsyncGenerator[str, None]:
        adapter = await self.get_adapter(model)
        async for token in adapter.chat_stream(messages):
            yield token
