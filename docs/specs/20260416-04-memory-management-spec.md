# Memory 管理设计规格

> 版本: v1.0.0
> 日期: 2026-04-16
> 状态: 待审批

---

## 1. 需求描述

### 1.1 问题

现有 `MemoryStore` + `MemoryRetrieval` 只是脚手架：
- Embedding 是占位符 `[0.0] * 768`
- 搜索只是 `LIKE` 查询，没有真正的向量检索
- 没有 session 概念，只有 `ExecutionLog` 一张表
- 没有 scenario/phase 维度的 memory 分类
- 与 Phase-Role-Architecture 的 memory 设计（`memory/{scenario}/{phase}/`）不兼容

### 1.2 目标

| 版本 | 能力 | 说明 |
|------|------|------|
| **v1.0** | 三层 memory 结构 + 文件系统存储 | `sessions/`, `scenarios/`, `shared/` 目录结构，JSON/jsonl 存储 |
| **v1.1** | 向量检索 + 嵌入模型 | ChromaDB 真正工作，嵌入模型替换占位符 |
| **v1.2** | 跨 session 知识聚合 | 从执行历史自动提取可复用知识 |

### 1.3 约束

- 文件系统为主，SQLite/ChromaDB 为索引层（不替换文件存储）
- 所有 memory 按 scenario + phase 分类
- 支持 jsonl 流式写入，不丢失任何对话记录
- 可回溯完整历史

---

## 2. 架构设计

### 2.1 三层 Memory 结构

```
memory/
├── sessions/                              # 会话层（用户交互）
│   └── {session_id}/
│       ├── chat.jsonl                     # 所有对话记录（时间序）
│       ├── context.json                   # 当前上下文（活跃摘要）
│       └── metadata.json                  # session 元信息
│
├── scenarios/                             # 场景层（Phase-Role-Architecture）
│   └── {scenario_id}/
│       └── {phase_id}/
│           ├── input.json                 # phase 输入
│           ├── output.json                # phase 输出
│           ├── chat.jsonl                 # phase 对话记录
│           └── artifacts/                 # phase 产生的文件
│
└── shared/                                # 共享层（跨 session 知识）
    ├── skills/                            # 技能进化记录
    ├── knowledge/                         # 长期学习成果
    └── reports/                           # 场景执行报告
```

### 2.2 存储策略

| 数据层 | 存储方式 | 用途 |
|--------|---------|------|
| 文件系统 (JSON/jsonl) | **主存储** | 所有原始数据，可回溯 |
| SQLite | **索引层** | 快速查询（按日期、task_id、session_id） |
| ChromaDB | **向量索引** | 语义相似度检索 |

**设计原则**：文件系统是 truth source，SQLite 和 ChromaDB 只是加速层。即使索引丢失，从文件系统可以重建。

---

## 3. 模块定义

### 3.1 MemoryStore

**文件**: `src/memory/store.py`（重写）

```
职责: 统一管理 sessions/ 和 scenarios/ 的文件系统存储
```

**核心方法**:

| 方法 | 说明 |
|------|------|
| `save_session_message(session_id, role, content)` | 追加消息到 `chat.jsonl` |
| `load_session_messages(session_id, limit=None)` | 加载会话历史 |
| `save_session_context(session_id, context)` | 保存上下文摘要到 `context.json` |
| `load_session_context(session_id)` | 加载上下文摘要 |
| `save_phase_input(scenario_id, phase_id, data)` | 保存 phase 输入 |
| `save_phase_output(scenario_id, phase_id, data)` | 保存 phase 输出 |
| `load_phase_input(scenario_id, phase_id)` | 加载 phase 输入 |
| `load_phase_output(scenario_id, phase_id)` | 加载 phase 输出 |
| `save_phase_message(scenario_id, phase_id, role, content)` | 追加 phase 对话 |
| `save_artifact(scenario_id, phase_id, filename, content)` | 保存 phase 文件 |
| `save_report(scenario_id, report)` | 保存场景报告 |
| `save_knowledge(key, content)` | 保存共享知识 |
| `load_knowledge(key)` | 加载共享知识 |

### 3.2 MemoryIndex (SQLite)

**文件**: `src/memory/index.py`（新增）

```
职责: SQLite 索引层，提供快速查询
```

**表结构**:

```sql
CREATE TABLE session_index (
    id INTEGER PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,              -- "user" | "assistant" | "system"
    content TEXT NOT NULL,           -- 消息摘要（非全文）
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    phase_id TEXT,                   -- 关联的 phase（null = 自由对话）
    scenario_id TEXT                 -- 关联的 scenario（null = 自由对话）
);

CREATE TABLE phase_index (
    id INTEGER PRIMARY KEY,
    scenario_id TEXT NOT NULL,
    phase_id TEXT NOT NULL,
    input_summary TEXT,
    output_summary TEXT,
    status TEXT,                     -- "running" | "completed" | "failed"
    started_at DATETIME,
    completed_at DATETIME
);

CREATE TABLE knowledge_index (
    id INTEGER PRIMARY KEY,
    key TEXT UNIQUE NOT NULL,
    summary TEXT,
    tags TEXT,                       -- JSON 数组
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME
);
```

### 3.3 MemoryRetrieval

**文件**: `src/memory/retrieval.py`（重写）

```
职责: 从 memory 中检索相关内容
```

**检索策略**:

| 场景 | 方法 | 说明 |
|------|------|------|
| 查找最近的对话 | `get_recent_messages(session_id, n)` | 从文件系统读 `chat.jsonl` 最后 n 条 |
| 查找相关 skill | `search_skills(query)` | 先用 FTS，v1.1 切换到向量检索 |
| 查找历史执行 | `search_execution(query, days)` | SQLite `LIKE` 查询 |
| 查找 phase 输出 | `get_phase_output(scenario_id, phase_id)` | 直接读文件 |
| 查找相关知识 | `search_knowledge(query)` | 向量检索（v1.1） |

