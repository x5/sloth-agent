"""Agent Registry — 从 agents/*.md 加载 Agent 定义。

格式参考 everything-claude-code:
---
name: architect
description: Software architecture specialist...
tools: ["Read", "Grep", "Glob"]
model: opus
---
"""

from __future__ import annotations

import re
from pathlib import Path

from sloth_agent.agents.models import AgentDefinition


class AgentRegistry:
    """Agent 注册表，从 agents/*.md 目录加载。"""

    def __init__(self, agents: dict[str, AgentDefinition] | None = None):
        self._agents: dict[str, AgentDefinition] = agents or {}

    @classmethod
    def load_from_directory(cls, directory: str | Path) -> "AgentRegistry":
        """从目录加载所有 .md Agent 定义。"""
        dir_path = Path(directory)
        agents: dict[str, AgentDefinition] = {}

        if not dir_path.exists():
            return cls(agents)

        for md_file in sorted(dir_path.glob("*.md")):
            agent = cls._parse_md(md_file)
            if agent:
                agents[agent.id] = agent

        return cls(agents)

    @staticmethod
    def _parse_md(filepath: Path) -> AgentDefinition | None:
        """解析 .md 文件的 YAML frontmatter + body。"""
        content = filepath.read_text(encoding="utf-8")

        # Extract frontmatter between --- markers
        match = re.match(r"^---\n(.*?)\n---\n(.*)", content, re.DOTALL)
        if not match:
            return None

        frontmatter = match.group(1)
        body = match.group(2).strip()

        # Parse simple YAML frontmatter
        fm: dict[str, str | list] = {}
        for line in frontmatter.splitlines():
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()

            # Parse list: ["Read", "Grep", "Glob"]
            if value.startswith("["):
                items = re.findall(r'"([^"]*)"', value)
                fm[key] = items
            else:
                fm[key] = value

        return AgentDefinition(
            id=fm.get("name", filepath.stem),
            name=fm.get("name", filepath.stem),
            description=fm.get("description", ""),
            tools=fm.get("tools", []),
            model=fm.get("model", ""),
        )

    def get(self, agent_id: str) -> AgentDefinition | None:
        """获取 Agent 定义。"""
        return self._agents.get(agent_id)

    def get_provider_for(self, agent_id: str) -> str:
        """返回 Agent 对应的 Provider 名（从 model 推导）。"""
        agent = self.get(agent_id)
        if not agent or not agent.model:
            return ""
        # model 如 "deepseek-v3.2" → provider "deepseek"
        return agent.model.split("-")[0]

    def get_model_for(self, agent_id: str) -> str:
        """返回 Agent 的模型标识符。"""
        agent = self.get(agent_id)
        if not agent:
            return ""
        return agent.model

    def get_description(self, agent_id: str) -> str:
        """返回 Agent 的角色描述（用作 System Prompt）。"""
        agent = self.get(agent_id)
        if not agent:
            return ""
        return agent.description

    def list_all(self) -> list[str]:
        """返回所有已注册的 Agent ID。"""
        return list(self._agents.keys())

    def register(self, agent: AgentDefinition) -> None:
        """手动注册一个 Agent 定义。"""
        self._agents[agent.id] = agent
