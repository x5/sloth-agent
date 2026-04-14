# Sloth Agent 工作流工具与钩子规范

> 版本: v0.1.0
> 日期: 2026-04-15
> 参考: Superpowers Framework, Claude Code, Open Claw

---

## 1. 概述

本文档定义 Sloth Agent 每个工作流步骤中使用的工具、脚本和钩子（hooks），确保每个步骤都有可执行、可验证的保障机制。

### 1.1 设计原则

| 原则 | 说明 |
|------|------|
| **Evidence over claims** | 每个步骤必须有可验证的证据 |
| **Atomic commits** | 每个微任务单独提交 |
| **TDD Iron Law** | 没有失败测试就不能写生产代码 |
| **Hard Gates** | 关键步骤前必须通过审查 |

---

## 2. 工作流步骤工具映射

### 2.1 Step 1: Brainstorming（构思）

**目标**: 在写任何代码前，充分理解需求并设计解决方案

| 阶段动作 | 工具/命令 | 产出 |
|---------|----------|------|
| 探索上下文 | `Read`, `Glob`, `Grep` | 项目结构理解 |
| 收集需求 | `WebFetch` (外部参考) | 竞品/文档分析 |
| 记录问题 | `Write` (临时笔记) | 问题清单 |
| 提出方案 | LLM (Claude/GLM) | 2-3 个方案及权衡 |
| 撰写设计 | `Write` | `docs/specs/YYYYMMDD-*-design-spec.md` |
| 自我检查 | `grep -E "TBD\|TODO\|未完成"` | 无占位符验证 |

**Hooks**:
```yaml
pre_brainstorming:
  - check_workspace_exists: 验证工作区存在

post_brainstorming:
  - validate_design_spec: 验证设计文档格式
  - check_no_code_in_design: 确保设计文档无代码
```

### 2.2 Step 2: Writing Plans（写计划）

**目标**: 将设计分解为 2-5 分钟的微任务

| 阶段动作 | 工具/命令 | 产出 |
|---------|----------|------|
| 分解任务 | LLM (Claude) | 微任务列表 |
| 创建任务 | `TaskCreate` | 任务 ID |
| 验证覆盖 | `grep` + `Read` | Spec 覆盖检查 |
| 扫描占位符 | `grep -E "TBD\|TODO"` | 占位符检查 |
| 撰写计划 | `Write` | `docs/plans/YYYYMMDD-*-implementation-plan.md` |

**Scripts**:
```bash
# scripts/validate_plan.sh
#!/bin/bash
# 检查计划文档
# 1. 验证头部必须包含
# 2. 验证无占位符
# 3. 验证任务可执行
```

**Hooks**:
```yaml
pre_planning:
  - design_approved: 设计必须已审批

post_planning:
  - validate_plan_format: 验证计划格式
  - validate_task_breakdown: 验证任务分解粒度
  - update_todo_md: 更新 TODO.md
```

### 2.3 Step 3: Implementing（执行）

**目标**: TDD 驱动，每个任务遵循 RED-GREEN-REFACTOR

| 阶段动作 | 工具/命令 | 产出 |
|---------|----------|------|
| 编写测试 (RED) | `Write` | `tests/test_xxx.py` |
| 运行测试 | `Bash: pytest` | 测试失败输出 |
| 验证失败原因 | `Read` (测试输出) | 确认失败正确 |
| 写实现 (GREEN) | `Write`/`Edit` | `src/xxx.py` |
| 运行测试 | `Bash: pytest` | 测试通过输出 |
| 重构 (REFACTOR) | `Edit` | 优化代码 |
| Lint 检查 | `Bash: ruff` | 代码风格 |
| Type 检查 | `Bash: mypy` | 类型正确 |
| 提交代码 | `Bash: git commit` | 提交记录 |

**TDD Enforcer 规则**:
```python
THE_IRON_LAW = "没有失败的测试，就不能写任何生产代码"

class TDDEnforcer:
    def enforce_red(self, task):
        """RED: 必须先写失败测试"""
        test_file = self.write_test(task)
        result = run_pytest(test_file)
        if result.passed:
            raise TDDViolationError("测试必须失败!")
        return result

    def enforce_green(self, task):
        """GREEN: 写最小实现"""
        if not self.has_failing_test(task):
            raise TDDViolationError("没有失败测试!")
        impl_file = self.write_implementation(task)
        result = run_pytest(impl_file)
        if not result.passed:
            raise TDDViolationError("实现未能让测试通过!")
        return result
```

**Scripts**:
```bash
# scripts/run_tdd_cycle.sh
#!/bin/bash
# 运行完整 TDD 周期
# 1. 运行测试 (应该 RED)
# 2. 运行实现
# 3. 运行测试 (应该 GREEN)
# 4. 运行 lint/type/coverage
```

**Hooks**:
```yaml
pre_implementing:
  - task_approved: 任务必须已分解并审批
  - test_exists: 验证测试文件存在

post_implementing:
  - all_tests_pass: 所有测试必须通过
  - lint_clean: ruff 0 errors
  - type_clean: mypy 0 errors
  - coverage_threshold: >= 80%
  - git_commit: 自动提交
```

### 2.4 Step 4: Verifying（验证）

**目标**: 证据优于声明，4 步验证门控

| 阶段动作 | 工具/命令 | 产出 |
|---------|----------|------|
| Identify | 确定验证命令 | 验证命令列表 |
| Run | `Bash` | 完整输出 |
| Read | `Read` | 检查退出码和输出 |
| Verify | 分析结果 | pass/fail |

**验证门控清单**:

