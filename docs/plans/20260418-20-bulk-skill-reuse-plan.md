# Plan: 批量 Skill 复用（v0.4 技能扩展）— 已完成

## Context

Spec `20260418-19-bulk-skill-reuse-spec.md` 定义了 35 个待复用技能的分类和适配检查清单。本计划按复杂度分 3 批执行。

**约束条件：**
- 所有 Python 脚本使用 `uv run python`
- 所有测试使用 `uv run pytest`
- 每个 SKILL.md 前缀必须标注来源
- 不引入外部二进制依赖（gstack 35 个 bin、Codex CLI、$B、$D 等）
- 保持 482 测试全部通过

**状态：全部完成。** 42 个内建技能已导入完毕，所有 `trigger` 设为 `auto+manual`，所有 description 补充了 chat 触发短语。

## 执行结果

### 第一批：Tier A + Tier B（12 个技能）✅ 已完成

| 序号 | 技能 | 状态 |
|------|------|------|
| 1 | brainstorming | ✅ |
| 2 | verification-before-completion | ✅ |
| 3 | writing-plans | ✅ |
| 4 | requesting-code-review | ✅ |
| 5 | receiving-code-review | ✅ |
| 6 | using-git-worktrees | ✅ |
| 7 | subagent-driven-development | ✅ |
| 8 | finishing-a-development-branch | ✅ |
| 9 | writing-skills | ✅ |
| 10 | dispatching-parallel-agents | ✅ |
| 11 | retro | ✅ |
| 12 | investigate | ✅ |

### 第二批：Tier C（4 个技能）✅ 已完成

| 序号 | 技能 | 状态 |
|------|------|------|
| 13 | document-release | ✅ |
| 14 | health | ✅ |
| 15 | qa | ✅ |
| 16 | qa-only | ✅ |

### 第三批：Tier D（19 个技能 + 额外 7 个）✅ 已完成

| 序号 | 技能 | 状态 |
|------|------|------|
| 17 | office-hours | ✅ |
| 18 | plan-ceo-review | ✅ |
| 19 | plan-eng-review | ✅ |
| 20 | plan-design-review | ✅ |
| 21 | plan-devex-review | ✅ |
| 22 | review | ✅ |
| 23 | ship | ✅ |
| 24 | land-and-deploy | ✅ |
| 25 | canary | ✅ |
| 26 | design-consultation | ✅ |
| 27 | design-shotgun | ✅ |
| 28 | design-review | ✅ |
| 29 | cso | ✅ |
| 30 | benchmark | ✅ |
| 31 | autoplan | ✅ |
| 32 | checkpoint | ✅ |
| 33 | setup-deploy | ✅ |
| 34 | learn | ✅ |
| 35 | careful | ✅ |
| 36 | freeze | ✅ |
| 37 | guard | ✅ |
| 38 | unfreeze | ✅ |
| 39 | devex-review | ✅ |
| 40 | design-html | ✅ |
| 41 | test-driven-development | ✅ (v0.3 已存在) |
| 42 | systematic-debugging | ✅ (v0.3 已存在) |

## 后续更新（v0.4 完成后）

- 所有 42 个技能的 `trigger` 从 `manual` 统一改为 `auto+manual`
- 所有 42 个技能的 `description` 补充了 chat 触发短语，支持自动意图匹配
- `docs/specs/20260416-06-skill-management-spec.md` 已更新为 42 技能路由表
- `docs/plans/20260416-06-skill-management-implementation-plan.md` 已添加 v0.4 完成状态

## 验证

每批完成后：
1. `ls skills/builtin/` — 确认新技能目录存在
2. `grep "source:" skills/builtin/*/SKILL.md` — 确认来源标注
3. `grep -r "\.gstack" skills/builtin/` — 确认无残留
4. `uv run pytest` — 确认测试通过（当前 482 tests pass）
