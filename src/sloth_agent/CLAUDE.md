# Core CLAUDE (src/sloth_agent)

本文件定义 `src/sloth_agent/` 的实现约束。

## 变更前检查

1. 先确认模块已在 `docs/specs/` 注册。
2. 如新增模块，先更新 `docs/specs/architecture/spec.md`。
3. 先读取对应 `docs/specs/<module>/spec.md` 再实现。

## 开发流程

1. 在 `docs/changes/<change-name>/` 维护 `proposal.md`、`delta.md`、`tasks.md`。
2. 按 `tasks.md` 实现，避免超范围改动。
3. 完成后合并 `delta.md` 回模块 spec，并更新“最后更新”日期。

## 命令与验证

- Python 命令统一 `uv run`。
- 至少执行：
  - `uv run pytest tests/ -v`
  - 涉及评估时：`uv run pytest evals/ -v`

## 约束

- 不通过降低类型、lint 或测试标准来“过门禁”。
- 变更必须附带最小可验证证据（测试或可复现实验步骤）。
