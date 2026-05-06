# Tasks: Memory 架构 — 从会话存储到知识积累

> 日期: 2026-05-07
> 关联 proposal: docs/changes/memory-architecture/proposal.md
> 关联 delta: docs/changes/memory-architecture/delta.md

---

## Iter-12: Memory Foundation（5 天）

### Task M.1: Memory 数据库 + ORM（½ 天）

**文件：** `src/sloth_agent/core/memory/database.py` (new)、`src/sloth_agent/core/memory/models.py` (new)

- SQLite FTS5 全文索引（facts 表）
- chromadb collection 初始化（`sloth_semantic_memory`）
- `Episodic`、`SemanticFact`、`FactConfidence` ORM/collection models
- `memory/` 目录结构初始化（chroma/ + fts.db + episodes.jsonl）
- embedding 函数（all-MiniLM-L6-v2 默认，可配置）

### Task M.2: Ingest Pipeline（1 天）

**文件：** `src/sloth_agent/core/memory/ingestor.py` (new)
**测试：** `tests/core/memory/test_ingestor.py` (new)

- `MemoryIngestor`：
  - `ingest_session(session_id)` — 加载 Message 表 → LLM 生成摘要 + key_points + entities → 写入 Episodic
  - `consolidate(limit=50)` — 从 Episodic 提取跨 session 事实 → 写入 Semantic → 更新索引
- LLM 调用使用 `LLMAdapter`（Desktop）或 mock（core 测试）
- 去重：相同 key_point 不重复写入 Episodic

**验证：**
- 摄入一个 session → Episodic 表有记录
- consolidate 2 个相似 session → Semantic 有一条合并的 fact
- `uv run pytest tests/core/memory/test_ingestor.py -v` 通过

### Task M.3: Confidence Scoring（½ 天）

**文件：** `src/sloth_agent/core/memory/confidence.py` (new)
**测试：** `tests/core/memory/test_confidence.py` (new)

- `ConfidenceScorer`：
  - `compute(fact, current_time) → float` — Ebbinghaus 遗忘曲线
  - `reinforce(fact_id)` — 被新 source 确认时加分
  - `weaken(fact_id, contradiction_source)` — 被矛盾信息质疑时减分
  - `get_stale_threshold() → 0.3` — 低于此值标记 stale
- 衰减速率 λ 按 fact 类型不同（架构 0.01/天、bug 0.1/天、临时 0.5/天）

**验证：** 新 fact score=0.85，30 天后未确认 score≈0.65，被 reinforce 后回到 0.82

### Task M.4: Hybrid Search（1 天）

**文件：** `src/sloth_agent/core/memory/search.py` (new)
**测试：** `tests/core/memory/test_search.py` (new)

- `HybridSearch`：
  - `search_bm25(query, top_k=20)` — SQLite FTS5 全文搜索
  - `search_vector(query, top_k=20)` — chromadb embedding 语义搜索
  - `search_hybrid(query, top_k=10)` — RRF 融合三路结果
- RRF 参数：k=60
- 结果 `MemoryResult`: fact_id, content, score, source(哪种搜索命中), confidence

**验证：**
- 关键词搜索返回包含该词的结果
- 语义搜索返回不包含关键词但意思相近的结果
- RRF 融合后结果包含两种搜法都命中的排在前面

### Task M.5: Context Injection（½ 天）

**文件：** `src/sloth_agent/core/memory/injector.py` (new)
**测试：** `tests/core/memory/test_injector.py` (new)

- `MemoryContextInjector.inject(system_prompt, user_message) → enriched_prompt`
- 用 user_message 做 hybrid search → top 5 facts (score > 0.5)
- 格式化为 `[Relevant Memory]` block
- 注入到 system_prompt 顶部

**验证：**
- 空 memory → system_prompt 不变
- 有相关 memory → 顶部出现 `[Relevant Memory]` block，含 confidence 标注

### Task M.6: Memory API + Desktop 接线（1 天）

**文件：** `backend/app/routers/memory.py` (new)
**测试：** `backend/tests/integration/test_memory.py` (new)

- `POST /api/memory/sessions/{id}/ingest` — 摄入 session
- `POST /api/memory/consolidate` — 手动 consolidation
- `GET /api/memory/search?q=&top_k=10` — hybrid search
- `GET /api/memory/facts/{id}` — 单条 fact
- BrainstormEngine 接入 `MemoryContextInjector`（在 `_agent_turn` 的 prompt 构建前注入）
- 可选：前端 Memory tab 基础展示（事实列表 + 搜索框）

