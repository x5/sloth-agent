# 变更提案: Memory 架构 — 从会话存储到知识积累

> 日期: 2026-05-07
> 参考: Google ADK (BaseMemoryService)、Karpathy LLM Wiki、agentmemory (iii-engine)
> 影响模块: memory/, session/, events/, brainstorm/
> 关联 Iter: 12 (Foundation) + 13 (Advanced)

## 动机

Sloth 当前有 message 存储（`Message` 表）和 session 记录（`BrainstormSession`），但没有真正的"记忆"：

- Agent 每次对话从零开始，看不到历史讨论
- 没有跨 session 的知识积累
- Brainstorm 讨论的结论只存于当前 session，无法被后续对话利用
- agent 不会因为"见过更多"而变得更聪明

目标是让 memory 成为 Agent 自演进的引擎——每完成一次对话/讨论/调试，知识就积累一层，Agent 下次更聪明。

## 参考设计

### Karpathy LLM Wiki + agentmemory (gist 参考)

核心思想——四层 consolidation pipeline：

```
Working Memory (当前 session 流)
  → Episodic Memory (session 摘要，压缩)
    → Semantic Memory (跨 session 事实，consolidated)
      → Procedural Memory (workflow/pattern，extracted from repetition)
```

每往上一层，信息更稠密、置信度更高、存活时间更长。配合 confidence scoring（Ebbinghaus 遗忘曲线）、supersession（新信息推翻旧信息的完整 trace）、hybrid search（BM25 + vector + graph 三路融合）。

### Google ADK BaseMemoryService

- `add_session_to_memory(session)` — 整 session 摄入
- `search_memory(app_name, user_id, query)` — 跨 session 语义搜索
- Memory Bank + RAG 作为后端

### 为什么两件事要一起做

ADK 提供了"怎么存和搜"，gist 提供了"记忆应该有什么结构"。二者结合：ADK 的 `add_session_to_memory` 是 ingest 的触发点，gist 的 consolidation pipeline 是处理逻辑。

## 架构总览

```
on_session_end (hook from Iter-9)
        │
        ▼
┌──────────────────────────────────────────────────────┐
│                 Memory Pipeline                       │
│                                                       │
│  ┌─────────┐   ┌──────────┐   ┌─────────┐   ┌──────┐ │
│  │ Ingest  │──▶│ Extract  │──▶│  Merge  │──▶│Index │ │
│  │ 原始对话 │   │ 实体+关系 │   │ 冲突检测 │   │ 多路  │ │
│  │ →观测   │   │ +置信度  │   │ supersede│   │ 写入  │ │
│  └─────────┘   └──────────┘   └─────────┘   └──────┘ │
│                                                       │
│  ┌──────────────────────────────────────────────────┐ │
│  │              Retrieve (Hybrid)                   │ │
│  │   BM25 ──┬── RRF Fusion ──▶ Context Injection   │ │
│  │   Vector─┤                   到 Agent prompt     │ │
│  │   Graph ─┘                                      │ │
│  └──────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

## 分 Iter 策略

| Iter | 天 | 内容 | 交付 |
|------|---|------|------|
| **12** | 5 | Memory Foundation | Ingest pipeline + Consolidation tiers (W→E→S) + Confidence scoring + Hybrid search (BM25+vector) + Context injection |
| **13** | 5 | Memory Advanced | Knowledge graph (entity+relations) + Supersession + Crystallization + Procedural memory + Self-healing/lint + Event-driven hooks |

## 决策

| 问题 | 决策 |
|------|------|
| 存储后端 | chromadb（已有依赖）做向量 + SQLite FTS5 做 BM25 |
| Embedding model | 先用本地轻量模型（all-MiniLM-L6-v2），预留 API 切换 |
| 与现有 DB 的关系 | Memory 独立数据库（`memory/chroma/` + `memory/fts.db`），不混入业务 DB |
| 是否替代现有 Message 表 | 否。Message 表仍是 session 内消息的权威存储，memory 是额外的索引层 |
| Confidence 算法 | Ebbinghaus 遗忘曲线：`score = base * e^(-λt) + reinforcement_bonus` |
| 是否做 graph DB | Iter-12 不做原生 graph DB。用 SQLite 存实体-关系三元组，Iter-13 用 networkx 做图遍历 |
| 触发方式 | Iter-12 手动触发（API call），Iter-13 接 hooks 自动化 |

## 范围外

- 不替代现有 `backend Message` 表
- 不做多用户协作（single-user by design）
- 不做 PII 过滤（MVP 阶段手动管理隐私）
- 不做 bulk 操作 UI（Iter-13 有 API，UI 后续迭代）