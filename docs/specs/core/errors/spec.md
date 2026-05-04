# 错误处理与恢复

> 归档参考: archive/initial-specs/20260416-09-error-handling-recovery-spec.md
> 最后更新: 2026-05-01
> Scope: Core（CLI/Desktop 恢复流程按同一语义适配）

## 概述

运行时错误处理、熔断保护和状态恢复机制。

## 已实现

### 熔断器 (`src/sloth_agent/errors/`)

- `circuit_breaker.py` — 熔断器模式，连续失败达到阈值时打开
- `circuit_manager.py` — 管理多个熔断器实例

### 与 Runner 的集成

- NextStep `retry_same` / `retry_different` — 错误后的重试策略
- NextStep `abort` — 不可恢复错误的终止
- AdaptiveTrigger — 门控失败时触发重规划
- RunState.errors — 错误历史记录

### 状态恢复

- `Runner.persist()` — 每轮后写盘，支持中断恢复
- `Runner.resume_run_state()` — 从 state.json 恢复

## 待实现

- 完整的场景恢复（从任意中断点恢复）
- 错误分类与自动处理策略
- 降级执行模式

## 关键接口

- `CircuitBreaker.call(fn) → Result`
- `CircuitManager.get(name) → CircuitBreaker`
- `Runner.resume_run_state(run_dir) → RunState | None`
