# LLM 路由与 Provider 管理规范

> 版本: v1.0.0
> 日期: 2026-04-17
> 状态: 新增

---

## 1. 问题

不同 Agent 在不同阶段需要不同的 LLM：
1. Builder coding 阶段需要代码生成质量好的模型
2. Builder debugging 需要推理能力强的模型
3. Reviewer 必须使用与 Builder 不同的 provider（避免同源偏见）
4. 没有统一的路由配置和接口，各模块自行管理 LLM 调用

---

## 2. 架构设计

### 2.1 路由配置

v1.0 按 Agent + Stage 路由：

```yaml
# configs/agent.yaml
agents:
  builder:
    stages:
      plan_parsing:
        provider: "deepseek"
        model: "deepseek-r1-0528"
      coding:
        provider: "deepseek"
        model: "deepseek-v3.2"
      debugging:
        provider: "deepseek"
        model: "deepseek-r1-0528"
  reviewer:
    stages:
      review:
        provider: "qwen"
        model: "qwen3.6-plus"
  deployer:
    stages:
      deploy:
        provider: "deepseek"
        model: "deepseek-v3.2"
```

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
    """按 agent + stage 路由到正确的 LLM Provider。"""

    def __init__(self, config: Config):
        self.providers: dict[str, LLMProvider] = {}  # provider_name -> instance
        self.routes: dict = config.agents  # 从配置加载

    def get_model(self, agent: str, stage: str) -> LLMProvider:
        """根据 agent 和 stage 返回对应的 LLM Provider。"""
        route = self.routes[agent]["stages"][stage]
        return self.providers[route["provider"]]
```

---

## 3. 模块定义

### 3.1 LLMRouter

**文件**: `src/sloth_agent/providers/llm_router.py`（新建）

**核心方法**:

| 方法 | 说明 |
|------|------|
| `__init__(config)` | 初始化 providers 和 routes |
| `get_model(agent, stage)` | 返回对应 LLMProvider 实例 |

### 3.2 Provider 实现

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

---

## 5. 测试策略

| 测试 | 说明 |
|------|------|
| `test_router_get_model` | agent + stage 路由到正确的 provider |
| `test_provider_generate_mock` | mock provider 的 generate 接口可调用 |

---

*规格版本: v1.0.0*
*创建日期: 2026-04-17*
