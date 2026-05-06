# Delta: Memory 架构 — 从会话存储到知识积累

> 关联模块: memory/spec.md, session/spec.md, events/spec.md, brainstorm/spec.md
> 日期: 2026-05-07
> 参考: ADK BaseMemoryService、Karpathy LLM Wiki、agentmemory

---

## MODIFIED Requirements — memory/spec.md（全量重写）

### REQ-MEM-010: Consolidation Tiers（Iter-12）

```
四级记忆模型：

Working Memory（工作记忆）
- 范围: 当前 session 的 Message 流
- 存储: Message 表（现有）
- 生命周期: session 开始→结束
- 查询: 直接 SQL（现有 _load_history）

Episodic Memory（情节记忆）
- 范围: 单个 session 的自动摘要
- 存储: memory_store.episodes 表
- 字段: session_id, summary, key_points(list), entities(list), quality_score, created_at
- 触发: on_session_end hook → auto-ingest
- 生命周期: 永久，但有 retention decay
- 查询: 按 session_id / 关键词 / 时间范围

Semantic Memory（语义记忆）
- 范围: 跨 session 的事实/知识
- 存储: memory_store.facts 表 + chromadb collection
- 字段: fact_id, content, source_sessions(list), confidence, entity_tags, superseded_by, created_at, last_confirmed_at
- 触发: consolidation 进程（从 Episodic 中提取）
- 生命周期: 永久，confidence 随时间衰减
- 查询: hybrid search (BM25 + vector)

Procedural Memory（程序记忆）— Iter-13
- 范围: 从重复的 Semantic 中提取的 workflow/pattern
- 存储: memory_store.procedures 表
- 字段: procedure_id, name, steps(list), trigger_condition, success_rate, usage_count
- 查询: 按触发条件匹配
```

### REQ-MEM-011: Confidence Scoring（Iter-12）

```
每条 fact 的置信度算法：

score = base_confidence × e^(-λ × days_since_last_confirm) + Σ(reinforcement_bonus)

参数:
- base_confidence: 从 source quality 计算（人工确认=1.0，LLM生成=0.7，推断=0.4）
- λ: 衰减速率（架构决策=0.01/天，bug=0.1/天，临时信息=0.5/天）
- reinforcement_bonus: 每次被新 source 确认 +0.1，每次被 contradiction 削弱 -0.15
- score 范围 [0, 1]，<0.3 标记 stale，<0.1 归档

FactConfidence:
    fact_id, base_confidence, decay_rate(λ), last_confirmed_at,
    reinforcement_count, contradiction_count, current_score(computed)
```

### REQ-MEM-012: Hybrid Search（Iter-12）

```
三路检索 + RRF 融合：

1. BM25 (SQLite FTS5)
   - 对 facts.content 建 FTS5 全文索引
   - 支持 stemming + synonym expansion
   - 返回 top_k=20

2. Vector (chromadb)
   - 对 facts.content 做 embedding (all-MiniLM-L6-v2 默认)
   - collection: "sloth_semantic_memory"
   - 返回 top_k=20

3. Graph Traversal (Iter-13)
   - 基于 entity-relationship 三元组
   - 从 query 中提取的 entity 出发，走 1-2 跳
   - 返回 top_k=10

Fusion: Reciprocal Rank Fusion (k=60)
    RRF_score(d) = Σ 1/(k + rank_i(d))
    对每个 document，累加它在三路中的 RRF 分数，取 top_k=10

MemoryRetrieval:
    search(query, top_k=10, filters={}) → list[MemoryResult]
    inject_context(agent_prompt, query) → str  (拼接后的 prompt 片段)
```

### REQ-MEM-013: Ingest Pipeline（Iter-12）

```
MemoryIngestor:

    async def ingest_session(session_id) -> IngestResult:
        """session 结束后的自动摄入"""

        1. Load raw messages from Message 表
        2. LLM 生成 session summary + key_points + entities
        3. 写入 Episodic Memory
        4. 对每个 key_point 尝试 merge 到 Semantic Memory
        5. 更新索引 (FTS5 + chromadb)

    async def consolidate(limit=50) -> ConsolidateResult:
        """定期 consolidation 进程"""

        1. 选取最近 N 个未处理的 Episodic
        2. LLM 提取跨 session 的共同事实 → Semantic
        3. 检测重复/矛盾的 Semantic → supersession
        4. 更新 confidence scores
        5. 清理 stale facts (confidence < 0.1)

触发方式:
- Iter-12: POST /api/memory/ingest/{session_id} + POST /api/memory/consolidate
- Iter-13: hook on_session_end → auto-ingest；scheduled task → auto-consolidate
```

### REQ-MEM-014: Context Injection（Iter-12）

```
MemoryContextInjector:

    注入点: Agent system prompt 构建时（BrainstormEngine._agent_turn）

    格式:
    [Relevant Memory]
    - {fact_1} (confidence: 0.92, last confirmed: 3 days ago)
    - {fact_2} (confidence: 0.75, last confirmed: 12 days ago, may be stale)

    逻辑:
    1. 用当前 user message 做 hybrid search
    2. 取 top 5 facts (score > 0.5)
    3. 格式化为 [Relevant Memory] block
    4. 注入到 system prompt 顶部
```

