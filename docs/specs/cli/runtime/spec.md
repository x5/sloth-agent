# 运行时内核

> 归档参考: archive/initial-specs/20260416-01-phase-role-architecture-spec.md
> 最后更新: 2026-05-01
> Scope: CLI

## 概述

Sloth 的运行时内核由 Runner、RunState、NextStep 协议和 HookManager 组成。顶层只有一个 Runner 执行循环，所有 Agent 共享同一个 RunState。

## 已实现

### 5 步执行循环 (`src/sloth_agent/core/runner.py`)

```
prepare() → think() → resolve() → persist() → observe()
```

- `prepare()` — 组装初始 RunState
- `think()` — 按 current_agent 分发，返回 NextStep 指令
- `resolve()` — 根据 NextStep.type 路由状态转换
- `persist()` — 写 state.json 到文件系统

### NextStep 协议 (`src/sloth_agent/core/nextstep.py`)

8 种状态转换类型：

| 类型 | 含义 |
|------|------|
| `final_output` | 当前阶段正常结束 |
| `tool_call` | 需要调用工具 |
| `phase_handoff` | 阶段交接（如 Builder → Reviewer） |
| `retry_same` | 同一 Agent 重试 |
| `retry_different` | 换 Agent 重试 |
| `replan` | 触发重规划 |
| `interruption` | 中断等待外部输入 |
| `abort` | 终止执行 |

### RunState (`src/sloth_agent/core/runner.py`)

单一 Pydantic 模型，所有 Agent 共享：
- `run_id`, `session_id`, `current_agent`, `current_phase`
- `turn`, `handoff_payload`, `tool_history`, `errors`
- `phase` (initializing/running/paused/completed/aborted)

### HookManager (`src/sloth_agent/core/runner.py`)

轻量事件钩子，hook 点包括：`run.start/end`, `phase.start/end`, `model.start/end`, `tool.start/end`, `handoff`, `gate.pass/fail`, `budget.warn/over`

### 3 道质量门控 (`src/sloth_agent/core/gates.py`)

- Gate1 — Builder 完成后：lint + type check
- Gate2 — Reviewer 完成后：blocking issues + coverage
- Gate3 — Deployer 完成后：smoke test

### 自适应重规划 (`src/sloth_agent/core/adaptive.py`)

AdaptiveTrigger + Replanner：门控连续失败时触发重规划，最多 N 次。

### 三层上下文边界 (`src/sloth_agent/core/runner.py`)

- ModelVisibleContext — 可发给 LLM
- RuntimeOnlyContext — 绝对不能发给 LLM
- RunState — 桥接层

## 待实现

- `observe()` 步骤尚未实现
- 8-Agent 并行执行（远期）

## 关键接口

- `Runner.run(state) → RunState` — 主循环入口
- `Runner.think(state) → NextStep` — Agent 调度
- `Runner.resolve(state, next_step) → RunState` — 状态路由
