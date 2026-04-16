"""v1.0 Runtime Kernel — Runner, RunState, NextStep, HookManager.

Spec: architecture-overview.md §3.1.1, §5.1.1.1, §5.1.1.2
"""

import json
import logging
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, Field

from sloth_agent.core.config import Config
from sloth_agent.core.tools.models import ToolCallRequest
from sloth_agent.core.tools.orchestrator import ToolOrchestrator
from sloth_agent.core.tools.tool_registry import ToolRegistry

logger = logging.getLogger("runner")


# ---------------------------------------------------------------------------
# NextStep protocol (spec §5.1.1.2)
# ---------------------------------------------------------------------------

class NextStepType(str, Enum):
    final_output = "final_output"
    tool_call = "tool_call"
    phase_handoff = "phase_handoff"
    retry_same = "retry_same"
    retry_different = "retry_different"
    replan = "replan"
    interruption = "interruption"
    abort = "abort"


class ToolRequest(BaseModel):
    tool_name: str
    params: dict[str, Any] = Field(default_factory=dict)


class NextStep(BaseModel):
    type: NextStepType
    output: str | None = None
    request: ToolRequest | None = None
    next_agent: str | None = None
    next_phase: str | None = None
    reason: str | None = None


# ---------------------------------------------------------------------------
# RunState — single source of truth (spec §3.1.1)
# ---------------------------------------------------------------------------

class RunState(BaseModel):
    """唯一运行时状态，所有真相源。"""
    run_id: str
    session_id: str | None = None
    current_agent: str | None = None      # "builder" / "reviewer" / "deployer"
    current_phase: str | None = None      # "plan_parsing" / "coding" / ...
    phase: str = "initializing"           # initializing | running | paused | completed | aborted
    turn: int = 0
    tool_history: list[dict] = Field(default_factory=list)
    pending_interruptions: list[dict] = Field(default_factory=list)
    handoff_payload: dict | None = None
    model: str = "deepseek-v3.2"
    output: str | None = None
    errors: list[str] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @property
    def is_finished(self) -> bool:
        return self.phase in ("completed", "aborted")


# ---------------------------------------------------------------------------
# HookManager (spec §7.4)
# ---------------------------------------------------------------------------

class HookManager:
    """轻量事件钩子管理器。"""

    def __init__(self):
        self.hooks: dict[str, list[Callable]] = {}

    def on(self, event: str, handler: Callable) -> None:
        self.hooks.setdefault(event, []).append(handler)

    def emit(self, event: str, data: Any = None) -> None:
        for handler in self.hooks.get(event, []):
            handler(data)

    def hook_points(self) -> list[str]:
        """返回 v1.x 所有 hook 点名称。"""
        return [
            "run.start", "run.end",
            "phase.start", "phase.end",
            "model.start", "model.end",
            "tool.start", "tool.end",
            "handoff",
            "gate.pass", "gate.fail",
            "reflection",
            "resume",
            "budget.warn", "budget.over",
        ]


# ---------------------------------------------------------------------------
# Runner — 唯一执行循环内核 (spec §3.1.1)
# ---------------------------------------------------------------------------

