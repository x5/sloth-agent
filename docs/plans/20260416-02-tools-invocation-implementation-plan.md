# Tools Invocation 实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.
> **Spec:** `docs/specs/20260416-02-tools-invocation-spec.md`
> **Module:** #2 — Tools Invocation（工具调用机制）
> v0.1.0 实现状态: ToolRegistry / Executor / HallucinationGuard / 6 个内置工具已实现，58 tests pass
> v0.1.0 实现文件: `src/sloth_agent/core/tools/` (tool_registry.py, executor.py, hallucination_guard.py, builtin/)

**Goal:** Complete the v1.0 tools invocation runtime — IntentResolver, StreamProcessor, RollbackManager, Function Calling adapter, and second-phase builtin tools. Phase 1 core (Tool base, Registry, HallucinationGuard, RiskGate, Executor, Formatter, Orchestrator, builtin file/shell/search) is already implemented.

**Tech Stack:** Python 3.10+, pydantic, pytest, asyncio (existing)

---

## Task 1: IntentResolver

**Spec:** §4.1
**Files:**
- Create: `src/sloth_agent/core/tools/intent_resolver.py`
- Test: `tests/core/tools/test_intent_resolver.py`

### Step 1: Write the failing test

```python
# tests/core/tools/test_intent_resolver.py

from sloth_agent.core.tools.intent_resolver import IntentResolver
from sloth_agent.core.tools.tool_registry import ToolRegistry


def _make_resolver():
    registry = ToolRegistry()
    return IntentResolver(registry=registry)


def test_parse_direct_call():
    resolver = _make_resolver()
    result = resolver.resolve('@tool:read_file path="src/main.py"')
    assert result is not None
    assert result.tool_name == "read_file"
    assert result.params["path"] == "src/main.py"


def test_keyword_match_read():
    resolver = _make_resolver()
    result = resolver.resolve("读取 src/main.py 的内容")
    assert result is not None
    assert result.tool_name == "read_file"


def test_keyword_match_run():
    resolver = _make_resolver()
    result = resolver.resolve("运行 pytest tests/")
    assert result is not None
    assert result.tool_name == "run_command"


def test_no_match():
    resolver = _make_resolver()
    result = resolver.resolve("今天天气不错")
    assert result is None
```

### Step 2: Run test to verify it fails

```bash
uv run pytest tests/core/tools/test_intent_resolver.py -v
```

Expected: FAIL with ModuleNotFoundError

### Step 3: Write minimal implementation

```python
# src/sloth_agent/core/tools/intent_resolver.py

"""Intent resolver: parse user/LLM intent into tool calls."""

import re
from typing import Any

from sloth_agent.core.tools.models import ToolCallRequest
from sloth_agent.core.tools.tool_registry import ToolRegistry


class IntentResolver:
    """解析用户/LLM 意图，路由到对应工具。"""

    KEYWORD_RULES = {
        r"^(读取|打开|查看|read)\s+.*文件?": ("read_file", {"path": 1}),
        r"^(写入|创建|保存|write)\s+.*文件?": ("write_file", {"path": 1}),
        r"^(搜索|查找|search|grep)\s+": ("search", {"pattern": 1}),
        r"^(运行|执行|run|execute)\s+": ("run_command", {"command": 1}),
    }

    TOOL_CALL_PATTERN = re.compile(r"@tool:(\w+)\s+(.*)")
    PARAM_PATTERN = re.compile(r'(\w+)="([^"]*)"')

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def resolve(self, intent: str) -> ToolCallRequest | None:
        """解析意图，返回工具调用请求。"""
        # 1. Check structured @tool:xxx
        direct = self._parse_direct_call(intent)
        if direct:
            return direct

        # 2. Keyword match
        keyword = self._keyword_match(intent)
        if keyword:
            return keyword

        # 3. No match — caller may fall back to LLM analysis
        return None

    def _parse_direct_call(self, intent: str) -> ToolCallRequest | None:
        match = self.TOOL_CALL_PATTERN.match(intent)
        if not match:
            return None
        tool_name = match.group(1)
        params_str = match.group(2)
        params = dict(self.PARAM_PATTERN.findall(params_str))
        return ToolCallRequest(tool_name=tool_name, params=params, source="direct")

    def _keyword_match(self, intent: str) -> ToolCallRequest | None:
        for pattern, (tool_name, _) in self.KEYWORD_RULES.items():
            if re.search(pattern, intent, re.IGNORECASE):
                return ToolCallRequest(
                    tool_name=tool_name,
                    params={"intent": intent},
                    source="keyword",
                    confidence=0.7,
                )
        return None
```

