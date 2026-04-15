"""Configuration loader for sloth-agent framework."""

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field


class WatchdogConfig(BaseModel):
    heartbeat_interval: int = 180
    max_missing_heartbeats: int = 3
    restart_delay: int = 60


class CheckpointConfig(BaseModel):
    interval: int = 1
    storage: str = "./checkpoints/"


class TDDConfig(BaseModel):
    enforced: bool = True
    coverage_threshold: int = 80
    ui_test_enabled: bool = True


class VerificationConfig(BaseModel):
    enabled: bool = True
    retry: int = 3
    file_exists_check: bool = True
    build_check: bool = True
    test_check: bool = True


class ApprovalChannel(BaseModel):
    type: str
    webhook: str | None = None
    smtp: str | None = None
    port: int = 587
    from_addr: str | None = None
    to: list[str] = Field(default_factory=list)


class ApprovalConfig(BaseModel):
    mode: str = "plan_level"
    async_channels: list[ApprovalChannel] = Field(default_factory=list)
    timeout_hours: int = 2


class MemoryConfig(BaseModel):
    short_term_retention_days: int = 7
    vector_db_path: str = "./memory/context/"
    sqlite_path: str = "./memory/agent.db"


class ChatConfig(BaseModel):
    max_context_turns: int = 20
    auto_approve_risk_level: int = 2
    stream_responses: bool = True
    prompt_prefix: str = "sloth> "


class AgentConfig(BaseModel):
    name: str = "sloth-agent"
    workspace: str = "./workspace"
    timezone: str = "Asia/Shanghai"


class ExecutionConfig(BaseModel):
    auto_execute_hours: str = "09:00-18:00"
    require_approval_hours: str = "18:00-09:00"


class Config(BaseModel):
    agent: AgentConfig = Field(default_factory=AgentConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    watchdog: WatchdogConfig = Field(default_factory=WatchdogConfig)
    checkpoint: CheckpointConfig = Field(default_factory=CheckpointConfig)
    tdd: TDDConfig = Field(default_factory=TDDConfig)
    verification: VerificationConfig = Field(default_factory=VerificationConfig)
    approval: ApprovalConfig = Field(default_factory=ApprovalConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    chat: ChatConfig = Field(default_factory=ChatConfig)


def load_config(config_path: str | Path | None = None) -> Config:
    """Load configuration from YAML file and environment variables."""
    load_dotenv()

    if config_path is None:
        # Look for config in configs/
        config_path = Path(__file__).parent.parent.parent / "configs" / "agent.yaml"

    config_path = Path(config_path)

    if config_path.exists():
        with open(config_path) as f:
            data = yaml.safe_load(f)
    else:
        data = {}

    # Expand environment variables in string values
    data = _expand_env_vars(data)

    return Config(**data)


def _expand_env_vars(data: Any) -> Any:
    """Recursively expand environment variables in config data."""
    if isinstance(data, dict):
        return {k: _expand_env_vars(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_expand_env_vars(item) for item in data]
    elif isinstance(data, str):
        return os.path.expandvars(data)
    return data
