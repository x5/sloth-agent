# Sloth Agent 工作流流程实现计划

> 版本: v0.1.0
> 日期: 2026-04-15
> 基于: docs/specs/20260415-workflow-process-spec.md

---

## 1. 概述

本文档定义如何将 Superpowers 风格的严谨流程实现到 Sloth Agent 中。

### 1.1 需要实现的核心组件

| 组件 | 说明 | 优先级 |
|------|------|--------|
| Workflow Engine | 工作流状态机 | P0 |
| Brainstorming Module | 构思/提问模块 | P1 |
| Plan Generator | 计划生成器 | P1 |
| TDD Enforcer | TDD 强制执行 | P1 |
| Verifier | 验证器 | P0 |
| Code Reviewer | 代码审查器 | P2 |
| Debugger | 系统化调试器 | P2 |

---

## 2. 工作流状态机

### 2.1 状态定义

```python
class WorkflowState(Enum):
    """工作流状态枚举"""
    IDLE = "idle"                              # 空闲
    BRAINSTORMING = "brainstorming"           # 构思阶段
    BRAINSTORMING_AWAITING_APPROVAL = "brainstorming_awaiting_approval"
    PLANNING = "planning"                     # 计划阶段
    PLANNING_AWAITING_APPROVAL = "planning_awaiting_approval"
    IMPLEMENTING = "implementing"            # 执行阶段
    VERIFYING = "verifying"                  # 验证阶段
    CODE_REVIEW = "code_review"               # 代码审查
    COMPLETING = "completing"                # 完成阶段
    DEBUGGING = "debugging"                  # 调试阶段
    ERROR = "error"                          # 错误状态
```

### 2.2 状态转换规则

```
┌─────────┐
│  IDLE  │◀────────────────────────────────────────┐
└────┬────┘                                         │
     │ new_task                                      │
     ▼                                              │
┌───────────────┐                                    │
│ BRAINSTORMING │                                    │
└───────┬───────┘                                    │
        │ design_approved                            │
        ▼                                            │
┌─────────────────────┐                              │
│ BRAINSTORMING_AWAITING_APPROVAL │                  │
└──────────┬──────────┘                              │
           │ user_approved                           │
           ▼                                          │
┌─────────┐                                          │
│ PLANNING│                                          │
└────┬────┘                                          │
     │ plan_approved                                │
     ▼                                                │
┌─────────────────────┐                              │
│ PLANNING_AWAITING_APPROVAL │                       │
└──────────┬──────────┘                              │
           │ user_approved                           │
           ▼                                          │
┌─────────┐    │                                     │
│IMPLEMENTING│◀┘                                     │
└────┬────┘                                         │
     │ task_done                                   │
     ▼                                              │
┌──────────┐                                         │
│VERIFYING│                                         │
└────┬────┘                                         │
     │ verification_failed                          │
     ▼                                              │
┌─────────┐    │                                     │
│DEBUGGING│──┘                                      │
└────┬────┘                                         │
     │ verified                                    │
     ▼                                              │
┌──────────┐                                        │
│CODE_REVIEW│                                       │
└────┬─────┘                                        │
     │ review_passed                              │
     ▼                                              │
┌──────────┐                                        │
│COMPLETING│                                        │
└────┬─────┘                                        │
     │ done ◀──────────────────────────────────────┘
     ▼
┌──────────┐
│   IDLE   │
└──────────┘
```

---

## 3. 核心模块实现

### 3.1 工作流引擎

**文件**: `src/sloth_agent/workflow/engine.py`

```python
class WorkflowEngine:
    """
    工作流引擎 - 控制所有状态转换和流程执行
    """

    def __init__(self, config: Config):
        self.state = WorkflowState.IDLE
        self.history: list[WorkflowState] = []

    def transition(self, event: str, data: dict = None) -> WorkflowState:
        """
        处理状态转换

        Args:
            event: 事件名称
            data: 附加数据

        Returns:
            新的工作流状态

        Raises:
            InvalidTransitionError: 如果转换无效
        """
        pass

    def get_valid_events(self) -> list[str]:
        """获取当前状态下可以触发的事件"""
        pass

    def get_state(self) -> WorkflowState:
        """获取当前状态"""
        pass

    def get_history(self) -> list[WorkflowState]:
        """获取状态历史"""
        pass
```

### 3.2 Brainstorming 模块

**文件**: `src/sloth_agent/workflow/brainstorming.py`

