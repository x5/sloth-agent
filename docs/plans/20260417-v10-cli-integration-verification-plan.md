# v1.0 Task 8: CLI 集成与 v1.0 验证闭环 — Implementation Plan

> Spec 来源: `docs/specs/00000000-00-architecture-overview.md` §6.0, §7.3, §9.0, §11.0, §11.5
> Plan 文件: `docs/plans/20260417-v10-cli-integration-verification-plan.md`
> 对应 TODO: `Task 8: CLI 集成与 v1.0 验证闭环`
> 依赖: Task 7 (FS Memory / Checkpoint / Skill Loading)

---

## 1. 目标

打通 `sloth run` 主路径，输入 Plan 后可跑完整 Builder → Gate1 → Reviewer → Gate2 → Deployer → Gate3 流水线；配置阶段级模型路由；增加最小 eval/smoke 场景验证。

---

## 2. 步骤（按顺序执行）

### 步骤 8.1: 实现 LLM Provider 路由

**文件**: `src/sloth_agent/providers/llm_router.py`（新建或扩展现有）

**内容** (spec §7.3, §11.0):

v1.0 阶段级 LLM 路由配置：

```yaml
agents:
  builder:
    stages:
      plan_parsing: { provider: "deepseek", model: "deepseek-r1-0528" }
      coding:       { provider: "deepseek", model: "deepseek-v3.2" }
      debugging:    { provider: "deepseek", model: "deepseek-r1-0528" }
  reviewer:
    stages:
      review: { provider: "qwen", model: "qwen3.6-plus" }
  deployer:
    stages:
      deploy: { provider: "deepseek", model: "deepseek-v3.2" }
```

```python
class LLMRouter:
    def __init__(self, config: Config):
        self.providers = {}  # provider_name -> LLMProvider instance
        self.routes = config.agents  # 从配置加载

    def get_model(self, agent: str, stage: str) -> LLMProvider:
        route = self.routes[agent]["stages"][stage]
        return self.providers[route["provider"]]
```

每个 Provider 需要实现统一的 `generate()` 接口（兼容 OpenAI 格式）。

**验收**: 给定 agent + stage，能返回正确的模型实例。

---

### 步骤 8.2: 改造 `sloth run` 命令

**文件**: `src/sloth_agent/cli/app.py`（修改）

**内容** (spec §9.0 CLI 入口):

当前 `run` 命令调用 `AgentEvolve.run()`（昼夜循环），需要改为：

```python
@app.command()
def run(plan: str = typer.Argument(..., help="Plan 文件路径")):
    from sloth_agent.core.orchestrator import ProductOrchestrator
    from sloth_agent.core.runner import Runner

    config = load_config()
    orchestrator = ProductOrchestrator(config)
    runner = Runner(config, orchestrator.tool_registry, ...)

    # 1. 加载 Plan
    plan_text = Path(plan).read_text()

    # 2. 创建 RunState
    state = orchestrator.create_run_state(run_id=uuid4().hex)

    # 3. 设置 Builder phase
    state.current_agent = "builder"
    state.current_phase = "plan_parsing"

    # 4. 跑完整流水线
    final_state = runner.run(state)

    # 5. 输出结果
    if final_state.phase == "completed":
        console.print("[green]流水线执行成功![/green]")
    else:
        console.print(f"[red]流水线失败: {final_state.errors}[/red]")
```

**验收**: `sloth run path/to/plan.md` 可调用 ProductOrchestrator → Runner → 完整流水线。

---

### 步骤 8.3: 实现最小 eval suite

**文件**: `evals/`（新建）

**内容** (spec §11.5 Eval Framework):

v1.0 最小 eval 任务集：

```
evals/
├── plans/
│   ├── crud-api.md           # 创建 CRUD API 的 Plan
│   ├── fix-type-error.md     # 修复类型错误的 Plan
│   ├── add-tests.md          # 添加单元测试的 Plan
│   └── refactor-module.md    # 重构模块的 Plan
└── runner.py                 # Eval runner
```

每个 eval task 包含预期结果：

```yaml
eval_tasks:
  - name: "create-crud-api"
    plan: "evals/plans/crud-api.md"
    expected:
      files_created: 4
      tests_pass: true
      coverage_min: 0.80
```

**验收**: `sloth eval` 可跑全量 eval suite，输出各维度得分。

---

### 步骤 8.4: 实现 smoke test 场景

**文件**: `evals/smoke_test.py`（新建）

smoke test 验证：
1. 输入最小 Plan → Builder 解析成功
2. Builder 产出 BuilderOutput
3. Reviewer 接收并产出 ReviewerOutput
4. Gate1/Gate2/Gate3 全部通过（mock）
5. Deployer 部署成功

整个链路用 mock LLM 跑通，不依赖真实模型调用。

**验收**: smoke test 可复现，证明流水线骨架完整。

---

### 步骤 8.5: 更新 README / 使用文档

**文件**: `README.md`（修改）

添加 v1.0 使用说明：
- 安装步骤
- `sloth run <plan>` 用法
- 配置 LLM API key
- 目录结构说明
- 已知限制

**验收**: README 包含 v1.0 完整使用指南。

---

## 3. 文件清单

| 文件 | 动作 |
|------|------|
| `src/sloth_agent/providers/llm_router.py` | **新建/重构** |
| `src/sloth_agent/cli/app.py` | **修改** — run 命令改为调用 Runner |
| `evals/plans/crud-api.md` | **新建** |
| `evals/plans/fix-type-error.md` | **新建** |
| `evals/plans/add-tests.md` | **新建** |
| `evals/plans/refactor-module.md` | **新建** |
| `evals/runner.py` | **新建** |
| `evals/smoke_test.py` | **新建** |
| `README.md` | **修改** — 添加 v1.0 使用说明 |

---

## 5. 验收标准

- [ ] `sloth run <plan>` 可调用 ProductOrchestrator → Runner → 完整流水线
- [ ] LLM Router 按 agent + stage 返回正确的模型实例
- [ ] 最小 eval suite 可运行，输出各维度得分
- [ ] smoke test 可复现，证明流水线骨架完整
- [ ] README 包含 v1.0 完整使用指南

---

*Plan 版本: v1.0.0 | 创建: 2026-04-17*
