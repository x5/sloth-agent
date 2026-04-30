# LLM Provider 路由

> 归档参考: archive/initial-specs/20260417-20-llm-router-spec.md
> 最后更新: 2026-05-01

## 概述

多 Provider 统一路由层，支持 OpenAI 和 Anthropic 双 API 格式。按 Stage 级别为不同 Agent 分配不同模型。

## 已实现

### LLM Router (`src/sloth_agent/providers/`)

- `llm_router.py` — 多 Provider 路由，按 Agent/Stage 分配模型
- `llm_providers.py` — Provider 实现（OpenAI 格式 + Anthropic 格式）

### 模型分配策略（v1.0 Stage 级）

| Agent | 默认模型 |
|-------|---------|
| Builder | deepseek-v3.2 |
| Reviewer | qwen3.6-plus / claude |
| Deployer | deepseek-v3.2 |

### 配置 (`configs/llm_providers.yaml`)

- 多 Provider 端点定义
- API Key 管理
- 超时与重试配置

### Web 端 LLM 管理（桌面应用）

- `POST /api/llm/test` — 连接测试
- LLM 配置 CRUD
- Settings → LLM tab（前端）

## 待实现

- 自动降级（主 Provider 不可用时切换备选）
- Agent 级独立模型配置
- 费用预测

## 关键接口

- `LLMRouter.route(agent_id, stage) → LLMProvider`
- `LLMProvider.chat(messages, **kwargs) → Response`
- `POST /api/llm/test` — 连接测试
