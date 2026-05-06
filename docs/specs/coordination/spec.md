# 多 Agent 协调

> 归档参考: archive/initial-specs/20260416-03-multi-agent-coordination-spec.md
> 最后更新: 2026-05-01
> 状态: 未实现
> Scope: Core

## 概述

远期目标：8 个专职 Agent 并行执行，支持任务拓扑排序、分组并行、Git worktree 隔离、结果合并和冲突检测。

## 待实现

- 任务 DAG 拓扑排序
- 分组内并行执行
- Git worktree 隔离
- 结果合并 + 冲突检测
- 角色：规划师、编码员、审查员、测试员、集成员、报告员

## 当前状态

v1.0 使用 3-Agent 串行流水线（Builder → Reviewer → Deployer），并行协调未开始。
