# Brainstorm 模式

> 归档参考: archive/initial-specs/20260430-brainstorm-mode-spec.md
> 最后更新: 2026-05-01

## 概述

多 Agent 并行讨论模式。用户发起话题，多个 Expert Agent 并行发言、辩论、协作产出。所有产出写入隔离沙箱，项目文件零风险。

## 已实现

### 后端 API (`backend/app/routers/brainstorm.py`)

- `POST /api/inspirations/{id}/brainstorm-sessions` — 创建会话
- `GET /api/inspirations/{id}/brainstorm-sessions` — 会话列表
- `GET /api/brainstorm-sessions/{id}` — 会话详情（含沙箱文件树）

### 沙箱隔离 (`backend/app/services/sandbox.py`)

- 每个 Brainstorm 会话有独立沙箱目录 `brainstorm-sessions/{id}/`
- 沙箱内可自由读写，项目文件只读

### 数据模型

- `BrainstormSession` — id, inspiration_id, topic, status, sandbox_path
- `BrainstormFile` — session_id, path, content

### 前端 (`frontend/src/stores/brainstormStore.ts`)

- Zustand store 管理 Brainstorm 会话状态

## 待实现（规范阶段）

- 两轮投票引擎（Round 1 意图 + Round 2 完整响应）
- SSE 流式推送 Agent 消息
- 冷却计时器（5s + 3s 确认）
- 彩色线程 UI（BrainstormArea 组件）
- Lead Agent 回合总结

## 迭代计划

| 迭代 | 范围 |
|------|------|
| Iter-4 | 会话沙箱 CRUD |
| Iter-5 | 讨论引擎 + SSE |
| Iter-6 | 彩色线程 UI |
| Iter-7 | 读 Tools + 上下文引擎 |
| Iter-8 | 写 Tools + 受限执行器 |
| Iter-9 | 异步自主模式 |

## 关键接口

- `POST /api/brainstorm-sessions/{id}/discuss` — 发起讨论（规划中）
- `SandboxManager.create_session(inspiration_id) → BrainstormSession`
