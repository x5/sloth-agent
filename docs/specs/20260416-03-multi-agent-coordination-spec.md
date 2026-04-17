# 多 Agent 并行与协同规范

> 版本: v1.0.0
> 日期: 2026-04-16
> 状态: 新增

---

## 1. 问题

当前 Sloth Agent 是单线程执行：一个 Phase → 一个 Agent → 顺序执行。

需要支持：

1. **并行执行**：多个独立任务同时执行（如前端和后端同时开发）
2. **角色分工**：不同 Agent 扮演不同角色（Coder、Reviewer、Tester）
3. **任务分发**：主 Agent 分发任务给子 Agent，收集结果
4. **结果合并**：多个 Agent 的输出合并到一个分支
5. **冲突解决**：多个 Agent 修改同一文件时的冲突处理

---

## 2. 架构总览

```
                    ┌───────────────────┐
                    │   Coordinator     │
                    │  (主 Agent)        │
                    │                   │
                    │  - 任务分解        │
                    │  - 分发调度        │
                    │  - 结果收集        │
                    │  - 冲突解决        │
                    └───────┬───────────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
        ┌─────▼────┐ ┌─────▼────┐ ┌─────▼────┐
        │ Agent A  │ │ Agent B  │ │ Agent C  │
        │ (Coder)  │ │(Reviewer)│ │ (Tester) │
        │          │ │          │ │          │
        │ worktree │ │ worktree │ │ worktree │
        │ feat/a   │ │ feat/a   │ │ feat/a   │
        └────┬─────┘ └────┬─────┘ └────┬─────┘
             │             │             │
             └─────────────┼─────────────┘
                           │
                    ┌──────▼───────┐
                    │   Merger     │
                    │  (结果合并)   │
                    └──────────────┘
```

---

## 3. 角色定义

### 3.1 Agent 角色

| 角色 | 职责 | 技能 | 输出 |
|------|------|------|------|
| **Planner** | 任务分解、优先级排序 | writing-plans, brainstorming | PLAN + 任务列表 |
| **Coder** | 编写代码、TDD 循环 | test-driven-development, subagent-driven-development | 代码 + 测试 |
| **Reviewer** | 代码审查、Spec 合规检查 | requesting-code-review, /review | Review 报告 |
| **Tester** | 端到端测试、QA 验证 | /qa, /cso | 测试报告 |
| **Integrator** | 合并分支、解决冲突 | finishing-a-development-branch | 合并后的代码 |
| **Reporter** | 生成日报、状态报告 | — | 报告文档 |

### 3.2 角色配置

```python
@dataclass
class AgentRole:
    name: str  # "coder", "reviewer", "tester"
    description: str
    skills: list[str]  # 该角色使用的技能
    model: str  # 推荐模型
    worktree_prefix: str  # 工作空间前缀
    max_instances: int  # 最大并行实例数

ROLE_DEFINITIONS = {
    "planner": AgentRole(
        name="planner",
        description="Task decomposition and planning",
        skills=["writing-plans", "brainstorming"],
        model="claude-sonnet",
        worktree_prefix="plan",
        max_instances=1,
    ),
    "coder": AgentRole(
        name="coder",
        description="Implementation with TDD",
        skills=["test-driven-development", "subagent-driven-development"],
        model="deepseek",
        worktree_prefix="code",
        max_instances=3,
    ),
    "reviewer": AgentRole(
        name="reviewer",
        description="Code review and spec compliance",
        skills=["requesting-code-review"],
        model="claude-sonnet",
        worktree_prefix="review",
        max_instances=2,
    ),
    "tester": AgentRole(
        name="tester",
        description="End-to-end testing and QA",
        skills=["/qa", "/cso"],
        model="claude-sonnet",
        worktree_prefix="test",
        max_instances=2,
    ),
}
```

---

## 4. 任务分发

### 4.1 任务描述

```python
@dataclass
class TaskAssignment:
    task_id: str
    task_name: str
    role: str  # "coder" | "reviewer" | "tester"
    description: str
    context: dict  # 上下文信息（文件路径、spec 等）
    input_files: list[str]  # 输入文件
    expected_output: str  # 预期输出描述
    priority: int  # 1 = highest
    timeout_minutes: int = 30
    dependencies: list[str]  # 依赖的 task_id
    worktree_branch: str  # 专属分支
```

### 4.2 Coordinator（协调器）

