# 架构总览

> 归档参考: archive/initial-specs/00000000-00-architecture-overview.md
> 最后更新: 2026-05-01

## 产品定位

Sloth Agent — 一站式自主开发智能 Agent。输入一份 Plan，输出已开发、测试通过、部署上线的完整项目。

核心流水线：`Plan → Builder → Gate1 → Reviewer → Gate2 → Deployer → Gate3 → Done`

## 技术栈

| 层 | 技术 |
|---|------|
| 核心运行时 (CLI) | Python 3.10+, typer, pydantic |
| 后端 Sidecar | Python 3.12+, FastAPI, SQLAlchemy async, aiosqlite |
| 前端 | React 18, TypeScript, Vite, Zustand |
| 桌面壳 | Tauri v2 (Rust) |
| 数据库 | SQLite (sloth.db / agent.db) |
| 向量存储 | ChromaDB |
| LLM | OpenAI/Anthropic 双格式，多 Provider 路由 |

## 设计原则

- **3-Agent 串行流水线**（v1.0）：Builder → Reviewer → Deployer
- **工具优先**：Agent 通过工具层执行操作，所有操作可审计
- **技能即指令**：SKILL.md prompt 模板，运行时注入，兼容 Claude Code
- **文件系统即真相**：JSON/jsonl 存储，可回溯、可手动编辑
- **质量保障**：3 道自动门控（lint/type → test/coverage → smoke test）
- **自适应重规划**：门控失败时触发 replan，最多 N 次重试

## 系统全景

```
CLI 入口 (sloth run)
     │
     ▼
Orchestrator (Plan 解析 → 流水线调度)
     │
     ├── Builder Agent  → Gate1 (lint/type)
     ├── Reviewer Agent → Gate2 (test/coverage)
     └── Deployer Agent → Gate3 (smoke test)
```

同时有一套独立的桌面应用（Tauri + React + FastAPI），支持 Inspiration 管理、Agent Pool、团队对话、Brainstorm 模式。

## 目录结构

```
agent-evolve/
├── src/sloth_agent/     # 核心运行时
│   ├── core/            # Runner, NextStep, Orchestrator, Builder, Gates
│   ├── agents/          # Agent 定义与注册
│   ├── tools/           # Tool 调佣、编排、风险门控
│   ├── memory/          # 记忆存储、技能管理
│   ├── providers/       # LLM Provider 路由
│   ├── chat/            # REPL、对话会话
│   ├── cost/            # 成本追踪
│   ├── errors/          # 熔断、错误恢复
│   └── cli/             # CLI 入口
├── backend/             # FastAPI Sidecar
├── frontend/            # React + Tauri 桌面应用
├── skills/              # SKILL.md 技能定义
├── configs/             # YAML 配置
└── docs/
    ├── specs/           # 源头真相（本目录）
    ├── changes/         # 进行中的 Delta 变更
    ├── archive/         # 历史归档
    └── plans/           # 实现计划
```
