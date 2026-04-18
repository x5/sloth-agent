# Skill 批量复用规范 — 已完成

> 最后更新: 2026-04-19
> 状态: 42 个技能全部导入完毕，trigger 统一为 auto+manual

## 概述

从 37 技能路由表（`docs/ref/37_skills_route_table.md`）中，除去已复用的 `test-driven-development` 和 `systematic-debugging`，剩余 35 个技能需要评估并批量复用到 `skills/builtin/`。最终实际导入 42 个技能（包含 spec 中未列出的 careful/freeze/guard/unfreeze/setup-deploy/learn/devex-review）。

**目标：** 每个技能产出独立的 SKILL.md + 配套参考文件，标注来源，适配我们的工具链（Python/uv pytest、Claude Code 内置工具），无外部二进制依赖。

**结果：** 42 个技能全部导入完毕，所有 `trigger: auto+manual`，所有 description 补充了 chat 触发短语。

## 技能来源

| 来源 | 目录 | 许可证 | 复用条件 |
|------|------|--------|----------|
| obra/superpowers | `docs/ref/superpowers-main/skills/` | MIT | 保留版权声明，标注来源 |
| gstack | `docs/ref/gstack-main/` | 无明确开源许可 | 提取方法论部分，剥离 gstack 生态依赖 |

## 复用分类体系

### Tier A：纯方法论（PURE）

**特征：** SKILL.md 内容是推理框架和决策流程，不调用外部二进制、不需要浏览器、没有脚本依赖。

**适配动作：**
1. 复制 SKILL.md 内容
2. 前缀 `source` 字段标注来源
3. 调整工具调用为 Claude Code 内置工具（Read/Grep/Bash 等）
4. 移除所有 `~/.gstack/` 路径引用
5. 将 `AskUserQuestion` 保持原样（我们已支持）
6. 将 `Agent` 子代理调用保持原样（我们已支持）

### Tier B：轻量工具（TOOLS）

**特征：** 依赖 git、标准 shell 工具（grep/find/sed）、项目测试框架。

**适配动作：**
1. 执行 Tier A 全部动作
2. Python 脚本统一使用 `uv run python`
3. 测试命令统一使用 `uv run pytest`
4. 移除对 gstack 二进制（`gstack-slug`、`gstack-config` 等 35 个）的引用
5. 移除 `bun`/`npm` 引用，替换为项目等价物
6. 移除 `npx slop-scan` 引用
7. 移除 `codex` CLI 引用（如需要"第二意见"，改用 Agent 子代理）

### Tier C：浏览器依赖（BROWSER）

**特征：** 需要 `$B`（Playwright/Chromium）或 `$D`（GPT Image API）二进制。

**适配动作：**
1. 执行 Tier A 全部动作
2. 浏览器交互改为 `WebFetch` + `WebSearch` 工具
3. 视觉检查改为描述性指令（"使用浏览器检查..."）
4. 设计生成移除（我们没有 `$D` 二进制）
5. 保留方法论框架，标注"需要浏览器工具时可扩展"

### Tier D：复杂系统（COMPLEX）

**特征：** 依赖多个外部系统（Codex CLI、gh CLI、gstack 生态二进制、浏览器、设计工具）。

**适配动作：**
1. 优先使用 `openclaw/` 目录下的精简版方法论版本（如有）
2. 如果没有精简版，手动提取核心方法论，剥离所有生态依赖
3. 用 Agent 子代理替代多代理编排
4. 用 Claude Code 工具替代外部 CLI（gh → Git 工具，codex → Agent 子代理）
5. 标注"完整实现需要额外基础设施"

## 每个技能的适配检查清单

- [ ] 前缀 `source` 字段正确（如 "adapted from obra/superpowers, MIT License"）
- [ ] 无 `~/.gstack/` 路径引用
- [ ] 无 gstack 二进制引用（35 个 bin/ 脚本）
- [ ] Python 脚本使用 `uv run python`
- [ ] 测试命令使用 `uv run pytest`
- [ ] 无 `codex` CLI 引用
- [ ] 无 `npx slop-scan` 引用
- [ ] 无 `bun`/`npm` 引用（除非是项目本身的依赖管理）
- [ ] 配套参考文件（checklist、anti-patterns 等）一并复制
- [ ] SKILL.md 触发条件正确（`trigger: auto+manual`）
- [ ] 版本号设为 `1.0.0`（初始导入）
- [ ] 无绝对路径引用（全部改为相对路径或描述性指令）

## 浏览器自动化集成

Tier C 和 Tier D 中的多个技能需要浏览器能力（QA 审计、设计审查、调试等）。我们选择**内建 Playwright Python 包 + 首次使用时安装 Chromium**。

### 方案

| 层次 | 内容 | 说明 |
|------|------|------|
| Python 依赖 | `playwright` + `pytest-playwright` | 通过 `uv pip install` 安装，体积小（~3MB） |
| 浏览器二进制 | Chromium（~150MB） | 首次使用时按需下载，不强制 |

### 安装流程

安装脚本（`install.sh` / `install.ps1`）在末尾执行以下可选步骤：

