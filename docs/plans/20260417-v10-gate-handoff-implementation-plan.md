# v1.0 Task 4: Gate 机制与 Phase Handoff — Implementation Plan

> Spec 来源: `docs/specs/00000000-00-architecture-overview.md` §5.1.1.1, §5.1.3, §6.0
> Plan 文件: `docs/plans/20260417-v10-gate-handoff-implementation-plan.md`
> 对应 TODO: `Task 4: Gate 机制与 Phase Handoff`
> 依赖: Task 3 (Builder Agent)

---

## 1. 目标

实现 3 个自动门控（Gate1/Gate2/Gate3）和 `phase_handoff` 语义，打通 Builder → Reviewer → Deployer 的结构化交接。

---

## 2. 步骤（按顺序执行）

### 步骤 4.1: 实现 Gate 数据模型和接口

**文件**: `src/sloth_agent/core/gates.py`（新建，替换或扩展 `core/orchestrator.py` 中的 gate 逻辑）

**内容** (spec §5.1.3):

```python
class GateResult(BaseModel):
    passed: bool
    passed_checks: list[str]
    failed_checks: list[str]
    raw_output: str = ""

class Gate1Config(BaseModel):
    """Gate1: Builder → Reviewer (构建质量)"""
    lint_must_pass: bool = True
    type_check_must_pass: bool = True
    tests_must_pass: bool = True
    max_retries: int = 3

class Gate2Config(BaseModel):
    """Gate2: Reviewer → Deployer (审查质量)"""
    no_blocking_issues: bool = True
    min_coverage: float = 0.80

class Gate3Config(BaseModel):
    """Gate3: Deployer → Done (部署验证)"""
    smoke_test_must_pass: bool = True
    auto_rollback: bool = True
```

**验收**: 所有 Gate 模型可序列化。

---

### 步骤 4.2: 实现 Gate1（构建质量门控）

**文件**: `src/sloth_agent/core/gates.py`（续）

**内容** (spec §5.1.3):

```python
class Gate1:
    """Builder → Reviewer: lint + type check + tests pass"""

    def __init__(self, config: Gate1Config):
        self.config = config

    def check(self, branch: str, workspace: str) -> GateResult:
        passed = []
        failed = []
        raw = ""

        # lint
        if self.config.lint_must_pass:
            r = self._run_lint(workspace)
            if r.passed: passed.append("lint")
            else: failed.append("lint"); raw += r.output

        # type check
        if self.config.type_check_must_pass:
            r = self._run_type_check(workspace)
            if r.passed: passed.append("type_check")
            else: failed.append("type_check"); raw += r.output

        # tests
        if self.config.tests_must_pass:
            r = self._run_tests(workspace)
            if r.passed: passed.append("tests")
            else: failed.append("tests"); raw += r.output

        return GateResult(
            passed=len(failed) == 0,
            passed_checks=passed,
            failed_checks=failed,
            raw_output=raw,
        )
```

lint 工具: `ruff check` 或 `flake8`
type check 工具: `mypy` 或 `pyright`
tests 工具: `pytest`

**验收**: Gate1 对通过和失败场景各有正确返回值，raw_output 包含完整错误信息。

---

### 步骤 4.3: 实现 Gate2（审查质量门控）

**文件**: `src/sloth_agent/core/gates.py`（续）

```python
class Gate2:
    """Reviewer → Deployer: 无 blocking issues + coverage ≥ 阈值"""

    def __init__(self, config: Gate2Config):
        self.config = config

    def check(self, reviewer_output: ReviewerOutput, coverage: float) -> GateResult:
        passed = []
        failed = []

        if self.config.no_blocking_issues:
            if not reviewer_output.blocking_issues:
                passed.append("no_blocking_issues")
            else:
                failed.append(f"blocking_issues: {reviewer_output.blocking_issues}")

        if coverage >= self.config.min_coverage:
            passed.append(f"coverage({coverage:.0%} ≥ {self.config.min_coverage:.0%})")
        else:
            failed.append(f"coverage({coverage:.0%} < {self.config.min_coverage:.0%})")

        return GateResult(passed=len(failed) == 0, passed_checks=passed, failed_checks=failed)
```

