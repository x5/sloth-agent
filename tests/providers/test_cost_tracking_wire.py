"""Tests for cost tracking wired into LLMProviderManager."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from sloth_agent.providers.llm_providers import LLMProviderManager, LLMResponse


class TestCostTrackingWireIn:
    @pytest.mark.asyncio
    async def test_chat_records_cost_when_tracker_provided(self, tmp_path):
        from sloth_agent.cost.tracker import CostTracker

        tracker = CostTracker(storage_dir=tmp_path / "cost")
        manager = LLMProviderManager(
            config_path=None,
            cost_tracker=tracker,
        )
        # Add a mock provider
        mock_provider = MagicMock()
        mock_provider.chat = AsyncMock(return_value=LLMResponse(
            content="hello",
            model="test-model",
            usage={"prompt_tokens": 100, "completion_tokens": 50},
        ))
        manager.providers["test"] = mock_provider
        manager.config["providers"] = [{"name": "test", "enabled": True}]
        manager.config["default_provider"] = "test"
        manager.config["fallback"] = {"order": ["test"]}

        from sloth_agent.providers.llm_providers import LLMMessage
        response = await manager.chat(
            [LLMMessage(role="user", content="hi")],
            provider="test",
        )

        assert response.content == "hello"
        assert tracker.get_total_cost() >= 0  # Cost recorded (may be 0 if model unknown)
        assert len(tracker.records) == 1

    @pytest.mark.asyncio
    async def test_chat_without_tracker_still_works(self, tmp_path):
        manager = LLMProviderManager(config_path=None)
        mock_provider = MagicMock()
        mock_provider.chat = AsyncMock(return_value=LLMResponse(
            content="hello",
            model="test-model",
        ))
        manager.providers["test"] = mock_provider
        manager.config["providers"] = [{"name": "test", "enabled": True}]
        manager.config["default_provider"] = "test"
        manager.config["fallback"] = {"order": ["test"]}

        from sloth_agent.providers.llm_providers import LLMMessage
        response = await manager.chat(
            [LLMMessage(role="user", content="hi")],
            provider="test",
        )
        assert response.content == "hello"

    @pytest.mark.asyncio
    async def test_cost_tracker_accepts_kwargs(self, tmp_path):
        from sloth_agent.cost.tracker import CostTracker

        tracker = CostTracker(storage_dir=tmp_path / "cost")
        manager = LLMProviderManager(config_path=None, cost_tracker=tracker)
        mock_provider = MagicMock()
        mock_provider.chat = AsyncMock(return_value=LLMResponse(
            content="test",
            model="gpt-4",
            usage={"prompt_tokens": 200, "completion_tokens": 100},
        ))
        manager.providers["test"] = mock_provider
        manager.config["providers"] = [{"name": "test", "enabled": True}]
        manager.config["default_provider"] = "test"
        manager.config["fallback"] = {"order": ["test"]}

        from sloth_agent.providers.llm_providers import LLMMessage
        response = await manager.chat(
            [LLMMessage(role="user", content="hi")],
            provider="test",
            scenario_id="test-scenario",
            phase_id="build",
            agent_id="builder",
            run_id="run-123",
        )
        assert len(tracker.records) == 1
        record = tracker.records[0]
        assert record.scenario_id == "test-scenario"
        assert record.phase_id == "build"
        assert record.agent_id == "builder"
        assert record.run_id == "run-123"