---

## 4. 数据格式

### 4.1 Session chat.jsonl

每行一条 JSON：

```jsonl
{"ts": "2026-04-16T10:00:00Z", "role": "user", "content": "帮我 review 这段代码"}
{"ts": "2026-04-16T10:00:05Z", "role": "assistant", "content": "好的，我来看看..."}
{"ts": "2026-04-16T10:01:00Z", "role": "system", "content": "phase-5 started: 代码审查"}
```

### 4.2 Session metadata.json

```json
{
  "session_id": "chat-20260416-100000",
  "created_at": "2026-04-16T10:00:00Z",
  "updated_at": "2026-04-16T10:30:00Z",
  "mode": "chat",
  "model": "deepseek-chat",
  "provider": "deepseek",
  "message_count": 42,
  "phases_executed": ["phase-5"]
}
```

### 4.3 Phase output.json

```json
{
  "phase_id": "phase-5",
  "scenario_id": "standard",
  "status": "completed",
  "output": {
    "review_passed": true,
    "verification_done": true,
    "issues_found": ["SQL injection in line 42"],
    "summary": "代码审查通过，发现 1 个安全问题"
  },
  "started_at": "2026-04-16T10:05:00Z",
  "completed_at": "2026-04-16T10:15:00Z"
}
```

### 4.4 Shared knowledge

```json
{
  "key": "tdd-best-practices",
  "title": "TDD 最佳实践",
  "content": "...",
  "tags": ["tdd", "testing", "best-practice"],
  "created_at": "2026-04-16",
  "updated_at": "2026-04-16",
  "source": "phase-3-execution"
}
```

---

## 5. 与现有代码的兼容

### 5.1 保留

- 现有 `ExecutionLog` 表保留（不删除），作为向后兼容
- 现有 ChromaDB 初始化保留，v1.1 启用
- 现有 `MemoryConfig` 配置保留

### 5.2 新增

- 文件系统存储层（`sessions/`, `scenarios/`, `shared/`）
- `MemoryIndex`（新的索引表）
- Session 概念

### 5.3 废弃

- `save_execution_log` → 改用 `save_session_message` + `save_phase_output`
- `load_report` → 改用 `load_session_context` + `load_phase_output`

---

## 6. 文件结构

```
src/
  memory/
    store.py               # 重写，文件系统存储
    index.py               # 新增，SQLite 索引
    retrieval.py           # 重写，检索引擎
    skills.py              # 保留（另有 Skill Spec）
    __init__.py            # 修改，导出新模块
tests/
  memory/
    __init__.py
    test_store.py          # 新增，文件系统存储测试
    test_index.py          # 新增，索引测试
    test_retrieval.py      # 新增，检索测试
memory/                    # 运行时数据目录
  ├── sessions/
  ├── scenarios/
  └── shared/
```

---

## 7. 测试策略

| 测试 | 说明 |
|------|------|
| `test_save_load_session_message` | 消息保存/加载一致 |
| `test_save_load_phase_output` | Phase 输出保存/加载一致 |
| `test_session_metadata` | metadata.json 正确写入 |
| `test_index_session_message` | SQLite 索引正确写入 |
| `test_index_phase_status` | Phase 状态索引正确 |
| `test_retrieval_recent_messages` | 能获取最近消息 |
| `test_retrieval_search_skills` | 能搜索技能（FTS） |

---

## 9. RunState 持久化（v1.0）

### 9.1 运行时会话存储

除 sessions/scenarios/shared 三层结构外，v1.0 Runner 需在运行时将执行状态写入文件系统，用于恢复、审计、回放：

```
memory/sessions/{run_id}/
├── state.json            # RunState 快照（当前阶段、状态码、错误信息）
├── tool_history.jsonl    # 工具调用记录（每行一条 ToolExecutionRecord）
├── turns.jsonl           # 每轮 LLM 对话记录
└── handoffs.jsonl        # phase handoff 记录
```

`Runner.persist()` 必须在以下时机写入：
1. 每次 turn 后写 `state.json`
2. 每次 tool_call 后追加 `tool_history.jsonl`
3. 每次 phase_handoff 后追加 `handoffs.jsonl`

`resume_run_state(run_id)` 从 `state.json` 读取恢复 Runner 状态。

### 9.2 三层上下文边界

运行时上下文分为三层，严格隔离：

| 层级 | 数据类 | 去向 |
|------|--------|------|
| **ModelVisibleContext** | 对话历史、检索到的记忆、当前任务、handoff payload | 可进入 LLM prompt |
| **RuntimeOnlyContext** | Config、ToolRegistry、SkillRegistry、Logger、workspace_handle | 仅供代码与工具层使用，不发给模型 |
| **PersistedRunState** | state.json、tool_history.jsonl、turns.jsonl、handoffs.jsonl | 用于恢复/审计/回放，不等价于对话历史 |

规则：
- 只有 `ModelVisibleContext` 能进入 prompt
- `RuntimeOnlyContext` 只供代码与工具层使用
- `PersistedRunState` 是运行记录，不等同于模型可见的对话历史

---

## 8. 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| jsonl 文件过大 | 读取慢 | 按 session 分割，每 session 一个文件 |
| SQLite 写入冲突 | 索引损坏 | WAL 模式，单写者 |
| 文件权限问题 | 无法写入 | 启动时检查目录权限 |

---

*规格版本: v1.0.0*
*创建日期: 2026-04-16*