class Runner:
    """唯一执行循环内核。

    prepare() → think() → resolve() → persist() → observe()
    """

    def __init__(
        self,
        config: Config,
        tool_registry: ToolRegistry | None = None,
        llm_provider: Any = None,
    ):
        self.config = config
        self.tool_registry = tool_registry or ToolRegistry(config)
        self.llm_provider = llm_provider
        self.hooks = HookManager()
        self.tool_orchestrator = ToolOrchestrator(
            config, self.tool_registry, llm_provider
        )

    def run(self, state: RunState) -> RunState:
        """推进同一个 run 直到完成、中断或终止。"""
        self.hooks.emit("run.start", {"run_id": state.run_id})
        while not state.is_finished:
            state.turn += 1
            next_step = self.think(state)
            state = self.resolve(state, next_step)
            self.persist(state)
            self.hooks.emit("turn.end", {"turn": state.turn, "step": next_step.type})
        self.hooks.emit("run.end", {"run_id": state.run_id, "phase": state.phase})
        return state

    def prepare(
        self,
        run_id: str,
        session_id: str | None = None,
        current_agent: str | None = None,
        current_phase: str | None = None,
    ) -> RunState:
        """组装 active agent / phase / context。"""
        state = RunState(
            run_id=run_id,
            session_id=session_id,
            current_agent=current_agent,
            current_phase=current_phase,
            phase="running" if current_agent else "initializing",
        )
        self.hooks.emit("phase.start", {"agent": current_agent, "phase": current_phase})
        return state

    def think(self, state: RunState) -> NextStep:
        """调 LLM 得到 next step。v1.0 默认返回 continuation。"""
        if self.llm_provider is None:
            # 无 LLM 时，返回 tool_call 以便工具执行可以继续
            return NextStep(type=NextStepType.tool_call)
        # 实际实现：调用 LLM 获取 next step
        # response = self.llm_provider.generate(...)
        # return NextStep.model_validate(response)
        raise NotImplementedError("think() requires LLM provider")

    def resolve(self, state: RunState, next_step: NextStep) -> RunState:
        """分发: final_output / tool_call / phase_handoff / retry / interrupt / abort。"""
        state.updated_at = datetime.now()

        match next_step.type:
            case NextStepType.final_output:
                state.phase = "completed"
                state.output = next_step.output

            case NextStepType.tool_call:
                if next_step.request:
                    call = ToolCallRequest(
                        tool_name=next_step.request.tool_name,
                        params=next_step.request.params,
                    )
                    result = self.tool_orchestrator.execute(state, call)
                    if hasattr(result, "id"):  # Interruption
                        state.phase = "paused"
                    else:
                        # Tool result already written to state by orchestrator
                        pass

            case NextStepType.phase_handoff:
                state.current_agent = next_step.next_agent
                state.current_phase = next_step.next_phase
                state.handoff_payload = {"output": next_step.output}
                state.turn = 0
                self.hooks.emit("handoff", {
                    "to_agent": next_step.next_agent,
                    "to_phase": next_step.next_phase,
                })

            case NextStepType.retry_same:
                pass  # 继续循环，不重置

            case NextStepType.retry_different:
                if next_step.reason:
                    state.errors.append(next_step.reason)

            case NextStepType.replan:
                state.phase = "aborted"
                state.errors.append(next_step.reason or "replan triggered")

            case NextStepType.interruption:
                state.phase = "paused"
                if next_step.request:
                    state.pending_interruptions.append({
                        "tool_name": next_step.request.tool_name,
                        "params": next_step.request.params,
                        "reason": next_step.reason,
                    })

            case NextStepType.abort:
                state.phase = "aborted"
                state.errors.append(next_step.reason or "aborted")

        return state

    def persist(self, state: RunState) -> None:
        """写回 RunState 到文件系统。"""
        state.updated_at = datetime.now()
        run_dir = Path(self._memory_dir()) / "sessions" / state.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "state.json").write_text(
            state.model_dump_json(indent=2), encoding="utf-8"
        )

    def _memory_dir(self) -> str:
        """返回 memory 根目录路径。"""
        project_root = Path(__file__).parent.parent.parent.parent
        return str(project_root / "memory")

    def _execute_tool(self, request: ToolRequest) -> dict:
        """调用 tool_registry 并返回结构化结果。"""
        tool = self.tool_registry.get_tool(request.tool_name)
        if not tool:
            return {
                "tool_name": request.tool_name,
                "success": False,
                "error": f"Unknown tool: {request.tool_name}",
                "duration_ms": 0,
            }
        try:
            result = tool.execute(**request.params)
            return {
                "tool_name": request.tool_name,
                "success": True,
                "output": str(result) if result is not None else "",
                "error": None,
                "duration_ms": 0,
            }
        except Exception as e:
            return {
                "tool_name": request.tool_name,
                "success": False,
                "output": "",
                "error": str(e),
                "duration_ms": 0,
            }