```yaml
verify_tests:
  command: "pytest --tb=short -v"
  check:
    - exit_code: 0
    - failures: 0
    - output_contains: "X passed"

verify_build:
  command: "cargo build 2>&1"  # Rust 项目
  check:
    - exit_code: 0

verify_coverage:
  command: "pytest --cov=src --cov-report=term"
  check:
    - coverage_percent: ">= 80"

verify_lint:
  command: "ruff check src/"
  check:
    - exit_code: 0

verify_types:
  command: "mypy src/"
  check:
    - exit_code: 0
```

**Red Flags（立即停止）**:
- 使用 "应该"、"可能"、"似乎" 等词
- 在验证前表达满足感（"完成了！"）
- 没有验证就 commit/push/PR
- 依赖部分验证

**Scripts**:
```bash
# scripts/verify_gate.sh
#!/bin/bash
# 4 步验证门控
# 1. Identify - 确定验证命令
# 2. Run - 完整重新运行
# 3. Read - 检查退出码
# 4. Verify - 验证通过/失败
```

### 2.5 Step 5: Code Review（代码审查）

**目标**: Spec 合规性检查优先于代码质量

| 阶段动作 | 工具/命令 | 产出 |
|---------|----------|------|
| Spec 合规检查 | `Read` + `Grep` | 合规性报告 |
| 代码质量检查 | `Bash: ruff`, `mypy` | 质量报告 |
| 安全性检查 | `Bash: ruff check --select=security` | 安全问题 |
| 性能检查 | `Bash: cargo bench` (Rust) | 性能报告 |
| 生成报告 | `Write` | Review 报告 |

**Review 报告格式**:

```markdown
## 代码审查报告

### Spec 合规性
- [ ] 符合项
- [ ] 不符合项

### 严重程度
- **Critical**: 必须修复
- **Major**: 应该修复
- **Minor**: 可以考虑

### 代码质量
- Lint: X errors
- Type: X errors
- Coverage: X%

### 安全性
- X issues found
```

**Scripts**:
```bash
# scripts/run_code_review.sh
#!/bin/bash
# 运行完整代码审查
# 1. Spec 合规性检查
# 2. Lint 检查
# 3. Type 检查
# 4. Coverage 检查
# 5. 生成报告
```

### 2.6 Step 6: Finishing（完成开发）

**目标**: 最终验证并提供合并选项

| 阶段动作 | 工具/命令 | 产出 |
|---------|----------|------|
| 最终验证 | `Bash: pytest` | 全部测试通过 |
| Lint/Format | `Bash: ruff format` | 代码格式 |
| 展示选项 | LLM | Merge/PR 选项 |
| 执行合并 | `Bash: git merge` | 合并结果 |

**Scripts**:
```bash
# scripts/finalize.sh
#!/bin/bash
# 最终合并前检查
# 1. 全量测试
# 2. Lint
# 3. Type
# 4. Coverage
# 5. 生成 diff
```

---

## 3. Debugging 工具链

**目标**: 四阶段调试法，系统化根因分析

| 阶段 | 工具 | 产出 |
|------|------|------|
| Root Cause | `Read` (日志), `Bash` (reproduce) | 错误复现 |
| Pattern Analysis | `Grep` (working examples) | 差异分析 |
| Hypothesis | `Bash` (minimal test) | 假设验证 |
| Implementation | `Edit` + `Bash: pytest` | 修复验证 |

**Scripts**:
```bash
# scripts/debug_cycle.sh
#!/bin/bash
# 四阶段调试
# Phase 1: 收集证据
# Phase 2: 模式分析
# Phase 3: 假设测试
# Phase 4: 实现验证
```

---

## 4. 工作流自动化脚本

### 4.1 每日循环脚本

```bash
# run.py (主入口)
python run.py --phase night    # Night: SPEC -> PLAN -> 审批
python run.py --phase day      # Day: 执行 PLAN -> Report
```

### 4.2 工具调用链

```
Night Phase (22:00):
  1. Read SPECs -> LLM(Planning) -> Write PLAN -> Human Approval -> Update TODO.md
  2. Skill Audit -> Skill Evolution (if needed)

Day Phase (09:00-18:00):
  1. Read TODO.md -> For each P0 task:
     - Brainstorming (if new)
     - Planning (if new)
     - Implementing (TDD cycle)
     - Verifying (4-step gate)
     - Code Review
  2. Update TODO.md
  3. Hourly Heartbeat

Report Phase:
  1. Generate daily report
  2. Update TODO.md completion
  3. Trigger Skill Evolution if errors
```

---

## 5. Watchdog 心跳机制

### 5.1 心跳间隔

```yaml
watchdog:
  heartbeat_interval: 180  # 3 分钟
  max_missed_heartbeats: 3  # 最多丢 3 次
  recovery_action: checkpoint_restore
```

### 5.2 Checkpoint 内容

```python
@dataclass
class Checkpoint:
    timestamp: datetime
    workflow_state: WorkflowState
    current_task: str
    pending_approvals: list[str]
    recent_commits: list[str]
    memory_summary: str
```

---

## 6. Git Hooks 配置

### 6.1 客户端 Hooks

```yaml
# .git/hooks/pre-commit
- run_lint: ruff check src/
- run_type: mypy src/
- run_tests: pytest tests/

# .git/hooks/commit-msg
- validate_commit_format: <type>(<scope>): <subject>

# .git/hooks/pre-push
- run_full_test_suite: pytest
- check_branch_status
```

---

## 7. 工具权限级别

| 级别 | 工具 | 风险 | 需要审批 |
|------|------|------|---------|
| L1 | Read, Glob, Grep | 低 | 否 |
| L2 | Write, Edit, Bash (safe) | 中 | 首次 |
| L3 | Bash ( destructive) | 高 | 明确审批 |
| L4 | git push, rm -rf | 极高 | 每次 |

---

*规范版本: v0.1.0*
*创建日期: 2026-04-15*