```python
class Coordinator:
    """多 Agent 协调器。

    负责任务分解、分发、结果收集和合并。
    """

    def __init__(self, config: Config):
        self.config = config
        self.tasks: dict[str, TaskAssignment] = {}
        self.results: dict[str, TaskResult] = {}
        self.agents: dict[str, AgentInstance] = {}

    def dispatch(self, plan: Plan) -> DispatchResult:
        """根据计划分发任务。"""
        # 1. 任务分组（按依赖关系拓扑排序）
        groups = self._topological_sort(plan.tasks)

        # 2. 逐组并行执行
        for group in groups:
            group_results = self._execute_parallel(group)
            self.results.update(group_results)

            # 检查是否有失败
            failed = [tid for tid, r in group_results.items() if not r.success]
            if failed:
                return DispatchResult(
                    status="partial_failure",
                    completed=len(group_results) - len(failed),
                    failed=failed,
                )

        return DispatchResult(status="success", completed=len(self.results))

    def _execute_parallel(self, task_ids: list[str]) -> dict[str, TaskResult]:
        """并行执行一组任务。"""
        import concurrent.futures

        results = {}
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.config.multi_agent.max_workers
        ) as executor:
            futures = {}
            for task_id in task_ids:
                task = self.tasks[task_id]
                future = executor.submit(self._execute_task, task)
                futures[future] = task_id

            for future in concurrent.futures.as_completed(futures):
                task_id = futures[future]
                try:
                    result = future.result(timeout=3600)  # 1 小时超时
                    results[task_id] = result
                except Exception as e:
                    results[task_id] = TaskResult(
                        task_id=task_id,
                        success=False,
                        error=str(e),
                    )

        return results

    def _execute_task(self, task: TaskAssignment) -> TaskResult:
        """执行单个任务。"""
        # 1. 创建工作空间
        worktree = self._create_worktree(task)

        # 2. 启动 Agent 实例
        agent = self._spawn_agent(task, worktree)

        # 3. 等待完成
        result = agent.run(timeout=task.timeout_minutes * 60)

        # 4. 保存结果
        self._save_result(task, result)

        return result
```

---

## 5. Git Worktree 隔离

### 5.1 工作空间管理

```python
class WorktreeManager:
    """管理多个 Git Worktree。

    每个 Agent 实例在独立的 worktree 中工作，
    避免文件系统冲突。
    """

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.worktrees_dir = self.repo_path / ".worktrees"
        self.worktrees_dir.mkdir(exist_ok=True)

    def create(self, branch: str, prefix: str = "agent") -> Worktree:
        """创建新的 worktree。"""
        name = f"{prefix}-{branch}-{uuid4().hex[:8]}"
        path = self.worktrees_dir / name

        subprocess.run(
            f"git worktree add {path} -b {branch}",
            shell=True, cwd=self.repo_path, capture_output=True,
        )

        return Worktree(name=name, path=path, branch=branch)

    def remove(self, worktree: Worktree) -> None:
        """删除 worktree。"""
        subprocess.run(
            f"git worktree remove {worktree.path}",
            shell=True, cwd=self.repo_path, capture_output=True,
        )

    def list_all(self) -> list[Worktree]:
        """列出所有 worktree。"""
        output = subprocess.run(
            "git worktree list --porcelain",
            shell=True, cwd=self.repo_path, capture_output=True, text=True,
        ).stdout

        worktrees = []
        for block in output.strip().split("\n\n"):
            lines = block.split("\n")
            if len(lines) >= 2:
                worktrees.append(Worktree(
                    path=Path(lines[0].split()[0]),
                    branch=lines[1].replace("branch ", ""),
                ))
        return worktrees
```

---

## 6. 结果合并

### 6.1 合并策略

```python
class MergeStrategy(Enum):
    """合并策略。"""
    SEQUENTIAL = "sequential"    # 按顺序合并（无冲突）
    ORS = "ours"                 # 以某个 Agent 的结果为主
    XORS = "theirs"              # 以另一个 Agent 的结果为主
    MANUAL = "manual"            # 需要人工解决冲突
```

### 6.2 合并器

