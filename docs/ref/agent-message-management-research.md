# Agent 工具消息管理策略调研

> 调研时间：2026-04-27
> 覆盖工具：Claude Code、OpenClaw、Hermes Agent、Codex CLI、Cursor AI

---

## 总览对比

| 维度 | Claude Code | OpenClaw | Hermes Agent | Codex CLI | Cursor AI | **Sloth (当前)** |
|------|-------------|----------|--------------|-----------|-----------|-------------------|
| 存储格式 | JSONL 文件 | JSONL 文件 | JSONL 文件 | SQLite | SQLite / 内存 | SQLite |
| 上下文策略 | 分层压缩 | 滑动窗口 | 摘要 + 关键消息 | 全量（窗口内） | 窗口 + 智能裁剪 | 最近 1000 条 |
| Token 管理 | 精确计数 + 预算 | Prompt Cache 感知 | 近似计数 | 模型原生窗口 | 自动估算 | 无 |
| 压缩手段 | Summarizer Agent | LLM 摘要 | 分层摘要 | 无（依赖大窗口） | 智能分段 | 无 |
| Head/Tail 保护 | ✅ system + 最近 N 轮 | ✅ system prompt 锚定 | ✅ 关键消息标记 | ❌ | ❌ | 仅 system prompt |
| 多 Agent 支持 | ✅ 子代理独立上下文 | ✅ Agent 间消息路由 | ✅ 子代理消息隔离 | ❌ | ❌ | ❌（仅 Lead Agent） |
| Prompt Cache | ✅（Anthropic API） | ✅ | 部分 | ❌ | ❌ | ❌ |
| 消息归档 | 自动轮转 | 文件分片 | 按 Session 归档 | 自动清理 | 自动清理 | 无 |

---

## 1. Claude Code

### 存储
- **JSONL 文件**：`~/.claude/projects/<project>/<session-id>.jsonl`
- 每次会话一个独立文件
- 包含完整的 tool call / tool result 序列

### 上下文管理（五件套）

1. **Layered Compression**：对话达到阈值时，由 Summarizer Agent 将中间部分压缩为摘要
2. **Head/Tail Protection**：
   - Head：system prompt + 项目指令（CLAUDE.md）永久保留
   - Tail：最近 N 轮对话完整保留（保证当前任务连贯性）
3. **Prompt Cache**：利用 Anthropic API 的 prompt cache，将 system prompt 和 CLAUDE.md 锚定为可缓存前缀，降低重复成本
4. **Token Budget**：精确计算 token 数（通过 Anthropic tokenizer），在预算内动态分配
5. **Context Window Manager**：当预算不足时触发 Summarizer → 压缩 → 继续

### 特点
- 最完善的消息管理体系
- 精确 token 计数是核心能力
- Summarizer Agent 是独立的 LLM 调用，相当于"元认知"层

---

## 2. OpenClaw

### 存储
- **JSONL 文件**：`~/.openclaw/sessions/<session-id>/messages.jsonl`
- 按 Session 目录组织，独立文件

### 上下文管理
- **Sliding Window + Prompt Cache**：
  - 保留 system prompt 作为缓存锚点
  - 滑动窗口内保留完整消息（默认约 50 轮）
  - 超出窗口的消息直接丢弃（不做摘要）
- **Agent 间消息路由**：
  - 子 Agent 有独立的消息队列
  - 父 Agent 可以查看子 Agent 的输出摘要
- **特点**：设计简洁，不追求极致压缩，依赖模型窗口不断扩大

---

## 3. Hermes Agent

### 存储
- **JSONL 文件**：按 Agent 实例存储，支持多文件分片

### 上下文管理
- **分层摘要 + 关键消息保护**：
  - 将对话分为 3 层：
    1. **System 层**（永久保留）
    2. **Summary 层**（自动生成的中间摘要）
    3. **Recent 层**（最近 N 条完整保留）
  - 关键消息（如错误、重要决策）标记为 protected，不被压缩
- **子代理隔离**：
  - 每个子代理有独立的上下文窗口
  - 子代理之间不共享消息（避免污染）
- **特点**：最适合多 Agent 协作的场景，消息隔离设计值得参考

---

## 4. Codex CLI (OpenAI)

### 存储
- **SQLite**：利用 SQLite 的结构化查询能力管理消息

### 上下文管理
- **全量（模型窗口内）**：
  - 依赖 GPT-4/OpenAI o-series 的大上下文窗口
  - 不做主动压缩，靠模型窗口硬扛
- **特点**：最简策略，"窗口够大就不用管"，但也最依赖特定模型能力

---

## 5. Cursor AI

### 存储
- **SQLite + 内存缓存**：
  - 消息持久化到 SQLite
  - 活跃会话缓存在内存中提速

### 上下文管理
- **窗口 + 智能裁剪**：
  - 基于文件相关性裁剪上下文
  - 当前打开的文件及其符号作为"锚点"注入 system prompt
  - 只保留与当前编辑上下文相关的对话片段
- **特点**：IDE 场景特有，用代码上下文（不是纯对话）来驱动消息裁剪

---

## 6. Sloth 现状 & 演进建议

### 当前阶段（v0.5.1）

```
SQLite 单表 → 取最近 1000 条 → 全量送入 LLM
                                  ↑
                             无 token 计数
                             无压缩/摘要
                             无 Prompt Cache
```

**适用条件**：DeepSeek v4 (1M context)、单个 Lead Agent、对话轮次有限

### 推荐演进路径

| 优先级 | 能力 | 原因 |
|--------|------|------|
| P0 | Token 计数 | 成本可控的基础，知道花了多少 token 才知道要不要压缩 |
| P1 | System Prompt Cache 锚定 | 利用 Anthropic/DeepSeek 的 prompt cache 降低重复成本 |
| P2 | 滑动窗口 + Head/Tail 保护 | 接近 OpenClaw 方案，实现简单，效果好 |
| P3 | 摘要压缩 | 接近 Claude Code/Hermes 方案，需要额外的 Summarizer Agent |
| P4 | 多 Agent 消息隔离 | 参考 Hermes 的分层设计，每个 Agent 独立上下文窗口 |

### 摘要压缩的时机判断

- **触发条件**（借鉴 Claude Code）：
  1. Token 预算使用率 > 80%
  2. 对话轮次 > 50 轮
  3. 最近一次压缩距今 > 20 轮
- **压缩内容**：
  - 保留：system prompt + 最近 10 轮 + 标记为 "关键" 的消息
  - 压缩：中间轮次 → 1 条 summary 消息（role: system, 类似 "conversation summary"）

### 多 Agent 场景的消息路由

参考 Hermes 的三级模型：
```
                  ┌─────────────┐
                  │ Orchestrator │  ← 全局上下文（摘要视图）
                  └──────┬──────┘
           ┌─────────────┼─────────────┐
           ▼             ▼             ▼
      ┌────────┐   ┌────────┐   ┌────────┐
      │Agent A │   │Agent B │   │Agent C │  ← 各自独立上下文
      └────────┘   └────────┘   └────────┘
```
- Orchestrator 看到的是各子 Agent 的摘要
- 子 Agent 之间不直接共享消息
- 需要协作时，通过 Orchestrator 转发

---

## 参考链接

- Claude Code: [anthropic.com/claude-code](https://www.anthropin.com/claude-code)
- OpenClaw: [github.com/openclaw/openclaw](https://github.com/openclaw/openclaw)
- Hermes Agent: [github.com/hermes-agent/hermes](https://github.com/hermes-agent/hermes)
- Codex CLI: [github.com/openai/codex](https://github.com/openai/codex)
