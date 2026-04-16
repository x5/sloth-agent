# v1.0 Task 5: Reviewer Agent Runtime — Implementation Plan

> Spec 来源: `docs/specs/00000000-00-architecture-overview.md` §5.1, §6.0; `docs/specs/20260416-01-phase-role-architecture-spec.md`
> Plan 文件: `docs/plans/20260417-v10-reviewer-agent-implementation-plan.md`
> 对应 TODO: `Task 5: Reviewer Agent Runtime`
> 依赖: Task 4 (Gate & Handoff)

---

## 1. 目标

实现 Reviewer Agent：读取 BuilderOutput，独立审查代码质量/安全/性能，产出 `ReviewerOutput` 结构化交接物。必须使用不同于 Builder 的模型路由（qwen3.6-plus 或 claude）。

---

## 2. 步骤（按顺序执行）

### 步骤 5.1: 定义 `ReviewerAgent` 核心类

**文件**: `src/sloth_agent/agents/reviewer.py`（新建）

**内容** (spec §5.1, §6.0):

```python
class ReviewerAgent:
    def __init__(self, config: Config, tool_orchestrator: ToolOrchestrator, llm_provider):
        self.config = config
        self.tool_orchestrator = tool_orchestrator
        self.llm = llm_provider  # qwen3.6-plus 或 claude（必须不同于 Builder）

    async def review(self, builder_output: BuilderOutput, workspace: str) -> ReviewerOutput:
        # 1. 读取变更文件
        changed_content = self._read_changed_files(builder_output.changed_files, workspace)

        # 2. 构建 review prompt
        prompt = self._build_review_prompt(builder_output, changed_content)

        # 3. 调 LLM 生成审查结果
        review_result = await self.llm.generate(prompt, output_schema=ReviewerOutput)

        # 4. 返回结构化结果
        return ReviewerOutput(
            approved=len(review_result.blocking_issues) == 0,
            branch=builder_output.branch,
            blocking_issues=review_result.blocking_issues,
            suggestions=review_result.suggestions,
        )
```

**验收**: `ReviewerAgent.review()` 可接收 BuilderOutput，返回 ReviewerOutput。

---

### 步骤 5.2: 实现 Review Prompt

**文件**: `src/sloth_agent/agents/reviewer.py`（续）

Prompt 必须包含：
- BuilderOutput 的 diff_summary（确定性数据）
- 变更文件的完整内容
- 审查维度：代码质量、安全性、性能、可维护性
- 输出格式要求：blocking_issues（必须修复才能继续）、suggestions（非阻塞）

**验收**: prompt 模板包含所有审查维度，输出可解析为 `ReviewerOutput`。

---

### 步骤 5.3: 集成 Reviewer 到 `Runner`

**文件**: `src/sloth_agent/core/runner.py`（修改）

- `Runner.prepare()` 支持设置 `current_agent="reviewer"`, `current_phase="review"`
- `Runner.think()` 在 reviewer phase 调用 ReviewerAgent
- `Runner.resolve()` 处理 reviewer 的 `phase_handoff`（Reviewer → Deployer）

**验收**: Runner 能以 reviewer 身份跑完一个 turn cycle。

---

### 步骤 5.4: 补充 reviewer 有效性测试

**文件**: `tests/agents/test_reviewer.py`（新建）

最小评估用例：
- 输入一段有明显 bug 的代码，验证 ReviewerOutput 中 blocking_issues 非空
- 输入一段干净的代码，验证 approved=True

**验收**: 测试可复现，证明 Reviewer 有独立审查能力。

---

## 3. 文件清单

| 文件 | 动作 |
|------|------|
| `src/sloth_agent/agents/reviewer.py` | **新建** |
| `src/sloth_agent/core/runner.py` | **修改** — 集成 Reviewer phase |
| `tests/agents/test_reviewer.py` | **新建** |

---

## 5. 验收标准

- [ ] `ReviewerAgent.review()` 可接收 BuilderOutput 并返回 ReviewerOutput
- [ ] Reviewer 使用不同于 Builder 的模型
- [ ] Review Prompt 包含 diff_summary + 变更内容 + 审查维度
- [ ] Runner 能以 reviewer 身份跑完整 turn cycle
- [ ] reviewer 有效性测试通过（能发现 bug 也能放行好代码）

---

*Plan 版本: v1.0.0 | 创建: 2026-04-17*
