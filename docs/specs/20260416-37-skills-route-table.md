# Sloth Agent 37 技能路由表

> 版本: v1.0.0
> 日期: 2026-04-16
> 参考: Superpowers (14 skills) + gstack (23 skills) = 37 skills

---

## 8 阶段工作流

| 阶段 | 阶段名称 | Superpowers (自动触发，14个) | gstack (手动命令，23个) |
| :--- | :--- | :--- | :--- |
| 阶段一 | 需求分析 | `brainstorming` (需求精炼) | `/office-hours` (产品方向诊断) |
| 阶段二 | 计划制定 | `writing-plans` (可执行实施计划) | `/autoplan` (CEO -> 设计 -> 工程三阶段自动审查) |
| 阶段三 | 编码实现 | `test-driven-development` (TDD 红绿循环)<br>`subagent-driven-development` (子代理逐任务开发)<br>`using-git-worktrees` (隔离工作空间) | |
| 阶段四 | 调试排错 | `systematic-debugging` (4阶段根因分析) | `/browse` (真实 Chromium 浏览器)<br>`/investigate` (浏览器级调试) |
| 阶段五 | 代码审查 | `requesting-code-review` (独立 reviewer 通道)<br>`verification-before-completion` (完成前证据收集) | `/review` (Staff 工程师级审查)<br>`/codex` (跨模型第二意见) |
| 阶段六 | 质量验证 | | `/qa` (真实浏览器端到端测试)<br>`/cso` (安全审计 OWASP + STRIDE)<br>`/plan-design-review` (80项设计审计) |
| 阶段七 | 发布上线 | `finishing-a-development-branch` (分支收尾) | `/ship` (测试 + 覆盖率 + PR)<br>`/land-and-deploy` (CI + 部署验证) |
| 阶段八 | 上线监控 | | `/canary` (控制台错误 + 性能回归) |

---

## 黑灯工厂：日夜分工

### 晚上（Human + Agent）→ 阶段一、阶段二

```
22:00 阶段一  需求分析
      ↓
      阶段二  计划制定
      ↓
      生成次日执行的 SPEC + PLAN
      ↓
      22:00 结束
```

**晚上做什么：**
- 人类补位：解决白天记录的未解决问题
- 明确需求：生成/细化 SPEC（阶段一）
- 制定计划：从 PLAN 中确定明天 todo（阶段二）

### 白天（Agent 自主）→ 阶段三 ~ 阶段八

```
09:00 阶段三  编码实现 (TDD + 子代理)
      ↓
      阶段四  调试排错 (如遇错误)
      ↓
      阶段五  代码审查 (review + codex 第二意见)
      ↓
      阶段六  质量验证 (QA + 安全 + 设计)
      ↓
      阶段七  发布上线 (ship + deploy)
      ↓
22:00 阶段八  上线监控 → 生成日报 → 结束
```

**白天做什么：**
- 严格按 8 阶段流程约束执行
- 遇到问题换模型/方式尝试
- 无法解决则记录，等晚上 review
- TDD + 验证门控硬卡，不靠 human

---

## 技能分类

### Superpowers (14 个自动触发)

| 技能 | 阶段 | 说明 |
|------|------|------|
| `brainstorming` | 阶段一 | 通过提问精炼需求，分段呈现设计方案 |
| `writing-plans` | 阶段二 | 将工作分解为 2-5 分钟微任务，包含文件路径、测试、验证步骤 |
| `test-driven-development` | 阶段三 | RED-GREEN-REFACTOR 循环 |
| `subagent-driven-development` | 阶段三 | 每个子任务创建独立子代理执行 |
| `using-git-worktrees` | 阶段三 | 隔离工作空间 |
| `systematic-debugging` | 阶段四 | 四阶段根因分析 |
| `requesting-code-review` | 阶段五 | 独立 reviewer 通道 |
| `verification-before-completion` | 阶段五 | 完成前收集证据 |
| `finishing-a-development-branch` | 阶段七 | 分支收尾，合并/PR 决策 |
| `receiving-code-review` | - | 接收审查反馈 |
| `executing-plans` | - | 批量执行计划，带 checkpoint |
| `dispatching-parallel-agents` | - | 并发子代理工作流 |
| `writing-skills` | - | 创建/修改技能 |
| `using-superpowers` | - | 技能系统介绍 |

### gstack (23 个手动命令)

| 技能 | 阶段 | 说明 |
|------|------|------|
| `/office-hours` | 阶段一 | 6 个强制问题诊断产品方向 |
| `/autoplan` | 阶段二 | CEO → 设计 → 工程三阶段自动审查 |
| `/browse` | 阶段四 | 真实 Chromium 浏览器 |
| `/investigate` | 阶段四 | 浏览器级系统调试 |
| `/review` | 阶段五 | 发现通过 CI 但生产会炸的 bug |
| `/codex` | 阶段五 | 通过 OpenAI Codex CLI 交叉分析 |
| `/qa` | 阶段六 | 真实浏览器端到端测试 |
| `/cso` | 阶段六 | OWASP Top 10 + STRIDE 威胁模型 |
| `/plan-design-review` | 阶段六 | 80 项设计审计 |
| `/ship` | 阶段七 | 测试 + 覆盖率 + PR |
| `/land-and-deploy` | 阶段七 | CI + 部署验证 |
| `/canary` | 阶段八 | 控制台错误 + 性能回归监控 |
| `/qa-only` | 阶段六 | 报告模式（不修改代码） |
| `/plan-ceo-review` | 阶段二 | 重新思考问题，4 种模式 |
| `/plan-eng-review` | 阶段二 | 锁定架构、数据流、边界条件 |
| `/plan-devex-review` | 阶段二 | 交互式 DX 审查 |
| `/design-consultation` | 阶段一 | 从零构建设计系统 |
| `/design-shotgun` | 阶段一 | 生成 4-6 个 AI 方案变体 |
| `/design-html` | - | 生成生产级 HTML/CSS |
| `/design-review` | - | 审计 + 修复 |
| `/devex-review` | - | 实时审计 onboarding 流程 |
| `/retro` | - | 每周团队回顾 |

---

## 多模型路由

| 阶段 | 推荐 LLM | 原因 |
|------|---------|------|
| 阶段一 (需求分析) | GLM-4 | 创意生成能力强 |
| 阶段二 (计划制定) | Claude 3.5 | 结构化思考强 |
| 阶段三 (编码实现) | DeepSeek | 代码生成强 |
| 阶段四 (调试排错) | Claude 3.5 | 逻辑推理强 |
| 阶段五 (代码审查) | Claude 3.5 + Codex | 深度分析 + 第二意见 |
| 阶段六 (质量验证) | Claude 3.5 | QA 分析 |
| 阶段七 (发布上线) | Claude 3.5 | 可靠执行 |
| 阶段八 (上线监控) | MiniMax | 快速推理 |

**切换时机：**
- 连续失败 N 次 → 切换到备选模型
- 按任务类型 → 自动选择对应 LLM

---

## 验证门控

| 阶段 | 门控条件 |
|------|---------|
| 阶段三 → 阶段四 | TDD 循环通过 (RED → GREEN → REFACTOR) |
| 阶段四 → 阶段五 | 错误已修复，测试通过 |
| 阶段五 → 阶段六 | 代码审查通过 + verification 收集完成 |
| 阶段六 → 阶段七 | QA 通过 + 安全审计通过 + 设计审计通过 |
| 阶段七 → 阶段八 | 部署成功 + CI 通过 |

---

*规范版本: v1.0.0*
*创建日期: 2026-04-16*
