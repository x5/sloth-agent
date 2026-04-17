"""Unified configuration manager with multi-level JSON config merging."""

from dataclasses import dataclass, field
from pathlib import Path
import json
import os
from typing import Any

from dotenv import load_dotenv


@dataclass
class ProviderConfig:
    api_key_env: str = ""
    base_url: str = ""
    models: dict[str, str] = field(default_factory=dict)
    is_optional: bool = False


@dataclass
class LLMConfig:
    providers: dict[str, ProviderConfig] = field(default_factory=dict)
    default_provider: str = "deepseek"


@dataclass
class AgentConfig:
    name: str = "sloth-agent"
    workspace: str = "./workspace"
    timezone: str = "Asia/Shanghai"


@dataclass
class SecurityConfig:
    sandbox_enabled: bool = True
    path_whitelist: list[str] = field(
        default_factory=lambda: ["./workspace/**", "./src/**", "./tests/**"]
    )
    command_denylist: list[str] = field(default_factory=lambda: ["rm -rf /", "dd", "mkfs"])


@dataclass
class SkillsConfig:
    global_dir: str = "~/.sloth-agent/skills"
    local_dir: str = ".sloth/local_skills"


@dataclass
class ObservabilityConfig:
    log_level: str = "INFO"
    log_file: str = "~/.sloth-agent/logs/sloth.log"


@dataclass
class SlothConfig:
    llm: LLMConfig = field(default_factory=LLMConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    execution: dict[str, Any] = field(default_factory=dict)
    chat: dict[str, Any] = field(default_factory=dict)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    skills: SkillsConfig = field(default_factory=SkillsConfig)
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)


class ConfigManager:
    """
    Load and merge multi-level config.json files.
    Supports user/project/local three levels, deep merge, local wins.
    Automatically loads .env files from project and global directories.
    """

    def __init__(
        self,
        project_dir: str | Path | None = None,
        user_config_dir: str | Path | None = None,
    ):
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()
        self._user_config_dir = (
            Path(user_config_dir) if user_config_dir else Path.home() / ".sloth-agent"
        )
        self._env_loaded = False

    def _ensure_env_loaded(self) -> None:
        """Load .env files from project and global directories."""
        if self._env_loaded:
            return
        # Load project .env first (higher priority)
        project_env = self.project_dir / ".env"
        if project_env.exists():
            load_dotenv(dotenv_path=project_env, override=True)
        # Load global .env as fallback
        global_env = self._user_config_dir / ".env"
        if global_env.exists():
            load_dotenv(dotenv_path=global_env, override=False)
        self._env_loaded = True

    @property
    def _user_config(self) -> Path:
        return self._user_config_dir / "config.json"

    @property
    def _project_config(self) -> Path:
        return self.project_dir / ".sloth" / "config.json"

    @property
    def _local_config(self) -> Path:
        return self.project_dir / ".sloth" / "config.local.json"

    @property
    def _global_config_example(self) -> Path:
        return Path.home() / ".sloth-agent" / "config.json.example"

    def load(self) -> SlothConfig:
        """Load and merge config from all three levels."""
        self._ensure_env_loaded()
        merged: dict[str, Any] = {}
        for cfg_path in [self._user_config, self._project_config, self._local_config]:
            if cfg_path.exists():
                data = json.loads(cfg_path.read_text(encoding="utf-8"))
                merged = self._deep_merge(merged, data)
        return self._from_dict(merged)

    def load_raw(self) -> dict[str, Any]:
        """Return the raw merged dict (for CLI display)."""
        merged: dict[str, Any] = {}
        for cfg_path in [self._user_config, self._project_config, self._local_config]:
            if cfg_path.exists():
                data = json.loads(cfg_path.read_text(encoding="utf-8"))
                merged = self._deep_merge(merged, data)
        return merged

    def load_scope(self, scope: str) -> dict[str, Any]:
        """Load config from a single scope level."""
        scope_map = {
            "user": self._user_config,
            "project": self._project_config,
            "local": self._local_config,
        }
        path = scope_map.get(scope)
        if path and path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}

    def _deep_merge(self, base: dict, override: dict) -> dict:
        result = base.copy()
        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _from_dict(self, data: dict) -> SlothConfig:
        llm_data = data.get("llm", {})
        providers = {}
        for name, prov in llm_data.get("providers", {}).items():
            providers[name] = ProviderConfig(**prov)
        llm = LLMConfig(
            providers=providers,
            default_provider=llm_data.get("default_provider", "deepseek"),
        )
        agent = AgentConfig(**data.get("agent", {}))
        security = SecurityConfig(**data.get("security", {}))
        skills = SkillsConfig(**data.get("skills", {}))
        observability = ObservabilityConfig(**data.get("observability", {}))
        return SlothConfig(
            llm=llm,
            agent=agent,
            execution=data.get("execution", {}),
            chat=data.get("chat", {}),
            security=security,
            skills=skills,
            observability=observability,
        )

    def get_api_key(self, provider: str) -> str | None:
        """Resolve the actual API key value for a given provider."""
        config = self.load()
        prov = config.llm.providers.get(provider)
        if not prov or not prov.api_key_env:
            return None
        return os.environ.get(prov.api_key_env)

    def get_required_env_vars(self) -> list[str]:
        """Return list of environment variable names that are required by config.
        Skips providers marked as optional."""
        config = self.load()
        vars_needed = []
        for name, prov in config.llm.providers.items():
            if prov.api_key_env and not getattr(prov, "is_optional", False):
                vars_needed.append(prov.api_key_env)
        return sorted(set(vars_needed))

    def check_env_vars(self) -> dict[str, bool]:
        """Check which required env vars are set. Returns {var_name: is_set}."""
        result = {}
        for var in self.get_required_env_vars():
            result[var] = var in os.environ and bool(os.environ.get(var))
        return result

    def save(self, data: dict[str, Any], scope: str = "local") -> Path:
        """Save config data to the specified scope level."""
        scope_map = {
            "user": self._user_config,
            "project": self._project_config,
            "local": self._local_config,
        }
        target = scope_map.get(scope)
        if not target:
            raise ValueError(f"Unknown scope: {scope}. Must be user, project, or local.")

        # Load existing data for this scope and merge
        existing = {}
        if target.exists():
            existing = json.loads(target.read_text(encoding="utf-8"))
        merged = self._deep_merge(existing, data)

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return target

    def validate(self) -> list[str]:
        """
        Validate the current merged config.
        Returns a list of error messages (empty = valid).
        """
        errors = []
        config = self.load()

        # Check LLM providers have required fields
        for name, prov in config.llm.providers.items():
            if not prov.base_url:
                errors.append(f"llm.providers.{name}.base_url is required")
            if not prov.api_key_env:
                errors.append(f"llm.providers.{name}.api_key_env is required")

        # Check agent config
        if not config.agent.workspace:
            errors.append("agent.workspace is required")
        if not config.agent.timezone:
            errors.append("agent.timezone is required")

        # Check security path_whitelist is not empty when sandbox enabled
        if config.security.sandbox_enabled and not config.security.path_whitelist:
            errors.append("security.path_whitelist cannot be empty when sandbox is enabled")

        return errors