```python
class BrainstormingModule:
    """
    构思模块 - 通过提问理解需求
    """

    def __init__(self):
        self.questions: list[dict] = []
        self.approaches: list[dict] = []
        self.current_phase: str = "exploring"

    def explore_context(self, task: str) -> dict:
        """
        探索项目上下文

        Returns:
            包含文件、文档、git历史的上下文
        """
        pass

    def ask_question(self, question: str, options: list[str] = None) -> dict:
        """
        向用户提问

        Args:
            question: 问题内容
            options: 选项列表（可选）

        Returns:
            用户回答
        """
        pass

    def propose_approaches(self, task: str) -> list[dict]:
        """
        提出多个方案及权衡分析

        Returns:
            方案列表，每项包含描述和权衡
        """
        pass

    def present_design_section(self, section: str) -> bool:
        """
        分段呈现设计方案

        Args:
            section: 设计内容段

        Returns:
            用户是否批准
        """
        pass

    def check_hard_gate(self) -> bool:
        """
        检查硬性门槛 - 在设计批准前不能写代码

        Returns:
            是否满足硬性门槛
        """
        pass
```

### 3.3 计划生成器

**文件**: `src/sloth_agent/workflow/planner.py`

```python
class ImplementationPlanner:
    """
    实现计划生成器 - 分解任务为小步骤
    """

    def __init__(self, config: Config):
        self.tasks: list[Task] = []

    def create_plan(self, design_doc: str) -> Plan:
        """
        从设计文档创建实现计划

        Args:
            design_doc: 设计文档路径

        Returns:
            实现计划
        """
        pass

    def break_into_micro_tasks(self, task: str) -> list[MicroTask]:
        """
        将任务分解为 2-5 分钟的微任务

        Args:
            task: 任务描述

        Returns:
            微任务列表
        """
        pass

    def add_verification_steps(self, task: MicroTask) -> MicroTask:
        """
        为每个任务添加验证步骤

        Returns:
            包含验证步骤的任务
        """
        pass

    def self_review(self) -> list[str]:
        """
        自我检查

        Returns:
            发现的问题列表
        """
        pass
```

### 3.4 TDD 强制器

**文件**: `src/sloth_agent/workflow/tdd_enforcer.py`

```python
class TDDEnforcer:
    """
    TDD 强制执行器
    """

    THE_IRON_LAW = "没有失败的测试，就不能写任何生产代码"

    def enforce_red(self, task: MicroTask) -> TestResult:
        """
        RED 阶段 - 编写失败的测试

        Returns:
            测试运行结果
        """
        pass

    def verify_red(self, result: TestResult) -> bool:
        """
        验证 RED - 确认测试失败原因正确

        Returns:
            是否正确失败
        """
        pass

    def enforce_green(self, task: MicroTask) -> TestResult:
        """
        GREEN 阶段 - 编写最小实现

        Returns:
            测试运行结果
        """
        pass

    def enforce_refactor(self, task: MicroTask) -> RefactorResult:
        """
        REFACTOR 阶段 - 重构代码

        Returns:
            重构结果
        """
        pass

    def run_cycle(self, task: MicroTask) -> CycleResult:
        """
        运行完整的红绿重构周期

        Returns:
            周期结果
        """
        pass
```

### 3.5 验证器

**文件**: `src/sloth_agent/workflow/verifier.py`

```python
class Verifier:
    """
    验证器 - 证据优于声明
    """

    def verify(self, claim: str, evidence_command: str) -> VerificationResult:
        """
        验证声明

        Args:
            claim: 声明内容
            evidence_command: 证明声明的命令

        Returns:
            验证结果
        """
        pass

    def check_tests(self) -> TestVerification:
        """验证测试通过"""
        pass

    def check_build(self) -> BuildVerification:
        """验证构建成功"""
        pass

    def check_coverage(self, threshold: float) -> CoverageVerification:
        """验证覆盖率"""
        pass

    def is_red_flag_present(self, output: str) -> bool:
        """检查红灯警告"""
        pass
```

### 3.6 代码审查器

**文件**: `src/sloth_agent/workflow/code_reviewer.py`

```python
class CodeReviewer:
    """
    代码审查器
    """

    def check_spec_compliance(self, diff: str, spec: str) -> ComplianceResult:
        """
        Spec 合规性检查

        Returns:
            合规性结果
        """
        pass

    def check_code_quality(self, diff: str) -> QualityResult:
        """
        代码质量检查

        Returns:
            质量结果
        """
        pass

    def generate_report(self) -> ReviewReport:
        """
        生成审查报告

        Returns:
            审查报告
        """
        pass
```

### 3.7 系统化调试器

**文件**: `src/sloth_agent/workflow/debugger.py`

