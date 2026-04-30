# 会话生命周期管理规范

> 版本: v1.0.0
> 日期: 2026-04-16
> 状态: v0.1.0 已实现 Checkpoint 子集
> v0.1.0 实现状态: Git CheckpointManager (create_git_checkpoint / rollback_to / auto_commit) 已实现
>   - 实现文件: `src/sloth_agent/reliability/checkpoint.py`
>   - 测试覆盖: `tests/reliability/test_checkpoint.py`

---

## 1. 问题

在昼夜循环、多 Agent 并行、worktree 隔离的场景下：
1. 会话的创建/暂停/恢复/终止没有明确定义
2. 什么状态是跨会话共享的、什么是会话隔离的，不清楚
3. 会话和 git branch 的映射关系未定义
4. 会话状态序列化与恢复机制缺失
5. 并发会话缺乏限制

---

## 2. 会话模型

### 2.1 会话定义

```python
@dataclass
class Session:
    """Agent 会话。"""
    session_id: str                # 唯一标识，如 "nightly-20260416"
    name: str                      # 人类可读名称
    status: SessionStatus          # active | paused | completed | failed | terminated
    created_at: float
    updated_at: float
    ended_at: float | None = None

    # 关联信息
    agent_id: str                  # 所属 Agent
    scenario_id: str               # 执行的场景
    branch: str                    # 关联的 git 分支
    worktree_path: str | None      # worktree 路径

    # 状态
    current_phase: str | None      # 当前执行的 Phase
    phases_completed: list[str]    # 已完成的 Phase
    phases_failed: list[str]       # 失败的 Phase
    checkpoint_path: str | None    # 最新 checkpoint 路径

    # 资源使用
    total_tokens: int              # 累计 token 消耗
    total_cost: float              # 累计费用
    tool_calls: int                # 工具调用次数
    llm_calls: int                 # LLM 调用次数

    # 配置
    max_context_turns: int         # 最大上下文轮次
    approved_tools: list[str]      # 已批准的工具列表


class SessionStatus(Enum):
    ACTIVE = "active"              # 正在执行
    PAUSED = "paused"              # 已暂停（等待恢复）
    COMPLETED = "completed"        # 正常完成
    FAILED = "failed"              # 失败终止
    TERMINATED = "terminated"      # 手动终止
```

### 2.2 会话类型

| 会话类型 | 创建时机 | 生命周期 | 状态共享 |
|---------|---------|---------|---------|
| **Autonomous Session** | 自主模式启动 | day/night 循环，直到场景完成或终止 | 跨 Phase 共享 |
| **Chat Session** | REPL 启动 | 用户退出时结束 | 独立 |
| **Multi-agent Session** | 多 Agent 分发 | 子任务完成时结束 | 通过消息总线共享 |

---

## 3. 会话管理器

```python
class SessionManager:
    """会话生命周期管理器。"""

    def __init__(self, config: Config, memory_store: MemoryStore):
        self.config = config
        self.memory = memory_store
        self.sessions: dict[str, Session] = {}
        self.max_concurrent = config.session.max_concurrent

    def create(self, scenario_id: str, agent_id: str,
               branch: str | None = None) -> Session:
        """创建新会话。"""
        # 检查并发限制
        active_count = sum(
            1 for s in self.sessions.values()
            if s.status == SessionStatus.ACTIVE
        )
        if active_count >= self.max_concurrent:
            raise SessionLimitError(
                f"Maximum concurrent sessions ({self.max_concurrent}) reached"
            )

        session_id = self._generate_session_id(scenario_id)
        session = Session(
            session_id=session_id,
            name=f"{scenario_id}-{datetime.now():%Y%m%d-%H%M%S}",
            status=SessionStatus.ACTIVE,
            created_at=time.time(),
            updated_at=time.time(),
            agent_id=agent_id,
            scenario_id=scenario_id,
            branch=branch or f"session/{session_id}",
        )

        self.sessions[session_id] = session
        self.memory.save_session(session)

        logger.info(f"Session created: {session_id}")
        return session

    def pause(self, session_id: str) -> None:
        """暂停会话。"""
        session = self._get_active_session(session_id)
        session.status = SessionStatus.PAUSED
        session.updated_at = time.time()
        self._save_session(session)
        self._create_checkpoint(session)

    def resume(self, session_id: str) -> Session:
        """恢复会话。"""
        session = self._get_session(session_id)
        if session.status != SessionStatus.PAUSED:
            raise SessionError(
                f"Session {session_id} is not paused (current: {session.status})"
            )

        # 从 checkpoint 恢复状态
        checkpoint = self._load_latest_checkpoint(session)
        if checkpoint:
            self._restore_from_checkpoint(session, checkpoint)

        session.status = SessionStatus.ACTIVE
        session.updated_at = time.time()
        self._save_session(session)

        logger.info(f"Session resumed: {session_id}")
        return session

    def complete(self, session_id: str) -> None:
        """正常完成会话。"""
        session = self._get_session(session_id)
        session.status = SessionStatus.COMPLETED
        session.ended_at = time.time()
        session.updated_at = time.time()
        self._save_session(session)
        self._create_checkpoint(session)

        logger.info(f"Session completed: {session_id}")

    def fail(self, session_id: str, reason: str) -> None:
        """标记会话失败。"""
        session = self._get_session(session_id)
        session.status = SessionStatus.FAILED
        session.ended_at = time.time()
        session.updated_at = time.time()
        session.metadata["failure_reason"] = reason
        self._save_session(session)
        self._create_checkpoint(session)

        logger.warning(f"Session failed: {session_id} - {reason}")

    def terminate(self, session_id: str) -> None:
        """手动终止会话。"""
        session = self._get_session(session_id)
        session.status = SessionStatus.TERMINATED
        session.ended_at = time.time()
        session.updated_at = time.time()
        self._save_session(session)

    def list_active(self) -> list[Session]:
        """列出所有活跃会话。"""
        return [
            s for s in self.sessions.values()
            if s.status == SessionStatus.ACTIVE
        ]

    def get(self, session_id: str) -> Session | None:
        """获取会话。"""
        return self.sessions.get(session_id)
```