---

## ADDED Requirements — Iter-13 Advanced

### REQ-MEM-020: Knowledge Graph（Iter-13）

```
实体提取 + 类型化关系：

Entity:
    entity_id, name, type(project|library|concept|person|file|decision),
    attributes(json), first_seen_at, last_seen_at

Relationship:
    from_entity, to_entity, relation_type(uses|depends_on|contradicts|caused|fixed|supersedes),
    confidence, source_facts(list), created_at

GraphTraversal:
    walk(entity, relation_type, max_hops=2) → list[Entity]
    downstream(entity) → 所有依赖链
    upstream(entity) → 所有被依赖链

查询示例: "升级 Redis 有什么影响" →
  1. 找到 Redis entity
  2. walk_downstream(Redis, "depends_on" or "uses")
  3. 返回所有受影响的服务/模块
```

### REQ-MEM-021: Supersession + Full Trace（Iter-13）

```
Supersession 模型：

当新信息推翻旧声明时：
- 旧 fact 不删除，置 superseded_by = new_fact_id
- 新 fact.supersedes = old_fact_id
- 保留完整 provenance chain
- 查询时默认返回 active facts，可选 include_superseded=true

例：
  fact_1: "User auth uses JWT" (created 2026-05-01)
  fact_2: "User auth uses Session tokens" (created 2026-05-15, supersedes=fact_1)

  查询 "how does auth work?" → 返回 fact_2（active），附注："previously: JWT (2026-05-01)"
```

### REQ-MEM-022: Crystallization（Iter-13）

```
Crystallization: Brainstorm 讨论 → 结构化 digest → wiki 页面

Crystallizer:
    async def crystallize(session_id) -> CrystallizationResult:
        """将完成的 Brainstorm 蒸馏为结构化知识"""

        1. 加载 session 全部 messages
        2. LLM 生成:
           - question: 核心问题是什么
           - findings: 发现了什么（3-5 条）
           - decision: 结论/决策
           - alternatives: 考虑过的替代方案
           - lessons: 可复用的经验教训
           - entities: 涉及的项目/技术/概念
        3. digest 存为 Markdown 页面
        4. lessons 提取为独立 Semantic facts
        5. entities 写入 knowledge graph

输出: wiki 页面 + 强化 knowledge graph + 新 Semantic facts
```

### REQ-MEM-023: Procedural Memory（Iter-13）

```
从重复的 Semantic 事实中提取 workflow：

Procedure:
    name: "Fix Bug Workflow"
    trigger_condition: "user reports a bug or error"
    steps:
      - grep_repo(error_message) → locate source
      - read_range(file, start, end) → understand context
      - propose fix → validate against tests
    source_sessions: [sess_1, sess_2, sess_5]  # 3 次相似的 bug fix 流程
    success_rate: 0.85
    usage_count: 12

提取逻辑:
    PatternExtractor:
        1. 聚类相似的 tool_call 序列
        2. 对高频模式生成 Procedure
        3. Agent 遇到 trigger_condition 时自动建议 Procedure
```

### REQ-MEM-024: Self-Healing + Event-Driven Automation（Iter-13）

```
自动维护任务（接 Iter-9 hooks + Iter-10 EventBus）:

on_session_end:
    → MemoryIngestor.ingest_session(session_id)

on_crystallization_complete:
    → Crystallizer.crystallize(session_id)
    → update knowledge graph
    → consolidate conflicting facts

on_schedule (daily/weekly):
    → LintPass: 检查 broken references, orphan entities, stale facts
    → AutoHeal: 修复可自动修复的问题
    → RetentionDecay: 更新所有 fact 的 current_score
    → StaleArchive: 归档 confidence < 0.1 的 facts

on_query (threshold):
    → 如果检索结果 quality_score > threshold → 自动写回 Semantic memory
```

### REQ-MEM-025: Memory API（Iter-12 + Iter-13 各一半）

```
Iter-12 API:
  POST   /api/memory/sessions/{id}/ingest     → 手动摄入 session
  POST   /api/memory/consolidate               → 手动触发 consolidation
  GET    /api/memory/search?q=&top_k=&filters= → hybrid search
  GET    /api/memory/facts/{id}                 → 获取单条 fact
  PATCH  /api/memory/facts/{id}                → 人工修正 fact

Iter-13 API:
  GET    /api/memory/graph/entity/{name}       → 查询实体（含关系图）
  GET    /api/memory/graph/traverse            → 图遍历
  POST   /api/memory/crystallize/{session_id}  → 结晶 Brainstorm 产出
  GET    /api/memory/procedures                 → 列出可用 procedure
  POST   /api/memory/lint                       → 手动触发 lint
  GET    /api/memory/stats                      → 记忆统计（facts 数、conf 分布）
```