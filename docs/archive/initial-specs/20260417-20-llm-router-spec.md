# LLM 路由与 Provider 管理规范

> 版本: v1.1.0
> 日期: 2026-04-17
> 状态: Agent-First 架构已实现，stage 概念已移除
> v1.1.0 变更: LLMRouter.get_provider(agent_name) 替代 get_model(agent, stage)
>   - Agent 模型声明从 `agents/*.md` frontmatter 提取
>   - 路由从 `agent → stages → provider` 简化为 `agent → provider`
>   - 实现文件: `src/sloth_agent/providers/llm_router.py`
>   - AgentRegistry: `src/sloth_agent/agents/registry.py`

---

## 1. 问题

不同 Agent 需要不同的 LLM：
1. Architect/Planner 需要推理能力强的模型
2. Engineer/Debugger 需要代码生成质量好的模型
3. Reviewer/QA 必须使用与 Engineer 不同的 provider（避免同源偏见）
4. 没有统一的路由配置和接口，各模块自行管理 LLM 调用

---

## 2. 架构设计

### 2.1 路由配置

v1.1.0 采用 Agent-First 架构，路由信息从 `agents/*.md` 文件的 YAML frontmatter 中提取：

```yaml
---
name: architect
description: 软件架构师。负责系统设计和关键技术决策。
tools: ["Read", "Grep", "Glob"]
model: glm-4
---
```

AgentRegistry 从 `agents/` 目录加载所有定义，LLMRouter 根据 agent 声明的 model/provider 路由。

### 2.2 统一接口

所有 Provider 实现统一的 `generate()` 方法（兼容 OpenAI 格式）：

```python
class LLMProvider:
    """统一的 LLM 接口。"""

    def generate(self, messages: list[dict], temperature: float = 0.0,
                 max_tokens: int | None = None) -> str:
        """发送消息并返回回复内容。"""


class DeepSeekProvider(LLMProvider): ...

class QwenProvider(LLMProvider): ...
```

### 2.3 Router

```python
class LLMRouter:
    """按 agent_name 路由到正确的 LLM Provider。"""

    def __init__(self, config: Config, agent_registry: AgentRegistry):
        self.providers: dict[str, LLMProvider] = {}  # provider_name -> instance
        self.agent_registry = agent_registry

    def get_provider(self, agent_name: str) -> LLMProvider:
        """根据 agent 名称返回对应的 LLM Provider。"""
        model = self.agent_registry.get_model_for(agent_name)
        provider = self.agent_registry.get_provider_for(agent_name)
        return self.providers[provider]
```

---

## 3. 模块定义

### 3.1 LLMRouter

**文件**: `src/sloth_agent/providers/llm_router.py`

**核心方法**:

| 方法 | 说明 |
|------|------|
| `__init__(config, agent_registry)` | 初始化 providers 和 agent_registry |
| `get_provider(agent_name)` | 返回对应 LLMProvider 实例 |

### 3.2 AgentRegistry

**文件**: `src/sloth_agent/agents/registry.py`

**核心方法**:

| 方法 | 说明 |
|------|------|
| `load_from_directory(path)` | 从目录加载所有 `.md` Agent 定义 |
| `get(agent_id)` | 返回 AgentDefinition |
| `get_provider_for(agent_id)` | 返回 provider 名 |
| `get_model_for(agent_id)` | 返回 model 名 |

### 3.3 Provider 实现

**文件**: `src/sloth_agent/providers/deepseek.py`、`src/sloth_agent/providers/qwen.py`（新建）

统一的 OpenAI-compatible API 调用。

---

## 4. 文件清单

| 文件 | 说明 |
|------|------|
| `src/sloth_agent/providers/__init__.py` | Provider 模块入口 |
| `src/sloth_agent/providers/llm_router.py` | LLMRouter |
| `src/sloth_agent/providers/deepseek.py` | DeepSeek Provider |
| `src/sloth_agent/providers/qwen.py` | Qwen Provider |
| `src/sloth_agent/agents/registry.py` | AgentRegistry |
| `src/sloth_agent/agents/models.py` | AgentDefinition 数据模型 |

---

## 5. 测试策略

| 测试 | 说明 |
|------|------|
| `test_router_get_provider` | agent_name 路由到正确的 provider |
| `test_provider_generate_mock` | mock provider 的 generate 接口可调用 |
| `test_agent_registry_load` | AgentRegistry 从 `.md` 文件加载定义 |

---

*规格版本: v1.1.0*
*创建日期: 2026-04-17*
*更新日期: 2026-04-20*