**验证：**
- 创建 session → 讨论 → end → POST /ingest → 有 Episodic 记录
- POST /consolidate → 提取 Semantic fact
- GET /search?q=Redis → 返回相关 fact
- Brainstorm 模式 → system prompt 含 [Relevant Memory]

### Iter-12 验收标准

- [ ] Episodic Memory：session 结束可摄入，生成摘要 + key_points + entities
- [ ] Semantic Memory：跨 session consolidation 提取事实
- [ ] Confidence scoring：Ebbinghaus 曲线自动衰减 + reinforcement
- [ ] Hybrid search：BM25 + vector → RRF 融合
- [ ] Context injection：Agent prompt 自动注入相关记忆
- [ ] API 可用：ingest / consolidate / search / facts
- [ ] 原有测试全通过

---

## Iter-13: Memory Advanced（5 天）

### Task M.7: Knowledge Graph（1½ 天）

**文件：** `src/sloth_agent/core/memory/graph.py` (new)
`tests/core/memory/test_graph.py` (new)

- `EntityStore`：entity CRUD + 属性存储
- `RelationStore`：三元组存储 (from, to, type, confidence, sources)
- `GraphTraversal`（networkx）：
  - `walk(entity, relation_type, max_hops=2)` → 子图
  - `downstream(entity)` → 依赖链
  - `upstream(entity)` → 被依赖链
- `EntityExtractor`：从 Episodic/Semantic 提取实体 + 关系

### Task M.8: Supersession + Full Trace（½ 天）

**文件：** `src/sloth_agent/core/memory/supersession.py` (new)

- `SupersessionManager`：
  - `supersede(old_fact_id, new_fact_id)` — 标记旧 fact，链接新 fact
  - `get_active_version(entity_key)` — 返回当前 active fact
  - `get_history(entity_key)` — 返回完整 provenance chain
- 查询 API 支持 `include_superseded=true`

### Task M.9: Crystallization（1 天）

**文件：** `src/sloth_agent/core/memory/crystallizer.py` (new)
`tests/core/memory/test_crystallizer.py` (new)

- `Crystallizer`：
  - `crystallize(session_id)` — Brainstorm → digest → wiki + facts + graph
  - LLM 生成 structured digest（question/findings/decision/alternatives/lessons/entities）
  - lessons 提取为 Semantic facts
  - entities 写入 knowledge graph
- API：`POST /api/memory/crystallize/{session_id}`

### Task M.10: Procedural Memory（1 天）

**文件：** `src/sloth_agent/core/memory/procedural.py` (new)
`tests/core/memory/test_procedural.py` (new)

- `PatternExtractor`：
  - 聚类相似的 tool_call 序列（按最近 N 个 session）
  - 高频模式 → 生成 `Procedure`（name/steps/trigger_condition/success_rate）
- `ProcedureStore`：procedure CRUD + usage tracking
- `ProcedureSuggester`：匹配 trigger_condition → 注入 procedure 到 agent prompt

### Task M.11: Self-Healing + Automation（1 天）

**文件：** `src/sloth_agent/core/memory/maintenance.py` (new)

- `LintPass`：检查 broken references、orphan entities、stale facts
- `AutoHeal`：修复可自动修复的问题（broken refs → 标记、orphans → 链接或归档）
- `RetentionDecay`：scheduled task，更新所有 fact 的 current_score，归档低于阈值的
- `ScheduledTasks`：daily/weekly 定时任务注册（接 EventBus scheduled events）

**自动化连接：**
- 接入 Iter-9 hooks：`on_session_end` → ingest
- 接入 Iter-10 EventBus：订阅 `session.completed` → auto-ingest
- 定时任务：`on_schedule` → consolidation + lint + decay

### Iter-13 验收标准

- [ ] Knowledge graph：实体 + 关系提取 + 图遍历（1-2 hop）
- [ ] Supersession：新 fact 可 supersede 旧 fact，旧 fact 保留 provenance
- [ ] Crystallization：Brainstorm → structured digest + new facts + graph update
- [ ] Procedural memory：从重复序列提取 workflow、支持 trigger 匹配
- [ ] Self-healing：lint→auto-fix + 定时 decay→archive
- [ ] Event-driven：session end → auto-ingest, schedule → consolidation
- [ ] API 全可用：graph / crystallize / procedures / lint / stats
- [ ] 原有测试全通过
