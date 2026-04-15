# Sloth Agent vs Claude Code：方向讨论

> 日期: 2026-04-16 更新
> 状态: **方向明确，流程确认**

---

## 核心目标

**Sloth Agent = 黑灯工厂**

```
晚上（22:00）：阶段一 需求分析 → 阶段二 计划制定
白天（09:00-22:00）：阶段三~八 自主执行 (编码→调试→审查→质量→发布→监控)
```

---

## 8 阶段工作流

| 阶段 | 阶段名称 | Superpowers | gstack | 时段 |
| :--- | :--- | :--- | :--- | :--- |
| 阶段一 | 需求分析 | brainstorming | /office-hours | 晚上 |
| 阶段二 | 计划制定 | writing-plans | /autoplan | 晚上 |
| 阶段三 | 编码实现 | TDD, subagent, git-worktrees | | 白天 |
| 阶段四 | 调试排错 | systematic-debugging | /browse, /investigate | 白天 |
| 阶段五 | 代码审查 | requesting-code-review | /review, /codex | 白天 |
| 阶段六 | 质量验证 | | /qa, /cso, /plan-design-review | 白天 |
| 阶段七 | 发布上线 | finishing-a-development-branch | /ship, /land-and-deploy | 白天 |
| 阶段八 | 上线监控 | | /canary | 白天 |

---

## 核心问题回答

### 1. 遇到解决不了的问题怎么办？
**换方式或换模型，不停下。均无法解决时记录，晚上 review。**

### 2. 白天质量谁来保证？
**TDD + 验证门控硬卡。不靠 human review。**

### 3. 和 Claude Code + cron 的差别？
**在于流程约束，要非常细致的流程约束。**

---

## 多模型切换时机

**A + B 组合：**

| 触发条件 | 切换方式 |
|---------|---------|
| **连续失败 N 次** | 按配置切换到备选模型 |
| **按任务类型** | Brainstorming 用 GLM，Implementing 用 DeepSeek，Review 用 Claude |

---

## 晚上 Human 工作流程

```
22:00 阶段一  需求分析 (brainstorming + office-hours)
   ↓
   阶段二  计划制定 (writing-plans + autoplan)
   ↓
   明确需求：生成/细化 SPEC
   ↓
   制定第二天计划：从 PLAN 中确定明天 todo
```

---

*讨论日期: 2026-04-15 → 2026-04-16*
*参与者: 牛马们*