```bash
# 安装 Playwright Python 包
uv pip install playwright pytest-playwright

# 下载 Chromium 浏览器（带确认提示）
uv run playwright install chromium
```

Windows PowerShell 同理。如果用户跳过 Chromium 下载，浏览器相关 Skill 自动降级到 `WebFetch` 模式。

### 技能中的浏览器使用约定

Skill 文档中的浏览器交互统一采用以下模式：

```markdown
1. 优先使用 Playwright（`uv run python` 调用 `playwright.sync_api`）
2. 如果浏览器不可用（未安装或启动失败），降级为 WebFetch/WebSearch
3. 所有浏览器操作必须在临时目录中运行，不污染用户环境
```

Python 示例脚本统一放在 `skills/builtin/{skill-name}/scripts/` 目录，使用 `uv run python scripts/{script}.py` 调用。

### 依赖检查

安装脚本应检测以下状态：

| 检查项 | 失败处理 |
|--------|----------|
| `playwright` 包已安装 | 提示 `uv pip install playwright` |
| `chromium` 已下载 | 提示 `uv run playwright install chromium` |
| Playwright 可启动 | 标记浏览器功能可用，否则标记为降级模式 |

## 35 个技能分类结果

### Tier A（PURE）— 2 个

| # | 技能名 | 来源 | 说明 |
|---|--------|------|------|
| 1 | brainstorming | superpowers | 创意转化为设计框架的推理流程 |
| 2 | checkpoint | gstack (openclaw) | 进度保存/恢复机制 |

### Tier B（TOOLS）— 10 个

| # | 技能名 | 来源 | 说明 |
|---|--------|------|------|
| 3 | writing-plans | superpowers | 实施计划编写框架 |
| 4 | verification-before-completion | superpowers | 完成前证据收集 |
| 5 | requesting-code-review | superpowers | 独立 reviewer 通道 |
| 6 | receiving-code-review | superpowers | 接受代码评审指导 |
| 7 | using-git-worktrees | superpowers | Git 工作树隔离 |
| 8 | subagent-driven-development | superpowers | 子代理逐任务开发 |
| 9 | retro | gstack (openclaw) | 每周回顾，git 命令分析 |
| 10 | investigate | gstack (openclaw) | 系统根因调试 |
| 11 | document-release | gstack (openclaw) | 发布后文档更新 |
| 12 | health | gstack | 代码质量健康检查 |

### Tier C（BROWSER）— 4 个

**特征：** 原 gstack 版本需要 `$B`（Playwright/Chromium）或 `$D`（GPT Image API）二进制。
**现状：** Playwright 已内建为 Python 依赖，可直接使用。

| # | 技能名 | 来源 | 说明 |
|---|--------|------|------|
| 13 | qa | gstack | 6 阶段 QA 工作流，使用 Playwright |
| 14 | qa-only | gstack | QA 仅报告模式 |
| 15 | design-review | gstack | 设计审计 + 修复循环（去除 $D 依赖） |
| 16 | investigate (完整版) | gstack | 浏览器级调试（与 #10 合并） |

### Tier D（COMPLEX）— 19 个

| # | 技能名 | 来源 | 精简版 | 说明 |
|---|--------|------|--------|------|
| 17 | office-hours | gstack | openclaw 版可用 | 产品方向诊断 |
| 18 | plan-ceo-review | gstack | openclaw 版可用 | CEO 级计划审查 |
| 19 | plan-eng-review | gstack | 无 | 工程计划审查 |
| 20 | plan-design-review | gstack | 无 | 设计审计（80 项） |
| 21 | plan-devex-review | gstack | 无 | 开发者体验审查 |
| 22 | review | gstack | 无 | Staff 工程师审查 |
| 23 | ship | gstack | 无 | 测试+覆盖率+PR |
| 24 | land-and-deploy | gstack | 无 | CI+部署验证 |
| 25 | canary | gstack | 无 | 控制台错误+性能回归 |
| 26 | codex | gstack | 无 | 跨模型第二意见 |
| 27 | design-consultation | gstack | 无 | 设计系统从零 |
| 28 | design-shotgun | gstack | 无 | 快速视觉设计探索 |
| 29 | cso | gstack | 无 | 安全审计 OWASP+STRIDE |
| 30 | benchmark | gstack | 无 | 性能回归检测 |
| 31 | autoplan | gstack | 无 | 自动审查流水线 |
| 32 | open-gstack-browser | gstack | 无 | 启动浏览器 |
| 33 | finishing-a-development-branch | superpowers | 无 | 分支收尾 |
| 34 | writing-skills | superpowers | 无 | 技能编写指南 |
| 35 | dispatching-parallel-agents | superpowers | 无 | 并行子代理调度 |

## 不可直接复用的技能

以下 gstack 技能因强依赖专有二进制或外部服务，本次不纳入复用范围：

- ~~`setup-deploy`~~ — 已适配：剥离 bun 和云 CLI 依赖，保留部署配置方法论
- `gstack-upgrade` — 依赖 gstack 自身升级机制
- `plan-tune` — 依赖 `gstack-developer-profile` 心理画像系统
- ~~`freeze` / `unfreeze`~~ — 已适配：改为通用编辑范围限制，不依赖 gstack 会话冻结基础设施