**验收**: blocking_issues 非空时失败，coverage 低于阈值时失败，两者都通过时放行。

---

### 步骤 4.4: 实现 Gate3（部署验证门控）

**文件**: `src/sloth_agent/core/gates.py`（续）

```python
class Gate3:
    """Deployer → Done: smoke test pass"""

    def __init__(self, config: Gate3Config):
        self.config = config

    def check(self, deploy_result: dict) -> GateResult:
        passed = deploy_result.get("smoke_test_passed", False)
        return GateResult(
            passed=passed,
            passed_checks=["smoke_test"] if passed else [],
            failed_checks=["smoke_test"] if not passed else [],
            raw_output=deploy_result.get("output", ""),
        )
```

**验收**: smoke test 通过时放行，失败时标记失败并保留 output。

---

### 步骤 4.5: 实现 `phase_handoff` 语义

**文件**: `src/sloth_agent/core/runner.py`（修改）

**内容** (spec §5.1.1.1):

在 `Runner.resolve()` 中处理 `phase_handoff`:

```python
def resolve(self, state: RunState, next_step: NextStep) -> RunState:
    match next_step.type:
        case "phase_handoff":
            state.current_agent = next_step.next_agent
            state.current_phase = next_step.next_phase
            state.handoff_payload = next_step.output  # BuilderOutput / ReviewerOutput
            state.turn = 0  # 新 phase 重置 turn 计数
            self.observe("handoff", {"from": ..., "to": next_step.next_agent})
```

与 `skill-as-tool` 的区分：
- `phase_handoff` → 更新 `current_agent` / `current_phase`，重置 turn
- `skill-as-tool` → 不更新 ownership，结果进入 `tool_history`，继续当前 turn

**验收**: handoff 后 `current_agent` / `current_phase` 正确更新，`handoff_payload` 保存结构化数据。

---

### 步骤 4.6: 打通 gate failure → retry / rollback / interrupt 流转

**文件**: `src/sloth_agent/core/runner.py`（修改）

**内容** (spec §7.1.1.2 gate failure 映射):

| gate 结果 | 映射到 NextStep |
|-----------|----------------|
| Gate1 失败 + 可修复 | `retry_same`（Builder 重试，最多 max_retries）|
| Gate1 失败 + 不可修复 | `retry_different` |
| Gate2 失败（blocking issues）| `retry_different`（打回 Builder）|
| Gate3 失败 | `retry_same`（smoke test 重试）或 `abort`（自动回滚）|

**验收**: Gate 失败不直接抛异常，而是返回 `NextStep` 让 Runner 循环决定下一步。

---

### 步骤 4.7: 编写单元测试

**文件**: `tests/core/test_gates.py`（新建）

| 测试用例 | 覆盖 |
|---------|------|
| `test_gate1_pass` | lint + type + tests 全部通过 |
| `test_gate1_lint_fail` | lint 失败时正确返回 |
| `test_gate1_test_fail` | 测试失败时正确返回 |
| `test_gate2_pass` | 无 blocking issues + coverage 达标 |
| `test_gate2_blocking_issues` | blocking issues 存在时失败 |
| `test_gate2_low_coverage` | coverage 低于阈值时失败 |
| `test_gate3_pass` | smoke test 通过 |
| `test_gate3_fail` | smoke test 失败 |
| `test_phase_handoff` | handoff 后 agent/phase 正确更新 |
| `test_gate_failure_to_retry` | gate 失败映射到 NextStep |

---

## 3. 文件清单

| 文件 | 动作 |
|------|------|
| `src/sloth_agent/core/gates.py` | **新建** |
| `src/sloth_agent/core/runner.py` | **修改** — phase_handoff 分支 + gate failure 流转 |
| `tests/core/test_gates.py` | **新建** |

---

## 5. 验收标准

- [ ] Gate1 可执行 lint + type check + tests 检查
- [ ] Gate2 可检查 blocking issues + coverage 阈值
- [ ] Gate3 可检查 smoke test 结果
- [ ] `phase_handoff` 正确更新 `current_agent` / `current_phase` / `handoff_payload`
- [ ] Gate 失败映射到 NextStep 而非抛异常
- [ ] 所有测试通过

---

*Plan 版本: v1.0.0 | 创建: 2026-04-17*