---

## 4. 会话与 Git 分支映射

### 4.1 分支命名规则

```
会话类型                  分支命名
──────────────────────────────────────────────
autonomous (单 Agent)    session/{session_id}
autonomous (多 Agent)    session/{session_id}/{agent_role}
chat                     chat/{session_id}
```

### 4.2 Worktree 管理

```python
class SessionWorktreeManager:
    """会话 worktree 管理。

    每个会话使用独立的 worktree 和分支，
    避免文件系统冲突。
    """

    def __init__(self, repo_path: str, base_dir: str = ".worktrees"):
        self.repo_path = Path(repo_path)
        self.base_dir = Path(base_dir)

    def create_session_worktree(self, session: Session) -> str:
        """为会话创建 worktree。"""
        worktree_path = self.base_dir / session.session_id
        branch = session.branch

        result = subprocess.run(
            f"git worktree add {worktree_path} -b {branch}",
            shell=True, cwd=self.repo_path, capture_output=True, text=True,
        )

        if result.returncode != 0:
            raise WorktreeError(f"Failed to create worktree: {result.stderr}")

        session.worktree_path = str(worktree_path)
        return str(worktree_path)

    def cleanup(self, session: Session) -> None:
        """清理会话 worktree。"""
        if session.worktree_path:
            subprocess.run(
                f"git worktree remove {session.worktree_path}",
                shell=True, cwd=self.repo_path, capture_output=True,
            )
            shutil.rmtree(session.worktree_path, ignore_errors=True)
```

---

## 5. 会话状态序列化

### 5.1 Checkpoint 格式

```json
{
    "session_id": "nightly-20260416-001",
    "version": 1,
    "timestamp": 1713254400.0,
    "state": {
        "current_phase": "implementation",
        "phases_completed": ["analysis", "design"],
        "phases_failed": [],
        "current_scenario": "feature-auth",
        "phase_state": {
            "implementation": {
                "retry_count": 0,
                "artifacts": ["src/auth.py", "tests/test_auth.py"],
                "gate_results": []
            }
        }
    },
    "resources": {
        "total_tokens": 25000,
        "total_cost": 0.50,
        "tool_calls": 15,
        "llm_calls": 8
    },
    "branch": "session/nightly-20260416-001",
    "worktree_path": ".worktrees/nightly-20260416-001"
}
```

### 5.2 Checkpoint 管理

```python
class CheckpointManager:
    """会话 checkpoint 管理。"""

    def __init__(self, checkpoint_dir: str = "checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)

    def create_checkpoint(self, session: Session,
                          phase_state: dict | None = None) -> str:
        """创建 checkpoint。"""
        checkpoint = {
            "session_id": session.session_id,
            "version": self._next_version(session.session_id),
            "timestamp": time.time(),
            "state": {
                "current_phase": session.current_phase,
                "phases_completed": session.phases_completed,
                "phases_failed": session.phases_failed,
                "phase_state": phase_state or {},
            },
            "resources": {
                "total_tokens": session.total_tokens,
                "total_cost": session.total_cost,
                "tool_calls": session.tool_calls,
                "llm_calls": session.llm_calls,
            },
            "branch": session.branch,
            "worktree_path": session.worktree_path,
        }

        cp_dir = self.checkpoint_dir / session.session_id
        cp_dir.mkdir(parents=True, exist_ok=True)

        cp_file = cp_dir / f"v{checkpoint['version']:03d}.json"
        cp_file.write_text(json.dumps(checkpoint, indent=2))

        return str(cp_file)

    def load_latest_checkpoint(self, session_id: str) -> dict | None:
        """加载最新 checkpoint。"""
        cp_dir = self.checkpoint_dir / session_id
        if not cp_dir.exists():
            return None

        checkpoints = sorted(cp_dir.glob("v*.json"))
        if not checkpoints:
            return None

        return json.loads(checkpoints[-1].read_text())
```

---

## 6. 配置

```yaml
# configs/session.yaml
session:
  max_concurrent: 5               # 最大并发会话数
  checkpoint_interval: 300        # 自动 checkpoint 间隔（秒）
  checkpoint_on:
    - "phase.enter"
    - "phase.exit"
    - "error.critical"
    - "session.pause"

  worktrees:
    base_dir: ".worktrees"
    auto_cleanup: true            # 会话完成后自动清理

  persistence:
    store_completed_days: 7       # 已完成会话保留天数
    store_failed_days: 30         # 失败会话保留天数
```

---

## 7. 文件清单

| 文件 | 说明 |
|------|------|
| `src/sloth_agent/session/__init__.py` | 会话模块入口 |
| `src/sloth_agent/session/manager.py` | SessionManager 会话管理器 |
| `src/sloth_agent/session/worktree.py` | SessionWorktreeManager worktree 管理 |
| `src/sloth_agent/session/checkpoint.py` | CheckpointManager checkpoint 管理 |
| `src/sloth_agent/session/models.py` | 会话数据模型 |
| `configs/session.yaml` | 会话配置 |

---

*规范版本: v1.0.0*
*创建日期: 2026-04-16*
