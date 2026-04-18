# 评估框架（Eval）设计规格

> 版本: v1.0.0
> 日期: 2026-04-17
> 状态: v0.1.0 已实现基础框架
> v0.1.0 实现状态: EvalRunner + SmokeTest + 标准任务集已实现，189 tests pass
>   - 实现文件: `evals/runner.py`, `evals/smoke_test.py`, `evals/tasks.yaml`
>   - 测试覆盖: `evals/test_runner.py`, `evals/test_smoke.py`

---

## 1. 问题

没有评估就没有改进基线。v1.0 需要内置轻量级 eval 框架，用于：
1. 衡量 Agent 执行质量
2. 验证流水线功能完整性（smoke test）
3. 回归检测（每次架构变更后跑一遍）

---

## 2. 评估维度

| 维度 | 指标 | 采集方式 | 目标 |
|------|------|---------|------|
| **成功率** | 任务完成率 | 门控通过/失败记录 | ≥ 80% |
| **质量** | lint 通过率、test coverage | 门控输出 | lint 100%, coverage ≥ 80% |
| **效率** | 总 token 消耗、总执行时间、重试次数 | Agent 执行日志 | 逐版本下降 |
| **审查独立性** | Reviewer blocking issues 数量 | ReviewerOutput | > 0 表示 Reviewer 有价值 |
| **自修复率** | Builder 自动修复成功率 | 门控+重试记录 | ≥ 60% |

---

## 3. 标准任务集（Eval Suite）

定义 4 个最小可执行 eval 任务：

```yaml
eval_tasks:
  - name: "create-crud-api"
    plan: "evals/plans/crud-api.md"
    expected:
      files_created: 4
      tests_pass: true
      coverage_min: 0.80

  - name: "fix-type-error"
    plan: "evals/plans/fix-type-error.md"
    expected:
      type_check: true
      tests_pass: true
      retries_max: 2

  - name: "add-unit-tests"
    plan: "evals/plans/add-tests.md"
    expected:
      coverage_delta: 0.15
      tests_pass: true

  - name: "refactor-module"
    plan: "evals/plans/refactor.md"
    expected:
      tests_pass: true
      no_new_lint_errors: true
```

---

## 4. Smoke Test

v1.0 smoke test 用 mock LLM 跑通整个流水线骨架，不依赖真实模型调用：

1. 输入最小 Plan → Builder 解析成功
2. Builder 产出 BuilderOutput
3. Reviewer 接收并产出 ReviewerOutput
4. Gate1/Gate2/Gate3 全部通过（mock）
5. Deployer 部署成功

**验收**: smoke test 可复现，证明流水线骨架完整。

---

## 5. 评估产出

每次 eval 运行后生成报告：

```
memory/evals/
├── {date}-{eval_id}/
│   ├── summary.json        # 总分 + 各维度得分
│   ├── tasks/
│   │   ├── create-crud-api.json
│   │   └── ...
│   └── comparison.json     # 与上次 eval 的对比（回归检测）
```

---

## 6. CLI 入口

```bash
sloth eval                          # 跑全量 eval suite
sloth eval --task fix-type-error    # 跑单个任务
sloth eval --compare                # 对比最近两次 eval 结果
```

---

## 7. 模块定义

### 7.1 EvalRunner

**文件**: `evals/runner.py`（新建）

```python
class EvalRunner:
    """运行 eval suite 并收集结果。"""

    def run_all(self, config: Config) -> EvalReport: ...
    def run_task(self, task_name: str, config: Config) -> TaskResult: ...
    def run_smoke_test(self, config: Config) -> SmokeTestResult: ...
```

---

## 8. 文件清单

| 文件 | 说明 |
|------|------|
| `evals/runner.py` | Eval runner |
| `evals/smoke_test.py` | Smoke test |
| `evals/plans/crud-api.md` | Eval plan |
| `evals/plans/fix-type-error.md` | Eval plan |
| `evals/plans/add-tests.md` | Eval plan |
| `evals/plans/refactor.md` | Eval plan |
| `evals/tasks.yaml` | Eval 任务定义 |

---

## 9. 测试策略

| 测试 | 说明 |
|------|------|
| `test_smoke_test_pipeline` | mock LLM 跑通完整流水线 |
| `test_eval_runner_single_task` | 单个 eval task 可执行并产出结果 |

---

*规格版本: v1.0.0*
*创建日期: 2026-04-17*
