"""Integration tests for brainstorm context + tool wiring."""

from pathlib import Path
import sys

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


class TestCoreImports:
    """Verify core modules are importable in the backend context."""

    def test_tool_pool_available(self):
        from sloth_agent.core.tools import ToolPool
        assert ToolPool.get() is not None

    def test_role_base_tools(self):
        from sloth_agent.core.agents.role_tools import ROLE_BASE_TOOLS
        assert "lead" in ROLE_BASE_TOOLS
        assert ROLE_BASE_TOOLS["lead"] == ["read", "grep"]
        assert "fortune" in ROLE_BASE_TOOLS
        assert len(ROLE_BASE_TOOLS["fortune"]) == 6

    def test_run_tool_loop_importable(self):
        from sloth_agent.core.brainstorm.tool_loop import run_tool_loop
        assert callable(run_tool_loop)

    def test_context_engine_importable(self):
        from sloth_agent.core.context.engine import ContextEngine
        assert ContextEngine is not None

    def test_llm_adapter_available(self):
        from app.shared.llm_adapter import LLMAdapter
        assert LLMAdapter is not None

    def test_context_adapter_available(self):
        from app.services.context import build_brainstorm_context, db_messages_to_dicts
        assert callable(build_brainstorm_context)
        assert callable(db_messages_to_dicts)


class TestAgentServiceTools:
    """Verify AgentService.get_effective_tools works correctly."""

    def test_lead_role_tools(self):
        from app.services.agent import AgentService
        tools = AgentService.get_effective_tools("lead")
        assert tools == ["read", "grep"]

    def test_lead_with_extras(self):
        from app.services.agent import AgentService
        tools = AgentService.get_effective_tools("lead", ["extra_tool"])
        assert tools == ["read", "grep", "extra_tool"]

    def test_unknown_role(self):
        from app.services.agent import AgentService
        tools = AgentService.get_effective_tools("unknown_role")
        assert tools == []

    def test_deduplication(self):
        from app.services.agent import AgentService
        tools = AgentService.get_effective_tools("lead", ["read"])
        assert tools == ["read", "grep"]

    def test_fortune_gets_all_tools(self):
        from app.services.agent import AgentService
        tools = AgentService.get_effective_tools("fortune")
        assert len(tools) == 6
        assert "grep_repo" in tools
        assert "ls_dir" in tools