### Step 4: Run test to verify it passes

```bash
uv run pytest tests/core/tools/test_intent_resolver.py -v
```

Expected: PASS (all 4 tests)

### Step 5: Commit

```bash
git add src/sloth_agent/core/tools/intent_resolver.py tests/core/tools/test_intent_resolver.py
git commit -m "feat(tools): add IntentResolver for intent-to-tool routing"
```

---

## Task 2: StreamProcessor

**Spec:** §5.5
**Files:**
- Create: `src/sloth_agent/core/tools/stream_processor.py`
- Test: `tests/core/tools/test_stream_processor.py`

### Step 1: Write the failing test

```python
# tests/core/tools/test_stream_processor.py

import asyncio
from dataclasses import dataclass

from sloth_agent.core.tools.stream_processor import StreamProcessor


@dataclass
class FakeChunk:
    type: str
    content: str = ""
    tool_name: str = ""
    tool_args: dict = None
    error: str = ""
    usage: dict = None


async def test_text_chunk_passthrough():
    proc = StreamProcessor()
    chunks = [FakeChunk(type="text", content="Hello")]
    events = [e async for e in proc.process_stream(iter(chunks))]
    assert len(events) == 1
    assert events[0].type == "text"
    assert events[0].content == "Hello"


async def test_done_event():
    proc = StreamProcessor()
    chunks = [FakeChunk(type="done", usage={"tokens": 100})]
    events = [e async for e in proc.process_stream(iter(chunks))]
    assert len(events) == 1
    assert events[0].type == "done"


async def test_error_event():
    proc = StreamProcessor()
    chunks = [FakeChunk(type="error", error="Something broke")]
    events = [e async for e in proc.process_stream(iter(chunks))]
    assert len(events) == 1
    assert events[0].type == "error"
```

### Step 2: Run test to verify it fails

```bash
uv run pytest tests/core/tools/test_stream_processor.py -v
```

Expected: FAIL

### Step 3: Write minimal implementation

```python
# src/sloth_agent/core/tools/stream_processor.py

"""Stream processor for LLM streaming output with tool call interception."""

from dataclasses import dataclass
from typing import AsyncIterator


@dataclass
class OutputEvent:
    type: str
    content: str = ""
    tool_name: str = ""
    tool_result: dict | None = None
    error: str = ""
    usage: dict | None = None


class StreamProcessor:
    """处理 LLM streaming 输出，拦截工具调用并执行。

    v1.0: 纯事件转换层，不直接执行工具（执行由 ToolOrchestrator 负责）。
    """

    async def process_stream(self, stream: AsyncIterator) -> AsyncIterator[OutputEvent]:
        """将原始 chunk 流转换为 OutputEvent 流。"""
        async for chunk in stream:
            match getattr(chunk, "type", ""):
                case "text":
                    yield OutputEvent(type="text", content=getattr(chunk, "content", ""))
                case "tool_call_start":
                    yield OutputEvent(
                        type="status",
                        content=f"Calling {getattr(chunk, 'tool_name', '')}..."
                    )
                case "tool_call_end":
                    yield OutputEvent(
                        type="tool_result",
                        tool_name=getattr(chunk, "tool_name", ""),
                        tool_result=getattr(chunk, "tool_args", None),
                    )
                case "error":
                    yield OutputEvent(type="error", error=getattr(chunk, "error", ""))
                case "done":
                    yield OutputEvent(type="done", usage=getattr(chunk, "usage", None))
                case _:
                    yield OutputEvent(type="unknown")
```

### Step 4: Run test to verify it passes

```bash
uv run pytest tests/core/tools/test_stream_processor.py -v
```

Expected: PASS

### Step 5: Commit

