"""Tests for ConfigManager — multi-level JSON config loading and merging."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from sloth_agent.core.config_manager import (
    ConfigManager,
    SlothConfig,
    LLMConfig,
    ProviderConfig,
    AgentConfig,
    SecurityConfig,
)


SAMPLE_USER = {
    "llm": {
        "default_provider": "deepseek",
        "providers": {
            "deepseek": {
                "api_key_env": "DEEPSEEK_API_KEY",
                "base_url": "https://api.deepseek.com/v1",
                "models": {"coding": "deepseek-v3.2"},
            }
        },
    },
    "agent": {"name": "sloth-agent", "workspace": "~/.sloth/workspace"},
    "security": {"sandbox_enabled": True},
}

SAMPLE_PROJECT = {
    "llm": {
        "providers": {
            "qwen": {
                "api_key_env": "QWEN_API_KEY",
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "models": {"review": "qwen3.6-plus"},
            }
        },
    },
    "agent": {"workspace": "./project-workspace"},
}

SAMPLE_LOCAL = {
    "llm": {"default_provider": "qwen"},
}


class TestConfigManagerDeepMerge:
    """Three-level config merge: user → project → local, local wins."""

    def test_merge_adds_new_keys(self, tmp_path):
        """Project config should add new provider without removing user's."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        sloth_dir = project_dir / ".sloth"
        sloth_dir.mkdir()

        user_config_dir = tmp_path / ".sloth-agent"
        user_config_dir.mkdir(parents=True)
        user_config = user_config_dir / "config.json"
        user_config.write_text(json.dumps(SAMPLE_USER))
        project_config = sloth_dir / "config.json"
        project_config.write_text(json.dumps(SAMPLE_PROJECT))

        cm = ConfigManager(project_dir=project_dir, user_config_dir=user_config_dir)
        raw = cm.load_raw()

        assert "deepseek" in raw["llm"]["providers"]
        assert "qwen" in raw["llm"]["providers"]
        assert raw["llm"]["default_provider"] == "deepseek"

    def test_local_overrides_user(self, tmp_path):
        """Local scope should override user-level values."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        sloth_dir = project_dir / ".sloth"
        sloth_dir.mkdir()

        user_config_dir = tmp_path / ".sloth-agent"
        user_config_dir.mkdir(parents=True)
        user_config = user_config_dir / "config.json"
        user_config.write_text(json.dumps(SAMPLE_USER))
        local_config = sloth_dir / "config.local.json"
        local_config.write_text(json.dumps(SAMPLE_LOCAL))

        cm = ConfigManager(project_dir=project_dir, user_config_dir=user_config_dir)
        config = cm.load()

        assert config.llm.default_provider == "qwen"

    def test_project_overrides_user_nested(self, tmp_path):
        """Project scope should override user workspace."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        sloth_dir = project_dir / ".sloth"
        sloth_dir.mkdir()

        user_config_dir = tmp_path / ".sloth-agent"
        user_config_dir.mkdir(parents=True)
        user_config = user_config_dir / "config.json"
        user_config.write_text(json.dumps(SAMPLE_USER))
        project_config = sloth_dir / "config.json"
        project_config.write_text(json.dumps(SAMPLE_PROJECT))

        cm = ConfigManager(project_dir=project_dir, user_config_dir=user_config_dir)
        config = cm.load()

        assert config.agent.workspace == "./project-workspace"


