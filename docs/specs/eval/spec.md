# 评估框架

> 归档参考: archive/initial-specs/20260417-21-eval-framework-spec.md
> 最后更新: 2026-05-02
> 状态: 实现中

## 概述

对 Agent 能力进行自动化评估：执行完整 Sloth 流水线，采集多维度指标，输出评分报告。兼具回归测试（版本间能力不退化）和能力基准（跟踪评分趋势）双重用途。

设计理念参考 GAIA（难度分级、真实任务）和 SWE-bench（自动验证、可复现）。

## 已实现

- `tests/` — 60+ 测试文件（对 App 自身的单元/集成测试，不属于 eval）
- `evals/` — 目录结构存在

## 核心设计

### 架构

```
evals/
├── tasks.yaml          # 任务索引（元数据 + 预期指标）
├── plans/              # 每个 task 的 Plan 文件
├── runner.py           # 执行引擎：跑 Sloth 流水线 + 采集指标
├── scoring.py          # 评分模块：四维度加权打分
├── models.py           # 数据模型：EvalTask, EvalResult, ScoreBreakdown
├── results/            # 评测结果（按版本存储 JSON）
└── __init__.py
```

### 执行流程

1. 读取 `tasks.yaml`，按 level/task 过滤
2. 对每个 task：读取 plan.md → 调用 Sloth 流水线（真实 LLM）→ 采集指标
3. 通过 HookManager 在 gate.pass/fail、model.end、run.end 时采集原始数据
4. 调用 scoring 计算四维度分数
5. 汇总为 EvalReport，写入 `evals/results/{version}.json`

### Task Schema

```yaml
eval_tasks:
  - name: crud-api
    description: Create a REST CRUD API
    difficulty: 1                    # L1 / L2 / L3
    plan: evals/plans/crud-api.md
    expected:
      gate1_pass: true               # lint + type check
      gate2_pass: true               # test + coverage
      gate3_pass: true               # smoke test
      min_files: 4
      min_coverage: 0.80
      lint_errors: 0
      max_tokens: 50000
      max_retries: 3
      max_duration_sec: 300
      has_deploy_artifacts: false     # L3 才需要
```

### 难度分级

| Level | 描述 | Pipeline 深度 | 典型 task |
|-------|------|--------------|-----------|
| L1 | 单文件/单模块 | Builder → Gate1 | 脚本、CLI 工具 |
| L2 | 多模块 CRUD | Builder → Reviewer → Gate2 | API 服务、数据处理 |
| L3 | 全栈应用 | 完整流水线 | 前后端 + 部署配置 |

### 评分模型

**每个 task 总分归一化到 100**，保证不同 level 可横向对比。

#### 正确性（基础权重 40%）

Gate 得分 = 40 × (实际通过 Gate 数 / 该 level 最大 Gate 数)：
- L1 最大 Gate 数 = 1（Gate1），满通 = 40 分
- L2 最大 Gate 数 = 2（Gate1 + Gate2），满通 = 40 分
- L3 最大 Gate 数 = 3（Gate1 + Gate2 + Gate3），满通 = 40 分

#### 部署产物维度归一化

- **L3**：保持原始四维权重（正确性 40% + 产出质量 30% + 过程效率 20% + 部署产物 10%）
- **L1/L2**：部署产物维度不计，10% 均摊至其余三维
  - 正确性 44.4% / 产出质量 33.3% / 过程效率 22.2%

#### 评分摘要

| 维度 | L1/L2 权重 | L3 权重 | 计算方式 |
|------|-----------|---------|----------|
| 正确性 | 44.4% | 40% | Gate 通过率（见上方归一化公式）|
| 产出质量 | 33.3% | 30% | 文件数、覆盖率、lint 各子项达标比例 |
| 过程效率 | 22.2% | 20% | 未超 token/重试/时长上限 = 满分，超限按比例扣 |
| 部署产物 | 不计 | 10% | DeployArtifactChecker 检查 Dockerfile / docker-compose |

等级标准：
- A (90+) — 全部 Gate 通过，产出质量高，效率好
- B (75+) — 核心 Gate 通过，有小瑕疵
- C (60+) — 基本能跑通，但有明显问题
- D (<60) — 流水线未跑通或产出质量差

### 结果存储

`evals/results/{version}.json` 结构：

```json
{
  "version": "v0.6.0",
  "timestamp": "2026-05-02T10:30:00Z",
  "summary": {
    "total_tasks": 5,
    "passed": 4,
    "failed": 1,
    "avg_score": 82.5,
    "grade": "B"
  },
  "tasks": [
    {
      "name": "crud-api",
      "difficulty": 1,
      "score": { "correctness": 40, "quality": 28, "efficiency": 18, "deploy": 0, "total": 86, "grade": "A" },
      "metrics": { "gates": {}, "files_created": 5, "coverage": 0.85, "tokens_used": 32000, "retries": 1, "duration_sec": 120 },
      "error": null
    }
  ],
  "dimensions": { "avg_correctness": 38.0, "avg_quality": 25.5, "avg_efficiency": 16.0, "avg_deploy": 3.0 }
}
```

### Runner 关键设计

- 复用 `sloth_agent.core.runner.Runner`，不重写流水线
- 通过 HookManager 注入 hook 采集指标（`gate.pass/fail`、`model.end`、`run.end`）
- **工作区隔离**：每个 task 在 `evals/workspaces/{task_name}_{timestamp}/` 独立目录运行，任务结束后清理，防止任务间文件污染
- **超时实现**：`concurrent.futures.ThreadPoolExecutor` 包装 `Runner.run()`，`future.result(timeout=max_duration_sec)` 捕获 `TimeoutError` 后判 D（跨平台，不用 SIGALRM）
- 单 task 失败/超时不阻塞其他 task 继续执行
- **L3 部署产物检查**：专用 `DeployArtifactChecker`，检查 Dockerfile / docker-compose.yml 存在且可解析；不复用 Gate3（Gate3 接口接收 `deploy_result` dict，语义不同）

### CLI 入口

```bash
sloth eval run                    # 跑全部 task
sloth eval run --level 1          # 只跑 L1
sloth eval run --task crud-api    # 跑单个 task
sloth eval report v0.6.0          # 查看某次结果
sloth eval compare v0.5.0 v0.6.0  # 对比两个版本
```

## 运行约束

- eval 只在大版本时运行，使用真实 LLM
- 不真正部署，只检查部署产物（Dockerfile、docker-compose 等）
- 结果按版本号存储，支持跨版本对比
- 部署评测只在 L3 任务中启用

## 待实现

- [ ] models.py — 数据模型
- [ ] scoring.py — 评分模块
- [ ] runner.py — 重写为流水线级执行
- [ ] CLI 入口集成
- [ ] L1/L2/L3 任务库（6 个初始任务）
- [ ] 单元测试