```bash
git add src/sloth_agent/core/tools/stream_processor.py tests/core/tools/test_stream_processor.py
git commit -m "feat(tools): add StreamProcessor for LLM streaming interception"
```

---

## Task 3: RollbackManager & Function Calling Adapter

**Spec:** §7.2 (Rollback), §6.1 (Function Calling)
**Files:**
- Create: `src/sloth_agent/core/tools/rollback.py`
- Create: `src/sloth_agent/core/tools/function_calling.py`
- Test: `tests/core/tools/test_rollback.py`
- Test: `tests/core/tools/test_function_calling.py`

### Step 1: Write the failing test

```python
# tests/core/tools/test_rollback.py

from dataclasses import dataclass
from sloth_agent.core.tools.rollback import RollbackManager


@dataclass
class FakeTool:
    name: str
    rollback_strategy: str = "none"


@dataclass
class FakeResult:
    success: bool = False
    output: str = ""


def test_no_rollback_strategy():
    mgr = RollbackManager()
    result = mgr.rollback(FakeResult(), FakeTool(rollback_strategy="none"))
    assert result.success is False
    assert "no rollback" in result.reason.lower()


def test_auto_rollback_write_file():
    mgr = RollbackManager()
    result = mgr.rollback(
        FakeResult(output="wrote file.txt"),
        FakeTool(name="write_file", rollback_strategy="auto"),
    )
    # Should suggest deletion of the written file
    assert result.requires_user_action or result.success
```

```python
# tests/core/tools/test_function_calling.py

from sloth_agent.core.tools.function_calling import build_function_schemas
from sloth_agent.core.tools.tool_registry import ToolRegistry


def test_build_function_schemas():
    registry = ToolRegistry()
    schemas = build_function_schemas(registry)
    # Should have at least the registered builtin tools
    names = [s["name"] for s in schemas]
    assert "read_file" in names
    assert "write_file" in names
    assert "run_command" in names
```

### Step 2: Run test to verify it fails

```bash
uv run pytest tests/core/tools/test_rollback.py tests/core/tools/test_function_calling.py -v
```

Expected: FAIL

### Step 3: Write minimal implementation

```python
# src/sloth_agent/core/tools/rollback.py

"""Rollback manager for tool execution failures."""

from dataclasses import dataclass


@dataclass
class RollbackResult:
    success: bool
    reason: str = ""
    requires_user_action: bool = False
    suggestion: str = ""


class RollbackManager:
    """管理工具执行失败后的回滚。"""

    def rollback(self, result, tool) -> RollbackResult:
        strategy = getattr(tool, "rollback_strategy", "none")

        if strategy == "none":
            return RollbackResult(success=False, reason="No rollback strategy configured")

        if strategy == "auto":
            return self._auto_rollback(result, tool)

        if strategy == "manual":
            return RollbackResult(
                success=False,
                reason="Manual rollback required",
                requires_user_action=True,
                suggestion=f"Please manually revert changes from tool: {tool.name}",
            )

        return RollbackResult(success=False, reason=f"Unknown strategy: {strategy}")

    def _auto_rollback(self, result, tool) -> RollbackResult:
        name = getattr(tool, "name", "")
        if name == "write_file":
            return RollbackResult(
                success=True,
                reason="Auto-rollback: delete created file",
                suggestion="Delete the file that was just created",
            )
        elif name == "run_command":
            return RollbackResult(
                success=False,
                reason="Cannot auto-rollback shell command",
                requires_user_action=True,
                suggestion="Command output cannot be automatically reverted",
            )
        return RollbackResult(
            success=False,
            reason=f"No auto-rollback for tool: {name}",
        )
```

```python
# src/sloth_agent/core/tools/function_calling.py

"""OpenAI-compatible function calling schema builder."""

from sloth_agent.core.tools.tool_registry import ToolRegistry


def build_function_schemas(registry: ToolRegistry) -> list[dict]:
    """将工具注册为 OpenAI-compatible function calling schema。"""
    schemas = []
    for tool in registry.list_all():
        params = {}
        required = []
        for param_name, param_def in getattr(tool, "params", {}).items():
            if isinstance(param_def, dict):
                params[param_name] = {
                    "type": param_def.get("type", "string"),
                    "description": param_def.get("description", ""),
                }
                if param_def.get("required", True):
                    required.append(param_name)
            else:
                params[param_name] = {"type": "string", "description": ""}

        schemas.append({
            "name": tool.name,
            "description": tool.description,
            "parameters": {
                "type": "object",
                "properties": params,
                "required": required,
            },
        })
    return schemas
```

