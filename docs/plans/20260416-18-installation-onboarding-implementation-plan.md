# 20260416-18-installation-onboarding-implementation-plan.md

> Spec 来源: `docs/specs/20260416-18-installation-onboarding-spec.md`
> Plan 文件: `docs/plans/20260416-18-installation-onboarding-implementation-plan.md`
> 对应 Arch: `docs/specs/00000000-00-architecture-overview.md` §9.0

---

## 1. 目标

实现 `sloth run` CLI 入口，调用 ProductOrchestrator → Runner → 完整自主流水线。

---

## 2. 步骤

### 步骤 1: 实现 `sloth run` 命令

**文件**: `src/sloth_agent/cli/app.py`（修改）

**内容** (spec §9):

```python
@app.command()
def run(plan: str = typer.Argument(..., help="Plan 文件路径")):
    """执行自主流水线: Builder → Reviewer → Deployer"""
    config = load_config()
    orchestrator = ProductOrchestrator(config)
    runner = Runner(config, orchestrator.tool_registry)

    plan_text = Path(plan).read_text()
    state = orchestrator.create_run_state()
    state.current_agent = "builder"
    state.current_phase = "plan_parsing"

    final_state = runner.run(state)

    if final_state.phase == "completed":
        console.print("[green]流水线执行成功![/green]")
    else:
        console.print(f"[red]流水线失败: {final_state.errors}[/red]")
```

**验收**: `sloth run path/to/plan.md` 可调用完整流水线。

---

### 步骤 2: 编写单元测试

| 文件 | 覆盖 | 测试数 |
|------|------|--------|
| `tests/cli/test_app.py` | `sloth run` 命令调用链路（mock） | 1 |

**具体测试**:

```
test_app.py:
  - test_run_command_calls_pipeline: mock Orchestrator 和 Runner，验证 run 命令正确调用
```

---

## 3. 文件清单

| 文件 | 动作 |
|------|------|
| `src/sloth_agent/cli/app.py` | **修改** — run 命令改为调用 Runner |
| `tests/cli/test_app.py` | **新建** |

---

## 4. 验收标准

- [ ] `sloth run <plan>` 可调用 ProductOrchestrator → Runner
- [ ] mock 测试验证命令正确传递参数给 pipeline
- [ ] 所有测试通过（共 1 test）

---

*Plan 版本: v1.0.0 | 创建: 2026-04-17*