```python
class SystematicDebugger:
    """
    系统化调试器 - 四阶段调试法
    """

    def phase1_root_cause(self, error: Error) -> RootCauseResult:
        """
        Phase 1: 根因调查

        - 仔细阅读错误信息
        - 复现问题
        - 检查最近的变更
        - 收集证据
        - 回溯调用栈
        """
        pass

    def phase2_pattern_analysis(self, evidence: dict) -> PatternResult:
        """
        Phase 2: 模式分析

        - 找到工作的示例
        - 完全对比
        - 识别差异
        """
        pass

    def phase3_hypothesis_testing(self, hypothesis: str) -> HypothesisResult:
        """
        Phase 3: 假设与测试

        - 形成单一具体理论
        - 用最小变更测试
        - 验证后再继续
        """
        pass

    def phase4_implementation(self, fix: Fix) -> ImplementationResult:
        """
        Phase 4: 实现

        - 首先创建失败的测试
        - 实现一个修复
        - 验证有效
        """
        pass

    def run_debug_cycle(self, error: Error) -> DebugResult:
        """
        运行完整的调试周期
        """
        pass
```

---

## 4. 工作流配置

### 4.1 工作流配置示例

```yaml
# configs/workflow.yaml
workflow:
  enabled: true

  # 硬性门槛
  hard_gates:
    - name: "no_code_before_design_approval"
      description: "设计批准前不能写代码"
      enforce: true

  # TDD 配置
  tdd:
    enforced: true
    coverage_threshold: 80

  # 验证配置
  verification:
    required: true
    evidence_required: true

  # 调试配置
  debugging:
    mandatory_root_cause: true
    max_fix_attempts: 3
```

---

## 5. 实现任务分解

### 任务 1: 工作流引擎 (P0)

```
- [ ] 创建 WorkflowState 枚举
- [ ] 实现 WorkflowEngine 类
- [ ] 实现状态转换规则
- [ ] 实现历史记录
- [ ] 单元测试
```

### 任务 2: Brainstorming 模块 (P1)

```
- [ ] 实现上下文探索
- [ ] 实现提问机制
- [ ] 实现方案提议
- [ ] 实现设计分段呈现
- [ ] 实现硬性门槛检查
- [ ] 单元测试
```

### 任务 3: 计划生成器 (P1)

```
- [ ] 实现任务分解
- [ ] 实现微任务创建
- [ ] 实现验证步骤添加
- [ ] 实现自我检查
- [ ] 单元测试
```

### 任务 4: TDD 强制器 (P1)

```
- [ ] 实现 RED 阶段
- [ ] 实现 GREEN 阶段
- [ ] 实现 REFACTOR 阶段
- [ ] 实现铁律检查
- [ ] 单元测试
```

### 任务 5: 验证器 (P0)

```
- [ ] 实现验证门控
- [ ] 实现测试验证
- [ ] 实现构建验证
- [ ] 实现覆盖率验证
- [ ] 实现红灯警告检测
- [ ] 单元测试
```

### 任务 6: 代码审查器 (P2)

```
- [ ] 实现 Spec 合规性检查
- [ ] 实现代码质量检查
- [ ] 实现审查报告生成
- [ ] 单元测试
```

### 任务 7: 系统化调试器 (P2)

```
- [ ] 实现 Phase 1-4
- [ ] 实现调试周期
- [ ] 实现根因验证
- [ ] 单元测试
```

### 任务 8: 项目初始化与文档强制器 (P0)

```
- [ ] 实现 DocumentEnforcer 类
- [ ] 实现 validate_project_structure()
- [ ] 实现 validate_docs_structure()
- [ ] 实现 validate_document_path()
- [ ] 实现 create_project_structure()
- [ ] 支持多语言项目 (Python/Rust/Node/Go)
- [ ] sloth init 命令集成
- [ ] 单元测试
```

**DocumentEnforcer 验证规则**:

| 检查项 | 不通过则 |
|--------|---------|
| 目录结构完整 | 拒绝初始化 |
| 文档命名规范 | 拒绝创建 |
| 文档位置正确 | 拒绝创建 |

---

## 6. 验收标准

### 6.1 工作流引擎

- [ ] 状态转换正确
- [ ] 历史记录完整
- [ ] 无效转换被拒绝

### 6.2 Brainstorming

- [ ] 提问机制正常工作
- [ ] 硬性门槛生效
- [ ] 设计文档正确生成

### 6.3 TDD

- [ ] RED 阶段测试必须先失败
- [ ] 没有失败测试不能写代码
- [ ] 覆盖率门槛生效

### 6.4 验证

- [ ] 必须有证据才能声称成功
- [ ] 红灯警告被检测
- [ ] 无验证不能标记完成

---

## 7. 与工具系统的集成

```
Workflow Engine
      │
      ├──▶ Tool: Read
      ├──▶ Tool: Write
      ├──▶ Tool: Edit
      ├──▶ Tool: Bash (执行验证命令)
      ├──▶ Tool: TaskCreate/List/Update
      ├──▶ Tool: Checkpoint
      └──▶ Tool: ApprovalRequest
```

---

*计划版本: v0.1.0*
*创建日期: 2026-04-15*
