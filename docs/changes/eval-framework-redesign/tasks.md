# 实现任务

## Phase 1: 基础结构

- [ ] 创建 `evals/models.py` — EvalTask、EvalResult、ScoreBreakdown 数据模型
- [ ] 迁移 `tasks.yaml` 至 `eval_tasks:` 顶层列表格式（迁移现有 `create-crud-api` 条目），增加 difficulty、expected 字段
- [ ] 创建 `evals/results/` 目录
- [ ] 创建 `evals/workspaces/` 目录（.gitignore 忽略内容）

## Phase 2: 核心引擎

- [ ] 实现 `evals/scoring.py` — 四维度加权评分，含 L1/L2 归一化逻辑
- [ ] 实现 `evals/artifact_checker.py` — DeployArtifactChecker（L3 部署产物验证）
- [ ] 重写 `evals/runner.py` — 工作区隔离（tempdir per task）+ ThreadPoolExecutor 超时 + HookManager 指标采集 + 调用 scoring
- [ ] 通过 HookManager 注入指标采集 hook（gate.pass/fail、model.end、run.end）

## Phase 3: CLI 与报告

- [ ] 实现 CLI 入口 `sloth eval run` — 支持 --level、--task 过滤
- [ ] 实现 `sloth eval report` — 读取并展示某次结果
- [ ] 实现 `sloth eval compare` — 版本间对比输出

## Phase 4: 任务库

- [ ] 编写 L1 任务 3 个（脚本、CLI 工具、数据处理）
- [ ] 编写 L2 任务 2 个（API 服务、数据库操作）
- [ ] 编写 L3 任务 1 个（全栈应用）

## Phase 5: 验证

- [ ] 编写 eval 模块自身的单元测试
- [ ] 用 L1 任务做端到端验证
- [ ] 更新 docs/specs/eval/spec.md — 合并 delta 条款
