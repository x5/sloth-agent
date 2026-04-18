# 42 个技能路由表

> 更新: 2026-04-19 — v0.4 批量复用完成，总计 42 个内建技能，全部 auto+manual

| 阶段 | 阶段名称 | Superpowers (12个) | gstack (30个) |
| :--- | :--- | :--- | :--- |
| 阶段一 | 需求分析 | `brainstorming` | `/office-hours` |
| 阶段二 | 计划制定 | `writing-plans` | `/autoplan`, `/plan-ceo-review`, `/plan-eng-review`, `/plan-devex-review` |
| 阶段三 | 编码实现 | `test-driven-development`, `subagent-driven-development`, `using-git-worktrees` | `/checkpoint`, `/learn` |
| 阶段四 | 调试排错 | `systematic-debugging` | `/investigate`, `/benchmark` |
| 阶段五 | 代码审查 | `requesting-code-review`, `verification-before-completion` | `/review`, `/receiving-code-review` |
| 阶段六 | 质量验证 | | `/qa`, `/qa-only`, `/cso`, `/plan-design-review`, `/design-review` |
| 阶段七 | 发布上线 | `finishing-a-development-branch` | `/ship`, `/land-and-deploy`, `/document-release`, `/setup-deploy`, `/retro` |
| 阶段八 | 上线监控 | | `/canary` |
| 设计相关 | | | `/design-consultation`, `/design-shotgun`, `/design-html`, `/devex-review` |
| 安全限制 | | | `/careful`, `/freeze`, `/guard`, `/unfreeze` |
| 元技能 | `writing-skills`, `dispatching-parallel-agents` | |

**总结：**
* 总技能：12 Superpowers + 30 gstack = 42
* 全部 trigger: auto+manual
* 每个 skill 的 description 包含 chat 触发短语，支持自动意图匹配
