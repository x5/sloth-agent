"""LLM Provider config CRUD — Sloth global Settings."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import async_session
from ..models import LLMConfig

router = APIRouter(prefix="/api/settings/llm", tags=["settings-llm"])


class CreateLLMRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=50)
    model: str = Field(min_length=1, max_length=100)
    api_key: str = Field(min_length=1, max_length=200)
    base_url: str = Field(min_length=1, max_length=500)
    api_format: str = Field(default="openai", max_length=20)


class UpdateLLMRequest(BaseModel):
    provider: str | None = Field(default=None, max_length=50)
    model: str | None = Field(default=None, max_length=100)
    api_key: str | None = Field(default=None, max_length=200)
    base_url: str | None = Field(default=None, max_length=500)
    api_format: str | None = Field(default=None, max_length=20)


class LLMResponse(BaseModel):
    id: str
    provider: str
    model: str
    api_key: str
    base_url: str
    api_format: str
    is_default: bool
    created_at: str

    model_config = {"from_attributes": True}

    @field_validator("created_at", mode="before")
    @classmethod
    def serialize_created_at(cls, v: object) -> str:
        if isinstance(v, datetime):
            return v.isoformat()
        return v


def _mask_key(key: str) -> str:
    if len(key) <= 8:
        return "****"
    return key[:4] + "****" + key[-4:]


async def get_db():
    async with async_session() as session:
        yield session


@router.get("", response_model=list[LLMResponse])
async def list_llm_configs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LLMConfig).order_by(LLMConfig.is_default.desc(), LLMConfig.created_at.asc()))
    configs = result.scalars().all()
    for c in configs:
        c.api_key = _mask_key(c.api_key)
    return configs


@router.post("", response_model=LLMResponse, status_code=201)
async def create_llm_config(req: CreateLLMRequest, db: AsyncSession = Depends(get_db)):
    # Auto-set as default if first LLM
    result = await db.execute(select(LLMConfig).limit(1))
    is_first = result.scalar_one_or_none() is None

    config = LLMConfig(
        provider=req.provider,
        model=req.model,
        api_key=req.api_key,
        base_url=req.base_url,
        api_format=req.api_format,
        is_default=is_first,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    config.api_key = _mask_key(config.api_key)
    return config


@router.patch("/{config_id}", response_model=LLMResponse)
async def update_llm_config(config_id: str, req: UpdateLLMRequest, db: AsyncSession = Depends(get_db)):
    config = await db.get(LLMConfig, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="LLM config not found")

    update_data = req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(config, key, value)

    await db.commit()
    await db.refresh(config)
    config.api_key = _mask_key(config.api_key)
    return config


@router.delete("/{config_id}", status_code=204)
async def delete_llm_config(config_id: str, db: AsyncSession = Depends(get_db)):
    config = await db.get(LLMConfig, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="LLM config not found")
    if config.is_default:
        raise HTTPException(status_code=400, detail="Cannot delete the default LLM provider")
    await db.delete(config)
    await db.commit()


@router.put("/{config_id}/default", response_model=LLMResponse)
async def set_default_llm(config_id: str, db: AsyncSession = Depends(get_db)):
    config = await db.get(LLMConfig, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="LLM config not found")

    await db.execute(update(LLMConfig).values(is_default=False))
    config.is_default = True
    await db.commit()
    await db.refresh(config)
    config.api_key = _mask_key(config.api_key)
    return config