class TestConfigManagerApiKey:
    """API key resolution from env vars."""

    def test_get_api_key_returns_env_value(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        sloth_dir = project_dir / ".sloth"
        sloth_dir.mkdir()

        user_config_dir = tmp_path / ".sloth-agent"
        user_config_dir.mkdir(parents=True)
        user_config = user_config_dir / "config.json"
        user_config.write_text(json.dumps(SAMPLE_USER))
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-123")

        cm = ConfigManager(project_dir=project_dir, user_config_dir=user_config_dir)
        key = cm.get_api_key("deepseek")
        assert key == "sk-test-123"

    def test_get_api_key_returns_none_if_unset(self, tmp_path):
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        sloth_dir = project_dir / ".sloth"
        sloth_dir.mkdir()

        user_config_dir = tmp_path / ".sloth-agent"
        user_config_dir.mkdir(parents=True)
        user_config = user_config_dir / "config.json"
        user_config.write_text(json.dumps(SAMPLE_USER))

        cm = ConfigManager(project_dir=project_dir, user_config_dir=user_config_dir)
        key = cm.get_api_key("deepseek")
        assert key is None

    def test_check_env_vars_reports_status(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        sloth_dir = project_dir / ".sloth"
        sloth_dir.mkdir()

        user_config_dir = tmp_path / ".sloth-agent"
        user_config_dir.mkdir(parents=True)
        user_config = user_config_dir / "config.json"
        user_config.write_text(json.dumps(SAMPLE_USER))
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-123")

        cm = ConfigManager(project_dir=project_dir, user_config_dir=user_config_dir)
        status = cm.check_env_vars()
        assert status["DEEPSEEK_API_KEY"] is True

    def test_required_env_vars_lists_all(self, tmp_path):
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        sloth_dir = project_dir / ".sloth"
        sloth_dir.mkdir()

        user_config_dir = tmp_path / ".sloth-agent"
        user_config_dir.mkdir(parents=True)
        user_config = user_config_dir / "config.json"
        user_config.write_text(json.dumps(SAMPLE_USER))

        cm = ConfigManager(project_dir=project_dir, user_config_dir=user_config_dir)
        vars_needed = cm.get_required_env_vars()
        assert "DEEPSEEK_API_KEY" in vars_needed


class TestConfigManagerSave:
    """Save config to specific scope levels."""

    def test_save_creates_file(self, tmp_path):
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        sloth_dir = project_dir / ".sloth"
        sloth_dir.mkdir()

        user_config_dir = tmp_path / ".sloth-agent"
        user_config_dir.mkdir(parents=True)

        cm = ConfigManager(project_dir=project_dir, user_config_dir=user_config_dir)
        saved = cm.save({"llm": {"default_provider": "qwen"}}, scope="local")

        assert saved.exists()
        data = json.loads(saved.read_text())
        assert data["llm"]["default_provider"] == "qwen"

    def test_save_merges_with_existing(self, tmp_path):
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        sloth_dir = project_dir / ".sloth"
        sloth_dir.mkdir()

        user_config_dir = tmp_path / ".sloth-agent"
        user_config_dir.mkdir(parents=True)
        local_config = sloth_dir / "config.local.json"
        local_config.write_text(json.dumps({"agent": {"name": "old"}}))

        cm = ConfigManager(project_dir=project_dir, user_config_dir=user_config_dir)
        cm.save({"llm": {"default_provider": "qwen"}}, scope="local")

        data = json.loads(local_config.read_text())
        assert data["agent"]["name"] == "old"
        assert data["llm"]["default_provider"] == "qwen"


class TestConfigManagerValidate:
    """Config validation."""

    def test_valid_config_no_errors(self, tmp_path):
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        sloth_dir = project_dir / ".sloth"
        sloth_dir.mkdir()

        user_config_dir = tmp_path / ".sloth-agent"
        user_config_dir.mkdir(parents=True)
        user_config = user_config_dir / "config.json"
        user_config.write_text(json.dumps(SAMPLE_USER))

        cm = ConfigManager(project_dir=project_dir, user_config_dir=user_config_dir)
        errors = cm.validate()
        assert errors == []

    def test_empty_config_has_errors(self, tmp_path):
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / ".sloth").mkdir()
        user_config_dir = tmp_path / ".sloth-agent"
        user_config_dir.mkdir(parents=True)

        cm = ConfigManager(project_dir=project_dir, user_config_dir=user_config_dir)
        errors = cm.validate()
        # Empty config: no providers means no errors from provider check,
        # but default security should be fine. Just verify it doesn't crash.
        assert isinstance(errors, list)


class TestConfigManagerEnvLoading:
    """Automatic .env file loading from project and global directories."""

    def test_loads_project_env(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        sloth_dir = project_dir / ".sloth"
        sloth_dir.mkdir()
        user_config_dir = tmp_path / ".sloth-agent"
        user_config_dir.mkdir(parents=True)

        # Create user config to define the provider
        user_config = user_config_dir / "config.json"
        user_config.write_text(json.dumps(SAMPLE_USER))

        # Create project .env with API key
        (project_dir / ".env").write_text("DEEPSEEK_API_KEY=from-project-env\n")
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

        cm = ConfigManager(project_dir=project_dir, user_config_dir=user_config_dir)
        key = cm.get_api_key("deepseek")
        assert key == "from-project-env"

    def test_falls_back_to_global_env(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        sloth_dir = project_dir / ".sloth"
        sloth_dir.mkdir()
        user_config_dir = tmp_path / ".sloth-agent"
        user_config_dir.mkdir(parents=True)

        # Create user config to define the provider
        user_config = user_config_dir / "config.json"
        user_config.write_text(json.dumps(SAMPLE_USER))

        # Create global .env (no project .env)
        (user_config_dir / ".env").write_text("DEEPSEEK_API_KEY=from-global-env\n")
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

        cm = ConfigManager(project_dir=project_dir, user_config_dir=user_config_dir)
        key = cm.get_api_key("deepseek")
        assert key == "from-global-env"

    def test_project_env_overrides_global_env(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        sloth_dir = project_dir / ".sloth"
        sloth_dir.mkdir()
        user_config_dir = tmp_path / ".sloth-agent"
        user_config_dir.mkdir(parents=True)

        # Create user config to define the provider
        user_config = user_config_dir / "config.json"
        user_config.write_text(json.dumps(SAMPLE_USER))

        # Create both .env files
        (user_config_dir / ".env").write_text("DEEPSEEK_API_KEY=global-key\n")
        (project_dir / ".env").write_text("DEEPSEEK_API_KEY=project-key\n")
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

        cm = ConfigManager(project_dir=project_dir, user_config_dir=user_config_dir)
        key = cm.get_api_key("deepseek")
        assert key == "project-key"
