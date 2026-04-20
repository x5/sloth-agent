"""Agent definition data model."""

from dataclasses import dataclass, field


@dataclass
class AgentDefinition:
    """从 agents/*.md 加载的 Agent 定义。"""
    id: str                                    # "architect", "engineer"
    name: str                                  # 显示名
    description: str                           # System Prompt / 行为描述
    tools: list[str] = field(default_factory=list)  # 可用工具列表
    model: str = ""                            # 模型标识符 (e.g. "deepseek-v3.2")
    provider: str = ""                         # Provider 名 (e.g. "deepseek")