### Step 4: Run test to verify it passes

```bash
uv run pytest tests/core/tools/test_rollback.py tests/core/tools/test_function_calling.py -v
```

Expected: PASS

### Step 5: Commit

```bash
git add src/sloth_agent/core/tools/rollback.py src/sloth_agent/core/tools/function_calling.py tests/core/tools/test_rollback.py tests/core/tools/test_function_calling.py
git commit -m "feat(tools): add RollbackManager and function calling schema builder"
```

---

## Task 4: Second-Phase Builtin Tools

**Spec:** §10.5 (第二阶段工具)
**Files:**
- Create: `src/sloth_agent/core/tools/builtin/web.py`
- Create: `src/sloth_agent/core/tools/builtin/test_runner.py`
- Create: `src/sloth_agent/core/tools/builtin/coverage.py`
- Test: `tests/core/tools/test_web.py`
- Test: `tests/core/tools/test_test_runner.py`
- Test: `tests/core/tools/test_coverage.py`

### Step 1: Write the failing test

```python
# tests/core/tools/test_web.py

from sloth_agent.core.tools.builtin.web import WebFetchTool, WebSearchTool


def test_web_fetch_tool_exists():
    tool = WebFetchTool()
    assert tool.name == "web_fetch"
    assert tool.risk_level >= 2


def test_web_search_tool_exists():
    tool = WebSearchTool()
    assert tool.name == "web_search"
```

```python
# tests/core/tools/test_test_runner.py

from sloth_agent.core.tools.builtin.test_runner import TestRunnerTool


def test_test_runner_exists():
    tool = TestRunnerTool()
    assert tool.name == "test_runner"


def test_test_runner_runs_pytest(tmp_path):
    tool = TestRunnerTool()
    test_file = tmp_path / "test_dummy.py"
    test_file.write_text("def test_pass(): assert True\n")
    result = tool.execute(test_dir=str(tmp_path))
    assert "passed" in result.lower() or "pass" in result.lower()
```

```python
# tests/core/tools/test_coverage.py

from sloth_agent.core.tools.builtin.coverage import CoverageCheckTool


def test_coverage_check_exists():
    tool = CoverageCheckTool()
    assert tool.name == "coverage_check"
```

### Step 2: Run test to verify it fails

```bash
uv run pytest tests/core/tools/test_web.py tests/core/tools/test_test_runner.py tests/core/tools/test_coverage.py -v
```

Expected: FAIL

### Step 3: Write minimal implementation

```python
# src/sloth_agent/core/tools/builtin/web.py

"""Web tools: web_fetch, web_search."""

import urllib.request
import urllib.parse
import json

from sloth_agent.core.tools.tool_registry import Tool


class WebFetchTool(Tool):
    name = "web_fetch"
    description = "Fetch content from a URL."
    group = "web"
    risk_level = 2
    permission = "plan_approval"

    params = {
        "url": {"type": "str", "required": True, "description": "URL to fetch"},
        "timeout": {"type": "int", "required": False, "default": "30"},
    }

    def execute(self, url: str, timeout: int = 30, **kwargs) -> str:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SlothAgent/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")[:10000]
        except Exception as e:
            return f"Error fetching {url}: {e}"

    def get_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {"type": "object", "properties": self.params, "required": ["url"]},
        }


class WebSearchTool(Tool):
    name = "web_search"
    description = "Search the web via an external API."
    group = "web"
    risk_level = 2
    permission = "plan_approval"

    params = {
        "query": {"type": "str", "required": True, "description": "Search query"},
    }

    def execute(self, query: str, **kwargs) -> str:
        # v1.0: return a placeholder suggesting WebFetch to a search API
        return f"Web search for '{query}' — configure a search provider in tools.yaml"

    def get_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {"type": "object", "properties": self.params, "required": ["query"]},
        }
```

