# 20260417-21-eval-framework-implementation-plan.md

> Spec 来源: `docs/specs/20260417-21-eval-framework-spec.md`（模块 21）
> Plan 文件: `docs/plans/20260417-21-eval-framework-implementation-plan.md`
> 对应 Arch: `docs/specs/00000000-00-architecture-overview.md` §11.5
> v0.1.0 实现状态: EvalRunner + SmokeTest 已实现 (2 tests pass), 189 tests 全量通过
> v0.1.0 实现文件: `evals/runner.py`, `evals/smoke_test.py`, `evals/tasks.yaml`

---

## 1. 目标

实现最小 eval suite + smoke test，验证流水线功能完整性并建立评估基线。

---

## 2. 步骤

### 步骤 1: 实现 Eval Runner

**文件**: `evals/runner.py`（新建）

**内容** (spec §3, §7):

```python
class EvalRunner:
    """运行 eval suite 并收集结果。"""

    def run_all(self, config) -> EvalReport:
        """跑全量 eval suite。"""

    def run_task(self, task_name: str, config) -> TaskResult:
        """运行单个 eval task。"""
```

### 步骤 2: 实现 Smoke Test

**文件**: `evals/smoke_test.py`（新建）

**内容** (spec §4):

用 mock LLM 跑通完整流水线：
1. Builder 解析最小 Plan → BuilderOutput
2. Reviewer 接收 → ReviewerOutput
3. Gate1/2/3 mock 通过
4. Deployer 部署成功

### 步骤 3: 创建 Eval Plans

**文件**: `evals/plans/`（新建 4 个文件）

- `crud-api.md` — 创建 CRUD API 的 Plan
- `fix-type-error.md` — 修复类型错误的 Plan
- `add-tests.md` — 添加单元测试的 Plan
- `refactor.md` — 重构模块的 Plan

### 步骤 4: 创建 Eval Task 定义

**文件**: `evals/tasks.yaml`（新建）

```yaml
eval_tasks:
  - name: "create-crud-api"
    plan: "evals/plans/crud-api.md"
    expected: { files_created: 4, tests_pass: true, coverage_min: 0.80 }
  - name: "fix-type-error"
    plan: "evals/plans/fix-type-error.md"
    expected: { type_check: true, tests_pass: true, retries_max: 2 }
  - name: "add-unit-tests"
    plan: "evals/plans/add-tests.md"
    expected: { coverage_delta: 0.15, tests_pass: true }
  - name: "refactor-module"
    plan: "evals/plans/refactor.md"
    expected: { tests_pass: true, no_new_lint_errors: true }
```

### 步骤 5: 编写单元测试

| 文件 | 覆盖 | 测试数 |
|------|------|--------|
| `evals/test_smoke.py` | smoke test 可复现 | 1 |
| `evals/test_runner.py` | eval runner 单 task 执行 | 1 |

---

## 3. 文件清单

| 文件 | 动作 |
|------|------|
| `evals/runner.py` | **新建** |
| `evals/smoke_test.py` | **新建** |
| `evals/tasks.yaml` | **新建** |
| `evals/plans/crud-api.md` | **新建** |
| `evals/plans/fix-type-error.md` | **新建** |
| `evals/plans/add-tests.md` | **新建** |
| `evals/plans/refactor.md` | **新建** |
| `evals/test_smoke.py` | **新建** |
| `evals/test_runner.py` | **新建** |

---

## 4. 验收标准

- [ ] `sloth eval` 可运行全量 eval suite
- [ ] smoke test 用 mock LLM 跑通完整流水线
- [ ] 每个 eval task 有预期结果定义
- [ ] 所有测试通过（共 2 tests）

---

*Plan 版本: v1.0.0 | 创建: 2026-04-17*
