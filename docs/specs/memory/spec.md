# 记忆管理

> 归档参考: archive/initial-specs/20260416-04-memory-management-spec.md
> 最后更新: 2026-05-01

## 概述

Sloth 的记忆系统负责存储和检索 Agent 运行时的上下文、对话历史、工具调用记录。

## 已实现

### 文件系统存储 (`src/sloth_agent/memory/store.py`)

- JSONL 格式追加写
- 按 session 组织目录结构
- 可手动编辑、可回溯

### 检索 (`src/sloth_agent/memory/retrieval.py`)

- 基础检索接口
- 按 session_id / run_id 查询

### 与 RunState 的关系

`Runner.persist()` 将 `RunState` 序列化为 `memory/sessions/{run_id}/state.json`，`tool_history` 追加写入 `tool_history.jsonl`。

## 待实现

- SQLite 索引层
- ChromaDB 向量检索
- 自动摘要与压缩

## 关键接口

- `MemoryStore.append(session_id, entry)`
- `MemoryStore.query(session_id, filters) → list`
- `Runner.persist(state)` — 写回 RunState
- `Runner.resume_run_state(run_dir) → RunState` — 恢复
