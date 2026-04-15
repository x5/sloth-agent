# 37 个技能路由表

| 阶段 | 阶段名称 | Superpowers (auto+manual，14个) | gstack (manual，23个) |
| :--- | :--- | :--- | :--- |
| 阶段一 | 需求分析 | `brainstorming` (需求精炼) | `/office-hours` (产品方向诊断) |
| 阶段二 | 计划制定 | `writing-plans` (可执行实施计划) | `/autoplan` (CEO -> 设计 -> 工程三阶段自动审查) |
| 阶段三 | 编码实现 | `test-driven-development` (TDD 红绿循环)<br>`subagent-driven-development` (子代理逐任务开发)<br>`using-git-worktrees` (隔离工作空间) | |
| 阶段四 | 调试排错 | `systematic-debugging` (4阶段根因分析) | `/browse` (真实 Chromium 浏览器)<br>`/investigate` (浏览器级调试) |
| 阶段五 | 代码审查 | `requesting-code-review` (独立 reviewer 通道)<br>`verification-before-completion` (完成前证据收集) | `/review` (Staff 工程师级审查)<br>`/codex` (跨模型第二意见) |
| 阶段六 | 质量验证 | | `/qa` (真实浏览器端到端测试)<br>`/cso` (安全审计 OWASP + STRIDE)<br>`/plan-design-review` (80项设计审计) |
| 阶段七 | 发布上线 | `finishing-a-development-branch` (分支收尾) | `/ship` (测试 + 覆盖率 + PR)<br>`/land-and-deploy` (CI + 部署验证) |
| 阶段八 | 上线监控 | | `/canary` (控制台错误 + 性能回归) |

**总结：**
* 总技能：14 Superpowers + 23 gstack = 37
* 洞察：Superpowers 专注编码质量（14 个 auto+manual 技能）；gstack 专注产品全流程（23 个 manual 命令）。Superpowers 主要分布于编码实现阶段；gstack 主要分布于质量验证与发布阶段。
