# Sloth Agent — CLAUDE.md

本文件只保留全局硬约束与入口，详细规范外链到模块级 CLAUDE。

## 权威入口（先读）

- 项目总览与运行方式：`README.md`
- Delta 工作流与模板：`docs/changes/README.md`
- 架构总规范：`docs/specs/architecture/spec.md`
- 模块规格目录：`docs/specs/`

## 模块级 CLAUDE（详细规则）

- Core 模块规范（`src/sloth_agent/`）：`src/sloth_agent/CLAUDE.md`
- 前端规范（TS/ESLint/组件测试）：`frontend/CLAUDE.md`
- 后端规范（单元测试/API 集成测试）：`backend/CLAUDE.md`
- 变更 `src/sloth_agent/` 时，仍以对应模块 spec 为准：`docs/specs/`

## 开发流程（最小闭环）

1. 确认影响模块并阅读对应 spec：
   - Core：`docs/specs/core/<module>/spec.md`
   - CLI：`docs/specs/cli/<module>/spec.md`
   - Desktop：`docs/specs/desktop/<module>/spec.md`
2. 在 `docs/changes/<change-name>/` 建立 `proposal.md`、`delta.md`、`tasks.md`
3. 按 `tasks.md` 实现并同步测试
4. 合并 `delta.md` 回模块 spec
5. 归档变更到 `docs/archive/<change-name>/`

## 工具链初始化

- 首次 clone 后执行 `npm install`（repo root），自动安装 lefthook 并注册 pre-commit hook

## 全局执行约束（必须）

1. 修改 `src/` 前，模块必须已在 `docs/specs/` 注册
2. 新模块先更新 `docs/specs/architecture/spec.md` 再写代码
3. Python 命令统一使用 `uv run`
4. 实现后至少执行：
   - `uv run pytest tests/ -v`
   - 涉及评估时：`uv run pytest evals/ -v`
5. 测试门禁细则按模块级 CLAUDE 执行（`frontend/CLAUDE.md`、`backend/CLAUDE.md`）

## Git 实践要求

1. 分支与提交
   - 功能开发在独立分支进行，禁止直接在主分支长期开发
   - 提交应小步、可回滚，一次提交只做一类改动
2. 提交信息
   - 提交信息需说明“改了什么 + 为什么改”
   - 推荐使用 `type(scope): summary`（如 `feat(frontend): add modal unit tests`）
3. 提交前检查
   - 必须先通过本地 lint 与测试门禁，再执行提交
   - 禁止提交明显失败或不可运行状态
4. 合并策略
   - 通过 PR 合并，PR 描述需包含变更范围、验证命令、风险点
   - 至少通过 CI 质量门禁后再合并
5. 禁止项
   - 未经明确批准，禁止执行破坏性历史操作（如 `git reset --hard`、强推）
   - 不得把密钥、令牌、密码等敏感信息提交到仓库

## 文档维护规则

- 顶层 CLAUDE 仅放入口与硬约束，不复制细节
- 细节优先维护在模块目录的 `CLAUDE.md` 和各目录 `README.md`
- 冲突时以 `docs/specs/` 与对应模块 `README.md` 为准
