# 会话管理

> 归档参考: archive/initial-specs/20260416-05-session-management-spec.md, archive/initial-specs/20260416-13-session-lifecycle-spec.md
> 最后更新: 2026-05-01
> 状态: 部分实现

## 概述

会话生命周期管理、检查点保存与恢复、会话分叉。

## 已实现

- `chat/session.py` — 基础会话逻辑
- `reliability/checkpoint.py` — 基础检查点
- `Runner.persist()` / `Runner.resume_run_state()` — 状态持久化与恢复

## 待实现

- 完整会话生命周期（创建 → 运行 → 暂停 → 恢复 → 归档）
- 会话分叉（fork）
- SQLite 会话索引