```python
class ResultMerger:
    """合并多个 Agent 的工作成果。"""

    def __init__(self, repo_path: str, target_branch: str):
        self.repo_path = Path(repo_path)
        self.target_branch = target_branch

    def merge(self, worktrees: list[Worktree], strategy: MergeStrategy) -> MergeResult:
        """合并多个 worktree 的结果。"""
        results = []

        # 切换到目标分支
        subprocess.run(
            f"git checkout {self.target_branch}",
            shell=True, cwd=self.repo_path, capture_output=True,
        )

        for worktree in worktrees:
            result = self._merge_one(worktree, strategy)
            results.append(result)
            if not result.success and strategy != MergeStrategy.MANUAL:
                break

        return MergeResult(
            success=all(r.success for r in results),
            results=results,
            conflicts=[r for r in results if not r.success],
        )

    def _merge_one(self, worktree: Worktree, strategy: MergeStrategy) -> MergeResult:
        """合并单个 worktree。"""
        try:
            result = subprocess.run(
                f"git merge {worktree.branch} --no-edit",
                shell=True, cwd=self.repo_path, capture_output=True, text=True,
            )

            if result.returncode == 0:
                return MergeResult(success=True, branch=worktree.branch)
            else:
                # 有冲突
                if strategy == MergeStrategy.OURS:
                    subprocess.run(
                        f"git checkout --ours . && git add .",
                        shell=True, cwd=self.repo_path, capture_output=True,
                    )
                    return MergeResult(success=True, branch=worktree.branch, note="used ours strategy")
                elif strategy == MergeStrategy.THEIRS:
                    subprocess.run(
                        f"git checkout --theirs . && git add .",
                        shell=True, cwd=self.repo_path, capture_output=True,
                    )
                    return MergeResult(success=True, branch=worktree.branch, note="used theirs strategy")
                else:
                    return MergeResult(
                        success=False,
                        branch=worktree.branch,
                        error=result.stderr,
                        conflicts=self._parse_conflicts(result.stderr),
                    )
        except Exception as e:
            return MergeResult(success=False, branch=worktree.branch, error=str(e))
```

---

## 7. Agent 间通信

### 7.1 消息总线

```python
@dataclass
class AgentMessage:
    from_agent: str
    to_agent: str
    message_type: str  # "task_result" | "error" | "sync_request" | "dependency_ready"
    payload: dict
    timestamp: float

class MessageBus:
    """Agent 间消息传递总线。"""

    def __init__(self, db_path: str = "./run/message_bus.db"):
        self.db_path = Path(db_path)
        self._init_db()

    def send(self, message: AgentMessage) -> None:
        """发送消息。"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO messages (from_agent, to_agent, type, payload, timestamp) "
                "VALUES (?, ?, ?, ?, ?)",
                (message.from_agent, message.to_agent, message.message_type,
                 json.dumps(message.payload), message.timestamp)
            )

    def receive(self, to_agent: str, message_type: str | None = None) -> list[AgentMessage]:
        """接收消息。"""
        with sqlite3.connect(self.db_path) as conn:
            if message_type:
                rows = conn.execute(
                    "SELECT * FROM messages WHERE to_agent = ? AND type = ? ORDER BY timestamp",
                    (to_agent, message_type)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM messages WHERE to_agent = ? ORDER BY timestamp",
                    (to_agent,)
                ).fetchall()

            return [
                AgentMessage(
                    from_agent=r[1], to_agent=r[2], message_type=r[3],
                    payload=json.loads(r[4]), timestamp=r[5]
                )
                for r in rows
            ]

    def mark_consumed(self, to_agent: str) -> int:
        """标记消息已消费（删除）。"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM messages WHERE to_agent = ?",
                (to_agent,)
            )
            return cursor.rowcount
```

### 7.2 依赖通知

```python
class DependencyManager:
    """管理任务间依赖关系。"""

    def __init__(self, message_bus: MessageBus):
        self.bus = message_bus
        self.dependencies: dict[str, list[str]] = {}  # task_id -> [dependency_ids]
        self.completed: set[str] = set()

    def wait_for_dependencies(self, task_id: str) -> None:
        """等待依赖任务完成。"""
        deps = self.dependencies.get(task_id, [])
        while not all(d in self.completed for d in deps):
            # 检查消息总线
            messages = self.bus.receive(task_id, message_type="dependency_ready")
            for msg in messages:
                self.completed.add(msg.payload["task_id"])
            time.sleep(1)

    def notify_dependents(self, task_id: str) -> None:
        """通知等待该任务的依赖。"""
        # 找出所有依赖这个任务的任务
        waiting_tasks = [
            tid for tid, deps in self.dependencies.items()
            if task_id in deps and tid not in self.completed
        ]

        for waiting_task in waiting_tasks:
            self.bus.send(AgentMessage(
                from_agent="coordinator",
                to_agent=waiting_task,
                message_type="dependency_ready",
                payload={"task_id": task_id},
                timestamp=time.time(),
            ))

        self.completed.add(task_id)
```

---

## 8. 场景示例

### 8.1 场景：前后端并行开发

```python
# 计划：开发一个新功能，包含前端和后端改动
plan = Plan(
    name="feature-user-auth",
    tasks=[
        TaskAssignment(
            task_id="backend-1",
            task_name="Implement auth API",
            role="coder",
            description="Create /api/auth/login endpoint",
            input_files=["src/api/__init__.py"],
            worktree_branch="feat/auth-backend",
        ),
        TaskAssignment(
            task_id="frontend-1",
            task_name="Implement login form",
            role="coder",
            description="Create login page component",
            input_files=["src/components/"],
            worktree_branch="feat/auth-frontend",
        ),
    ],
)

# 分发（前后端并行）
coordinator = Coordinator(config)
coordinator.tasks = {t.task_id: t for t in plan.tasks}
result = coordinator.dispatch(plan)

# 合并
merger = ResultMerger(repo_path=".", target_branch="develop")
worktrees = [t.worktree for t in plan.tasks]
merge_result = merger.merge(worktrees, strategy=MergeStrategy.SEQUENTIAL)
```

