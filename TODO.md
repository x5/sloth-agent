# Project TODO

> 最后更新: 20260416
> 框架: Sloth Agent v0.1.0

---

## 活跃任务

### P0: Phase-Role-Architecture 实现

> Plan: `docs/plans/20260416-phase-role-architecture.md`
> 总计: 7 tasks, 27 tests

依赖链: `1 → 2 → 3 → 4 → {5,6} → 7`

- [ ] **Task 1: Core Data Models** (5 tests)
  - [ ] Create `src/workflow/__init__.py`
  - [ ] Create `src/workflow/models.py` (Phase, Agent, Skill, Scenario, Gate)
  - [ ] Create `tests/workflow/test_models.py`
  - [ ] 测试通过, commit

- [ ] **Task 2: Registry System** (9 tests) ← Task 1
  - [ ] Create `src/workflow/registry.py` (PhaseRegistry 8 phases, AgentRegistry 8 agents, SkillRegistry 37 skills, ScenarioValidator 8 scenarios, 15 gates)
  - [ ] Create `tests/workflow/test_registry.py`
  - [ ] 测试通过, commit

- [ ] **Task 3: Memory Store** (6 tests) ← Task 2
  - [ ] Create `src/workflow/memory.py` (ScenarioMemoryStore)
  - [ ] Create `tests/workflow/test_memory.py`
  - [ ] 测试通过, commit

- [ ] **Task 4: Workflow Engine** (4 tests) ← Task 3
  - [ ] Create `src/workflow/engine.py` (WorkflowEngine, PhaseResult, ScenarioResult, Gate validation)
  - [ ] Create `tests/workflow/test_engine.py`
  - [ ] 测试通过, commit

- [ ] **Task 5: YAML Configuration** (1 test) ← Task 4
  - [ ] Modify `src/core/config.py` (add WorkflowConfig, PhaseConfig)
  - [ ] Create `configs/workflow.yaml`
  - [ ] Create `tests/workflow/test_config.py`
  - [ ] 测试通过, commit

- [ ] **Task 6: Integration Tests** (3 tests) ← Task 4
  - [ ] Create `tests/workflow/test_integration.py` (standard, frontend-only, gate failure)
  - [ ] 测试通过, commit

- [ ] **Task 7: Export Public API** ← Task 5 + Task 6
  - [ ] Update `src/workflow/__init__.py` (full exports)
  - [ ] Update `src/__init__.py` (add workflow)
  - [ ] Run full test suite (27 tests), commit

### 其他活跃任务

- [ ] **[P0]** Tool 系统实现 (Read/Write/Edit/Glob/Grep/Bash) @agent @20260415
- [ ] **[P1]** TDD Enforcer 实现 - RED-GREEN-REFACTOR 周期强制 @agent @20260415
- [ ] **[P1]** Skill 自动进化引擎实现 @agent @20260415
- [ ] **[P2]** Systematized Debugger 实现 - 四阶段调试法 @agent @20260415
- [ ] **[P2]** Code Reviewer 实现 @agent @20260415

## 阻塞

## 已完成

- [x] **[P0]** 框架规范文档编写 @agent @20260415
- [x] **[P0]** Document Naming Convention 制定 @agent @20260415
- [x] **[P1]** Workflow Process Spec 定义 @agent @20260415
- [x] **[P1]** Tools Design Spec 定义 @agent @20260415
- [x] **[P0]** Phase-Role-Architecture Spec 编写 @agent @20260416
- [x] **[P0]** Phase-Role-Architecture Plan 编写 @agent @20260416

---

## 任务标签说明

| 标签 | 说明 |
|------|------|
| `P0` | 最高优先级，当前迭代必须完成 |
| `P1` | 高优先级，当前迭代应该完成 |
| `P2` | 中优先级，当前迭代可以完成 |
| `@owner` | 任务负责人（agent/human） |
| `@YYYYMMDD` | 创建日期 |
| `← Task N` | 依赖前置任务 N |

---

## 更新日志

| 日期 | 更新内容 |
|------|---------|
| 20260415 | 初始版本，创建框架基础任务 |
| 20260416 | 整合 Phase-Role-Architecture 任务链，拆分 7 个子任务，建立依赖关系 |
