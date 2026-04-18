# 20260417-20-llm-router-implementation-plan.md

> Spec 来源: `docs/specs/20260417-20-llm-router-spec.md`（模块 20）
> Plan 文件: `docs/plans/20260417-20-llm-router-implementation-plan.md`
> 对应 Arch: `docs/specs/00000000-00-architecture-overview.md` §7.3, §11.0
> v0.1.0 实现状态: LLMRouter (register_provider / get_model) + MockProvider 已实现 (2 tests pass)
> v0.1.0 实现文件: `src/sloth_agent/providers/llm_router.py`

---

## 1. 目标

实现阶段级 LLM 路由：按 Agent + Stage 配置不同的模型，提供统一的 `LLMRouter` 和 Provider 接口。

---

## 2. 步骤

### 步骤 1: 实现 LLMRouter 和 Provider

**文件**: `src/sloth_agent/providers/llm_router.py`（新建）

**内容** (spec §2.2, §2.3):

```python
class LLMRouter:
    def __init__(self, config: Config):
        self.providers: dict[str, LLMProvider] = {
            "deepseek": DeepSeekProvider(config),
            "qwen": QwenProvider(config),
        }
        self.routes: dict = config.agents

    def get_model(self, agent: str, stage: str) -> LLMProvider:
        route = self.routes[agent]["stages"][stage]
        return self.providers[route["provider"]]
```

每个 Provider 实现统一的 `generate(messages, temperature, max_tokens) -> str` 接口。

**验收**: 给定 agent + stage，返回正确的 provider 实例。

---

### 步骤 2: 编写单元测试

| 文件 | 覆盖 | 测试数 |
|------|------|--------|
| `tests/providers/test_llm_router.py` | router 路由正确性 + mock provider | 2 |

**具体测试**:

```
test_llm_router.py:
  - test_router_get_model: builder/coding → deepseek, reviewer/review → qwen
  - test_provider_generate_mock: mock provider 的 generate 接口可调用并返回字符串
```

---

## 3. 文件清单

| 文件 | 动作 |
|------|------|
| `src/sloth_agent/providers/llm_router.py` | **新建** |
| `src/sloth_agent/providers/deepseek.py` | **新建** |
| `src/sloth_agent/providers/qwen.py` | **新建** |
| `tests/providers/test_llm_router.py` | **新建** |

---

## 4. 验收标准

- [ ] `LLMRouter.get_model("builder", "coding")` 返回 DeepSeekProvider
- [ ] `LLMRouter.get_model("reviewer", "review")` 返回 QwenProvider
- [ ] Provider 的 mock generate 接口可正常调用
- [ ] 所有测试通过（共 2 tests）

---

*Plan 版本: v1.0.0 | 创建: 2026-04-17*
