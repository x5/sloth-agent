# 20260416-13-session-lifecycle-implementation-plan.md

> Spec 来源: `docs/specs/20260416-13-session-lifecycle-spec.md`；`docs/specs/00000000-00-architecture-overview.md` §8.3
> Plan 文件: `docs/plans/20260416-13-session-lifecycle-implementation-plan.md`
> v0.1 实现状态: Git CheckpointManager (create_git_checkpoint / rollback_to / auto_commit) 已实现 (2 tests pass)
> v0.1 实现文件: `src/sloth_agent/reliability/checkpoint.py`

---

## 1. 目标

v1.0 实现基于 Git 的三级 checkpoint 机制（任务级/阶段级/Session 级），支持 checkpoint 创建、回滚、自动提交。

---

## 2. 步骤（按顺序执行）

### 步骤 1: 实现三级 Git Checkpoint

**文件**: `src/sloth_agent/reliability/checkpoint.py`（修改）

**内容** (spec §5, arch §8.3):

v1.0 三级 checkpoint：
- **Level 1 (任务级)**: Builder 每完成一个 task → `git commit`（自动）
- **Level 2 (阶段级)**: 每个 Agent 开始前 → `git tag sloth/stage/{stage}/start`
- **Level 3 (Session 级)**: Session 开始时 → `git tag sloth/session/{session_id}/start`

```python
class CheckpointManager:
    """基于 Git 的三级 checkpoint 和回滚。"""

    def create_git_checkpoint(self, level: str, label: str) -> str:
        """创建 git tag checkpoint。
        level: 'session' | 'stage' | 'task'
        label: 标识符，如 session_id 或 stage 名称
        """

    def rollback_to(self, tag: str) -> RollbackResult:
        """回滚到指定 checkpoint。"""

    def auto_commit(self, task, result) -> str:
        """任务完成后自动提交。"""
```

回滚触发规则（arch §8.3）：
- **任务级回滚**: reflect() action == "retry_different" → revert 上一个 task commit
- **阶段级回滚**: Gate 失败且 Builder 重试 3 次仍失败 → 回滚到阶段起点
- **Session 级回滚**: 用户主动 `sloth rollback --session`，或预算耗尽

**验收**: 在测试仓库中，git checkpoint 创建/回滚/自动提交可正常工作。

---

### 步骤 2: 编写单元测试

| 文件 | 覆盖 | 测试数 |
|------|------|--------|
| `tests/reliability/test_checkpoint.py` | git checkpoint 创建/回滚/自动提交 | 2 |

**具体测试**：

```
test_checkpoint.py:
  - test_create_and_rollback: 创建 git tag checkpoint 后，rollback_to() 正确回滚
  - test_auto_commit: auto_commit() 后，git log 包含预期提交信息
```

---

## 3. 文件清单

| 文件 | 动作 |
|------|------|
| `src/sloth_agent/reliability/checkpoint.py` | **修改** — 增加 git tag checkpoint、rollback、auto_commit |
| `tests/reliability/test_checkpoint.py` | **新建** |

---

## 4. 与现有代码的关系

| 现有文件 | 动作 | 原因 |
|----------|------|------|
| `src/sloth_agent/reliability/checkpoint.py` | **修改** | 现有只有 JSON 文件保存/恢复，需增加 git 功能 |
| `reliability/checkpoint.py` (旧) | **保留** | 现有 JSON checkpoint 保留，v1.0 同时支持两种机制 |

---

## 5. 验收标准

- [ ] `CheckpointManager.create_git_checkpoint()` 能创建 git tag
- [ ] `CheckpointManager.rollback_to()` 能回滚到指定 tag，并创建 safety backup tag
- [ ] `CheckpointManager.auto_commit()` 能自动 git add + commit
- [ ] 所有测试通过（共 2 tests）

---

*Plan 版本: v1.0.0 | 创建: 2026-04-17*
