"""Product Orchestrator — 产品层入口，不负责执行循环。

Spec: architecture-overview.md §3.1.1
"""

from pathlib import Path

from sloth_agent.core.config import Config
from sloth_agent.core.runner import RunState
from sloth_agent.core.tools.tool_registry import ToolRegistry


class ProductOrchestrator:
    """产品层入口。

    只负责：
    - 模式入口、创建/恢复 RunState
    - 调用 Runner.run(...)
    """

    def __init__(self, config: Config):
        self.config = config
        self.tool_registry = ToolRegistry(config)

    def create_run_state(
        self,
        run_id: str,
        session_id: str | None = None,
    ) -> RunState:
        return RunState(
            run_id=run_id,
            session_id=session_id,
            phase="initializing",
        )

    def _memory_dir(self, run_id: str) -> Path:
        """Return the memory directory for a given run_id."""
        project_root = Path(__file__).parent.parent.parent.parent
        return project_root / "memory" / "sessions" / run_id

    def resume_run_state(self, run_id: str) -> RunState | None:
        """从文件系统恢复 RunState。"""
        path = self._memory_dir(run_id) / "state.json"
        if path.exists():
            return RunState.model_validate_json(path.read_text(encoding="utf-8"))
        return None