### 8.2 场景：Coder → Reviewer → Tester 流水线

```python
pipeline = [
    {"role": "coder", tasks: ["impl-1", "impl-2"]},       # 并行编码
    {"role": "reviewer", tasks: ["review-1", "review-2"]},  # 并行审查
    {"role": "tester", tasks: ["test-e2e-1"]},              # 端到端测试
]

for stage in pipeline:
    # 等待上一阶段完成
    for task_id in stage["tasks"]:
        dependency_manager.wait_for_dependencies(task_id)

    # 执行当前阶段
    results = coordinator._execute_parallel(stage["tasks"])

    # 通知下一阶段
    for task_id in results:
        dependency_manager.notify_dependents(task_id)
```

---

## 9. 冲突检测与预防

### 9.1 文件级冲突检测

```python
class ConflictDetector:
    """检测多个 Agent 是否修改了同一文件。"""

    def detect(self, worktrees: list[Worktree]) -> list[FileConflict]:
        """检测文件冲突。"""
        file_map: dict[str, list[Worktree]] = {}  # file_path -> [worktrees that modified it]

        for wt in worktrees:
            changed_files = self._get_changed_files(wt)
            for file_path in changed_files:
                file_map.setdefault(file_path, []).append(wt)

        conflicts = []
        for file_path, wts in file_map.items():
            if len(wts) > 1:
                conflicts.append(FileConflict(
                    file_path=file_path,
                    worktrees=wts,
                ))

        return conflicts

    def _get_changed_files(self, worktree: Worktree) -> list[str]:
        """获取 worktree 中修改的文件。"""
        result = subprocess.run(
            f"git diff --name-only {worktree.branch}~1 {worktree.branch}",
            shell=True, cwd=worktree.path, capture_output=True, text=True,
        )
        return result.stdout.strip().split("\n")
```

---

## 10. 配置

```yaml
# configs/multi_agent.yaml
multi_agent:
  enabled: false  # 默认关闭
  max_workers: 4  # 最大并行 Agent 数
  message_bus_db: "./run/message_bus.db"

  roles:
    coder:
      model: "deepseek"
      max_instances: 3
    reviewer:
      model: "claude-sonnet"
      max_instances: 2
    tester:
      model: "claude-sonnet"
      max_instances: 2

  worktrees:
    base_dir: ".worktrees"
    auto_cleanup: true  # 任务完成后自动删除 worktree

  merge:
    default_strategy: "sequential"
    auto_resolve_conflicts: false  # 冲突时不自动解决
```

---

## 10. v1.0 Agent 交接协议

v1.0 采用 3-Agent 串行流水线（Builder → Reviewer → Deployer），Agent 间传递确定性数据（git diff、pytest 输出、覆盖率数字），而非 LLM 生成的摘要：

```python
class BuilderOutput(BaseModel):
    """Builder → Reviewer 的交接物"""
    branch: str                    # git branch name
    changed_files: list[str]       # 变更文件列表
    diff_summary: str              # git diff --stat
    test_results: TestReport       # pytest 输出（结构化）
    coverage: float                # 覆盖率数字
    build_log: str | None          # 构建日志（如有错误）


class ReviewerOutput(BaseModel):
    """Reviewer → Deployer 的交接物"""
    approved: bool
    branch: str
    blocking_issues: list[str]     # 空 = 通过
    suggestions: list[str]         # 非阻塞建议
```

---

## 11. 文件清单

| 文件 | 说明 |
|------|------|
| `src/sloth_agent/multiagent/coordinator.py` | Coordinator 总调度器 |
| `src/sloth_agent/multiagent/roles.py` | Agent 角色定义 |
| `src/sloth_agent/multiagent/worktree_manager.py` | Worktree 管理 |
| `src/sloth_agent/multiagent/merger.py` | 结果合并器 |
| `src/sloth_agent/multiagent/message_bus.py` | 消息总线 |
| `src/sloth_agent/multiagent/dependency.py` | 依赖管理 |
| `src/sloth_agent/multiagent/conflict_detector.py` | 冲突检测 |
| `src/sloth_agent/multiagent/models.py` | 数据模型 |
| `configs/multi_agent.yaml` | 多 Agent 配置 |

---

*规范版本: v1.0.0*
*创建日期: 2026-04-16*