```python
# src/sloth_agent/core/tools/builtin/test_runner.py

"""Test runner tool: execute test suites."""

import subprocess

from sloth_agent.core.tools.tool_registry import Tool


class TestRunnerTool(Tool):
    name = "test_runner"
    description = "Run test suite (pytest by default)."
    group = "sloth"
    risk_level = 2
    permission = "plan_approval"
    rollback_strategy = "none"

    params = {
        "test_dir": {"type": "str", "required": False, "default": "tests"},
        "extra_args": {"type": "str", "required": False, "default": ""},
    }

    def execute(self, test_dir: str = "tests", extra_args: str = "", **kwargs) -> str:
        cmd = f"pytest {test_dir} -v {extra_args}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        return f"Exit code: {result.returncode}\n{result.stdout}\n{result.stderr}"

    def get_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {"type": "object", "properties": self.params, "required": []},
        }
```

```python
# src/sloth_agent/core/tools/builtin/coverage.py

"""Coverage check tool."""

import subprocess

from sloth_agent.core.tools.tool_registry import Tool


class CoverageCheckTool(Tool):
    name = "coverage_check"
    description = "Check test coverage percentage."
    group = "sloth"
    risk_level = 1
    permission = "auto"

    params = {
        "source": {"type": "str", "required": False, "default": "src"},
        "threshold": {"type": "int", "required": False, "default": "80"},
    }

    def execute(self, source: str = "src", threshold: int = 80, **kwargs) -> str:
        cmd = f"pytest --cov={source} --cov-report=term-missing"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        return f"Exit code: {result.returncode}\n{result.stdout}\n{result.stderr}"

    def get_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {"type": "object", "properties": self.params, "required": []},
        }
```

### Step 4: Register new tools in `__init__.py`

Update `src/sloth_agent/core/tools/__init__.py` to export the new tools.

### Step 5: Run test to verify it passes

```bash
uv run pytest tests/core/tools/test_web.py tests/core/tools/test_test_runner.py tests/core/tools/test_coverage.py -v
```

Expected: PASS

### Step 6: Commit

```bash
git add src/sloth_agent/core/tools/builtin/web.py src/sloth_agent/core/tools/builtin/test_runner.py src/sloth_agent/core/tools/builtin/coverage.py tests/core/tools/test_web.py tests/core/tools/test_test_runner.py tests/core/tools/test_coverage.py src/sloth_agent/core/tools/__init__.py
git commit -m "feat(tools): add web_fetch, test_runner, and coverage_check builtin tools"
```

---

## Summary

| Task | Deliverable | Tests | Status |
|------|------------|-------|--------|
| 1 | IntentResolver | 4 | Pending |
| 2 | StreamProcessor | 3 | Pending |
| 3 | RollbackManager + Function Calling | 3 | Pending |
| 4 | Second-phase builtin tools (web, test, coverage) | 5 | Pending |

**Total: 15 new tests across 4 tasks**

Phase 1 (already implemented): Tool base, Registry, HallucinationGuard, RiskGate, Executor, Formatter, Orchestrator, builtin file/shell/search, configs.

---

## 合并说明

本 plan 于 2026-04-17 合并了 `20260417-v10-tool-runtime-implementation-plan.md` 的内容：

- v10 plan 的 Phase 1 组件（models, HallucinationGuard, RiskGate, Executor, Formatter, ToolOrchestrator, 6 核心工具, runner tool_call 分支对接）已在 Task 1 中实现
- v10 plan 作为追溯记录保留在此，原始步骤 2.1-2.10 对应关系：
  - 步骤 2.1 (models) → 已实现
  - 步骤 2.2 (Tool metadata 扩展) → 已实现
  - 步骤 2.3 (HallucinationGuard) → 已实现
  - 步骤 2.4 (RiskGate) → 已实现
  - 步骤 2.5 (Executor) → 已实现
  - 步骤 2.6 (ResultFormatter) → 已实现
  - 步骤 2.7 (ToolOrchestrator) → 已实现
  - 步骤 2.8 (6 核心工具) → 已实现
  - 步骤 2.9 (Runner tool_call 分支) → 已实现
  - 步骤 2.10 (单元测试) → 已实现
