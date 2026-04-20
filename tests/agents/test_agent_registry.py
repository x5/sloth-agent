"""Tests for AgentRegistry."""

import os
import tempfile

from sloth_agent.agents.registry import AgentRegistry
from sloth_agent.agents.models import AgentDefinition


def _make_temp_agents_dir():
    """Create a temp directory with sample agent .md files."""
    tmpdir = tempfile.mkdtemp()

    files = {
        "architect.md": """---
name: architect
description: Software architect for system design.
tools: ["Read", "Grep"]
model: glm-4
---

You are a software architect specializing in system design.""",
        "engineer.md": """---
name: engineer
description: Software engineer for coding.
tools: ["Write", "Edit", "Bash"]
model: deepseek-v3
---

You are a software engineer specializing in implementation.""",
        "reviewer.md": """---
name: reviewer
description: Code reviewer for quality.
tools: ["Read", "Grep"]
model: qwen3
---

You are a code reviewer specializing in quality assurance.""",
    }

    for fname, content in files.items():
        with open(os.path.join(tmpdir, fname), "w") as f:
            f.write(content)

    return tmpdir


class TestAgentRegistryLoad:
    def test_load_from_directory(self):
        tmpdir = _make_temp_agents_dir()
        reg = AgentRegistry.load_from_directory(tmpdir)
        agent_ids = reg.list_all()
        assert "architect" in agent_ids
        assert "engineer" in agent_ids
        assert "reviewer" in agent_ids

    def test_get_returns_definition(self):
        tmpdir = _make_temp_agents_dir()
        reg = AgentRegistry.load_from_directory(tmpdir)
        agent = reg.get("architect")
        assert isinstance(agent, AgentDefinition)
        assert agent.id == "architect"
        assert agent.model == "glm-4"

    def test_get_provider_for(self):
        tmpdir = _make_temp_agents_dir()
        reg = AgentRegistry.load_from_directory(tmpdir)
        provider = reg.get_provider_for("engineer")
        assert provider == "deepseek"

    def test_get_model_for(self):
        tmpdir = _make_temp_agents_dir()
        reg = AgentRegistry.load_from_directory(tmpdir)
        model = reg.get_model_for("reviewer")
        assert model == "qwen3"

    def test_get_description(self):
        tmpdir = _make_temp_agents_dir()
        reg = AgentRegistry.load_from_directory(tmpdir)
        desc = reg.get_description("architect")
        assert "software architect" in desc.lower()

    def test_get_unknown_raises(self):
        tmpdir = _make_temp_agents_dir()
        reg = AgentRegistry.load_from_directory(tmpdir)
        try:
            reg.get("nonexistent")
        except KeyError:
            pass  # Expected

    def test_register_manual(self):
        reg = AgentRegistry()
        reg.register(
            AgentDefinition(
                id="tester",
                name="tester",
                description="Test agent",
                tools=["Bash"],
                model="test-model",
                provider="test",
            )
        )
        assert reg.get("tester").id == "tester"
        assert reg.get_provider_for("tester") == "test"
