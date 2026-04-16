# v1.0 Task 6: Deployer Agent Runtime — Implementation Plan

> Spec 来源: `docs/specs/00000000-00-architecture-overview.md` §5.1, §6.0
> Plan 文件: `docs/plans/20260417-v10-deployer-agent-implementation-plan.md`
> 对应 TODO: `Task 6: Deployer Agent Runtime`
> 依赖: Task 5 (Reviewer Agent)

---

## 1. 目标

实现 Deployer Agent：接收 ReviewerOutput，执行部署脚本、运行 smoke test、验证上线结果，支持 Gate3 失败后的自动回滚。

---

## 2. 步骤（按顺序执行）

### 步骤 6.1: 定义 `DeployerAgent` 核心类

**文件**: `src/sloth_agent/agents/deployer.py`（新建）

**内容** (spec §5.1, §6.0):

```python
class DeployResult(BaseModel):
    success: bool
    branch: str
    deploy_log: str
    smoke_test_passed: bool
    smoke_test_output: str
    rollback_performed: bool = False

class DeployerAgent:
    def __init__(self, config: Config, tool_orchestrator: ToolOrchestrator, llm_provider):
        self.config = config
        self.tool_orchestrator = tool_orchestrator
        self.llm = llm_provider  # deepseek-v3.2

    async def deploy(self, reviewer_output: ReviewerOutput, workspace: str) -> DeployResult:
        # 1. 执行部署脚本
        deploy_log = self._run_deploy_script(workspace)

        # 2. 运行 smoke test
        smoke_result = self._run_smoke_test(workspace)

        # 3. Gate3 检查
        gate3 = Gate3(self.config.gates.deploy_verify)
        gate_result = gate3.check({"smoke_test_passed": smoke_result.passed, "output": smoke_result.output})

        if not gate_result.passed and self.config.gates.deploy_verify.auto_rollback:
            rollback_log = self._rollback(workspace)
            return DeployResult(
                success=False,
                branch=reviewer_output.branch,
                deploy_log=deploy_log,
                smoke_test_passed=False,
                smoke_test_output=smoke_result.output,
                rollback_performed=True,
            )

        return DeployResult(
            success=True,
            branch=reviewer_output.branch,
            deploy_log=deploy_log,
            smoke_test_passed=smoke_result.passed,
            smoke_test_output=smoke_result.output,
        )
```

**验收**: `DeployerAgent.deploy()` 可接收 ReviewerOutput，返回 DeployResult。

---

### 步骤 6.2: 实现部署脚本执行

**文件**: `src/sloth_agent/agents/deployer.py`（续）

部署脚本发现逻辑：
1. 检查 `deploy.sh` 或 `deploy/` 目录
2. 如果没有部署脚本，跳过部署步骤（仅记录）
3. 如果有，通过 `run_command` 工具执行

**验收**: 有部署脚本时执行，无脚本时优雅跳过。

---

### 步骤 6.3: 实现 smoke test

**文件**: `src/sloth_agent/agents/deployer.py`（续）

smoke test 执行逻辑：
1. 检查 `smoke_test.sh` 或 `tests/smoke/` 目录
2. 如果没有 smoke test，跳过（记录 warning）
3. 如果有，执行并返回 pass/fail

**验收**: 有 smoke test 时执行，无 test 时优雅跳过。

---

### 步骤 6.4: 实现自动回滚

**文件**: `src/sloth_agent/agents/deployer.py`（续）

Gate3 失败时：
1. 通过 git tag 找到部署前的 checkpoint
2. 执行 `git reset --hard` 回滚
3. 记录回滚日志

**验收**: Gate3 失败时正确回滚到部署前状态。

---

### 步骤 6.5: 集成 Deployer 到 `Runner`

**文件**: `src/sloth_agent/core/runner.py`（修改）

- `Runner.prepare()` 支持 `current_agent="deployer"`, `current_phase="deploy"`
- `Runner.resolve()` 处理 deployer 的 `final_output`（部署成功 → run 完成）

**验收**: Runner 能以 deployer 身份跑完一个 turn cycle。

---

### 步骤 6.6: 补充 end-to-end 部署阶段测试

**文件**: `tests/agents/test_deployer.py`（新建）

测试用例：
- 有部署脚本 + smoke test 通过 → DeployResult.success=True
- 有部署脚本 + smoke test 失败 → DeployResult.success=False + rollback_performed=True
- 无部署脚本 → 优雅跳过

---

## 3. 文件清单

| 文件 | 动作 |
|------|------|
| `src/sloth_agent/agents/deployer.py` | **新建** |
| `src/sloth_agent/core/runner.py` | **修改** — 集成 Deployer phase |
| `tests/agents/test_deployer.py` | **新建** |

---

## 5. 验收标准

- [ ] `DeployerAgent.deploy()` 可接收 ReviewerOutput 并返回 DeployResult
- [ ] 部署脚本存在时执行，不存在时优雅跳过
- [ ] smoke test 存在时执行，不存在时优雅跳过
- [ ] Gate3 失败时自动回滚到部署前状态
- [ ] Runner 能以 deployer 身份跑完整 turn cycle
- [ ] end-to-end 部署测试通过

---

*Plan 版本: v1.0.0 | 创建: 2026-04-17*
