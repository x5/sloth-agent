# Delta: Evals 评估框架重新设计

> 关联模块: specs/eval/spec.md

## ADDED Requirements

- REQ-EVAL-001: EvalRunner 复用 Sloth 流水线执行真实 LLM 任务，不使用 Mock
- REQ-EVAL-002: 支持 L1/L2/L3 三级难度分级（L1 单文件、L2 多模块 CRUD、L3 全栈应用）
- REQ-EVAL-003: 四维度加权评分，每个 task 总分均归一化到 100。L1 只跑 Gate1，Gate 得分 = 40 × (实际通过数 / 该 level 最大 Gate 数)，L1 max=1，L2 max=2，L3 max=3；部署产物维度 L1/L2 不计，其 10% 均摊至其余三维（正确性 44.4%、产出质量 33.3%、过程效率 22.2%），L3 保持原始权重。
- REQ-EVAL-004: 通过 HookManager 在 gate.pass/fail、model.end、run.end 时采集指标
- REQ-EVAL-005: 结果存储为 JSON 文件，路径 `evals/results/{version}.json`
- REQ-EVAL-006: 支持版本间对比，输出逐维度 diff 表格
- REQ-EVAL-007: 单 task 超时实现：`concurrent.futures.ThreadPoolExecutor` 包装 Runner.run()，`future.result(timeout=max_duration_sec)` 超时后判 D，跨平台兼容（不使用 SIGALRM）
- REQ-EVAL-008: CLI 入口：`sloth eval run / report / compare`
- REQ-EVAL-009: tasks.yaml 重构为 `eval_tasks:` 顶层列表（破坏性变更），需迁移现有 `create-crud-api` 条目；每条目增加 difficulty、expected 指标字段
- REQ-EVAL-010: L3 部署产物检查由专用 `DeployArtifactChecker` 实现（检查 Dockerfile / docker-compose.yml 存在且可解析），不复用 Gate3 接口（Gate3 接收 deploy_result dict，语义不同）
- REQ-EVAL-011: 评分等级 A(90+) / B(75+) / C(60+) / D(<60)
- REQ-EVAL-012: 每个 task 在独立临时工作区运行（`evals/workspaces/{task_name}_{timestamp}/`），Runner 初始化时注入 workspace_dir，任务结束后清理

## MODIFIED Requirements

- REQ-EVAL-旧-001: eval runner 从"只验证 plan 文件存在"改为"执行完整流水线并采集指标"
- REQ-EVAL-旧-002: tasks.yaml schema 增加 difficulty 和 expected 指标字段

## REMOVED Requirements

- REQ-EVAL-旧-003: 移除 smoke_test.py（冒烟测试功能合并到 Gate3，eval 不再需要独立的 mock 冒烟测试）
