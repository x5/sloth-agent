# 架构设计 Review 报告

> 评审对象: `docs/specs/00000000-architecture-overview.md` (v2.0.0)
> 评审日期: 2026-04-16
> 状态: 完成

---

## 评分总览

| 维度 | 评分 | 说明 |
|------|------|------|
| **完整性** | 9/10 | 覆盖面极广，几乎涵盖了 Agent 系统的所有方面 |
| **可执行性** | 4/10 | 规模过大，v1.0 scope 不现实，有"设计到死"的风险 |
| **创新性** | 5/10 | 在中国生态适配上有差异化，但在 Agent 核心能力（反思、自适应、学习）上落后于前沿 |
| **架构合理性** | 6/10 | 模块划分清晰，但 Agent 粒度过细、存储层过重、关键组件缺失 |

**一句话总结**：这是一份优秀的**愿景文档**，但不是一份好的**v1.0 架构**。砍掉 70% 范围，加入 adaptive execution + reflection + eval，先做出能跑的 Agent 再迭代。

---

## 一、架构设计问题

### 1.1 复杂度与交付风险严重不匹配

19 个 spec、15+ 模块、8+1 Agent、37 技能、8 场景 —— 这是一个 v3.0 级别的愿景文档，但标注为 v1.0 规划。以单人或小团队的产出能力，这个规模的系统**大概率会陷入永远在写基础设施、永远无法交付可用产品的困境**。

> **建议**：v1.0 核心交付应砍到 3-4 个模块（Tools + Memory + Chat + 1 Agent），其余全部标注为 future。

### 1.2 Agent 粒度过细，角色边界不清

8 个专用 Agent 按 Phase 绑定的设计有几个问题：

| 问题 | 说明 |
|------|------|
| **角色重叠** | Debugger vs Engineer、Reviewer vs QA 在实际开发中界限模糊，拆分后增加了不必要的上下文切换开销 |
| **过度隔离** | 每个 Agent 独立 context window = 关键信息在 Phase 间传递时必然丢失（summarization 是有损压缩） |
| **实例数设计缺乏依据** | Engineer 最大 3 实例、Debugger 2 实例——依据是什么？无负载模型支撑 |

> **建议**：合并为 3-4 个 Agent（Planning Agent、Execution Agent、Review Agent、General Agent），按能力域而非工序划分。

### 1.3 Phase 上下文传递是架构中最脆弱的环节

文档写道用 `ContextSummarizer` 做 Phase 间摘要传递，但：
- **摘要质量直接决定下游 Phase 的执行质量**——这是一个递归的 LLM 质量问题
- 没有提到摘要的验证机制（如何知道摘要是否遗漏了关键信息？）
- 没有提到 fallback（摘要不够时是否能回溯读取完整 chat.jsonl？）

> **建议**：加入 structured output schema 做 Phase 输出（而非自由文本摘要），下游 Phase 读取 schema 而非散文。

### 1.4 Worktree 多 Agent 并行方案过度理想化

```
Coordinator → 分发任务 → 独立 worktree + 分支 → 各自执行 → 合并
```

- Git 合并冲突的自动解决是业界公认的难题，文档中 `ConflictDetector` + `ResultMerger` 一笔带过
- 大多数真实开发任务是**顺序依赖**的（后端 API 没写完，前端无法联调）
- Worktree 创建/清理的开销在频繁小任务场景下不容忽视

> **建议**：v1.0 禁用多 Agent 并行（文档中 `multi_agent.enabled: false` 是对的），但架构上应为串行优化而非并行优化。

### 1.5 三层存储（FS + SQLite + ChromaDB）增加了不必要的复杂度

"可选" 的 SQLite 和 ChromaDB 意味着：
- 代码中存在大量 `if index_enabled` / `if vector_enabled` 分支
- 测试矩阵是 2×2 = 4 种配置组合
- 数据一致性保证变得困难（FS 写了但 SQLite 索引没更新？）

> **建议**：v1.0 仅用文件系统。如需索引，用内存中的 dict/set 做会话级缓存即可。

### 1.6 缺少关键架构组件

| 缺失项 | 影响 | 状态 |
|--------|------|------|
| **Context Window 管理策略** | 这是 Agent 系统的 #1 工程挑战，文档只提到 `max_context_turns: 20` 但没有截断、压缩、滑动窗口策略 | ✅ **v1.0**，已加入 §5.1.2（Token 分区 + ContextWindowManager + 确定性压缩规则） |
| **LLM Hallucination 防护** | Agent 的工具调用可能基于幻觉参数（伪造文件路径、错误命令），没有提到校验层 | ✅ **v1.0**，已加入 §7.1.3（HallucinationGuard：路径/命令/模式校验，工具调用链新增检测层） |
| **Streaming 架构** | 现代 Agent 交互必须 streaming 输出，但文档仅有 `stream_responses: true` 配置项，无架构设计 | ✅ **v1.0**，已加入 §7.5（StreamProcessor：文本/工具调用交织处理 + CLI 渲染 + Provider SSE 适配） |
| **评估框架** | 零 mention 如何评估 Agent 质量——没有 eval 就没有改进基线 | ✅ **v1.0**，已加入 §11.5（5 维度评分 + 标准任务集） |
| **回滚策略** | 除 git 外没有系统性回滚机制，checkpoint 的描述过于粗略 | ✅ **v1.0**，已加入 §8.3（3 级 Git Checkpoint：任务级/阶段级/Session 级 + 自动回滚触发规则） |
| **Token 预算管理** | 和 cost budget 不同，这是单次请求的 token 分配策略（system prompt 占多少、history 占多少、tools 占多少） | 📌 **v2.0**，已加入 §7.3.1（Token Budget Manager） |

---

## 二、创新性评估

### 2.1 做得好的

| 创新点 | 评价 |
|--------|------|
| **Cost-aware LLM 路由** | 实用且差异化，按预算选模型是真实痛点 |
| **SKILL.md 兼容 Claude Code** | 借力生态而非重造，聪明的决策 |
| **昼夜双模式** | "黑灯工厂" 概念有场景价值，但需要大量工程打磨 |
| **6 中国 LLM Provider** | 对目标用户群有实际价值 |

### 2.2 不够创新的

| 缺失方向 | 行业前沿做法 | 状态 |
|----------|------------|------|
| **无 Adaptive Planning** | 现代 Agent（如 SWE-Agent、Devin）支持动态重规划——执行中发现计划不对可以中途修正，而非死板走完 8 个 Phase | ✅ **v1.0**，已加入架构文档 §6.0 Adaptive Planning |
| **无 Reflection/Self-Critique** | 前沿 Agent 系统（Reflexion、LATS）都有自我评估和反思机制，你的 Agent 只管做不管评 | ✅ **已完整设计**：架构文档 §6.0 Reflection 机制——结构化 Reflection Schema + Stuck Detection + 与技能自进化衔接。参考 Reflexion（verbal reflection）+ SWE-Agent（完整环境观察）+ Aider（确定性工具反馈）|
| **无 Speculative Execution** | 对于不确定性高的任务，可并行尝试 2-3 种方案取最优（如 best-of-N sampling） | 📌 **v2.0**，已加入架构文档 §6.0 Speculative Execution |
| **无 Code Understanding 深度集成** | 仅有 grep/glob，缺少 AST 级别的代码理解（tree-sitter）、类型系统集成（LSP）、依赖图分析 | ✅ **v1.0**，已加入架构文档 §7.1.1 Code Understanding |
| **无 Human-in-the-Loop 学习** | 审批只是门控，不是学习——Agent 应该从人类的修改和拒绝中学到偏好 | ✅ **不冲突，与技能自进化互补**：技能自进化是 Agent 自驱（error/experience 触发），HiTL 学习是人驱（人类修改/拒绝触发），两者触发源不同但可共用技能存储机制 |
| **无 Tool-Use 学习** | Agent 应该记录哪些工具调用成功/失败，逐步优化工具选择策略 | ✅ **v1.0**，已加入架构文档 §7.1.2 Tool-Use 学习 |
| **事件系统过重** | 真正创新的做法是 **lightweight hook system**（pre/post hooks），而非完整 pub-sub + dead letter queue | ✅ **已处理**：架构文档 §7.4 已拆分为 v1.x 轻量 HookManager + v2.0 完整事件总线 |

---

## 三、优化建议（按优先级）

### P0：砍掉 70% 的 v1.0 范围 → ✅ 已落地（架构文档 §5.1 / §6.0 / §9.0 / §14）

```
v1.0 应只交付:
├── 1 个 General Agent（不拆 8 个）
├── Chat Mode（REPL + streaming）
├── Tools（read/write/edit/run_command/glob/grep）
├── Memory（纯文件系统，jsonl）
├── Skill Loading（加载 SKILL.md，斜杠触发）
└── 1 个 LLM Provider（DeepSeek 或 Qwen）

v1.1 再加:
├── 多 Provider + fallback
├── Cost tracking
├── Phase 基础流程（2-3 个 Phase）
└── Context summarization
```

### P1：加入 Adaptive Execution Loop → ✅ 已落地（架构文档 §6.0 Adaptive Execution）

替代死板的 Phase 线性流程：

```python
while task_not_done:
    plan = agent.plan(task, context)
    result = agent.execute(plan.next_step)
    reflection = agent.reflect(result)
    if reflection.needs_replan:
        context.update(reflection.learnings)
        continue  # 回到 plan
    if reflection.is_done:
        break
```

这比 `Phase 1 → 2 → 3 → ... → 8` 更灵活、更符合真实开发。

### P2：加入 Structured Output 做 Phase 间通信 → ✅ 已落地（架构文档 §5.1.1 BuilderOutput/ReviewerOutput）

```python
class PhaseOutput(BaseModel):
    """Phase 输出的强类型 schema，替代自由文本摘要"""
    decisions: list[Decision]
    artifacts: list[ArtifactRef]
    open_questions: list[str]
    next_phase_context: dict
```

### P3：加入 Token Budget Manager → 📌 已记入架构文档 §7.3.1（v2.0 需求）

```
单次 LLM 请求的 token 分配:
├── System Prompt:     15% (含角色定义 + 技能指令)
├── Context/History:   50% (对话历史 + 摘要)
├── Tool Definitions:  15% (工具 schema)
├── User Message:      10% (当前输入)
└── Reserved for Output: 10%

超出时的截断策略:
├── 优先截断最旧的对话轮次
├── 其次压缩 tool results（只保留摘要）
└── 最后降级 system prompt（移除非必要技能）
```

### P4：简化事件系统 → 📌 已记入架构文档 §7.4（v1.x hooks / v2.0 event bus）

```python
# 用 hooks 替代完整 event bus
class HookManager:
    hooks: dict[str, list[Callable]]

    def on(self, event: str, handler: Callable): ...
    def emit(self, event: str, data: Any): ...

# 同步、无持久化、无死信队列
# v1.x 足够用，v2.0 再考虑完整 event bus
```

### P5：加入 Eval 框架 → ✅ 已落地（架构文档 §11.5 评估框架）

没有评估就没有改进：
- 定义 10-20 个标准任务（创建文件、修复 bug、写测试、重构等）
- 每次架构变更后跑一遍 eval
- 记录成功率、token 消耗、执行时间

---

## 四、需回答的关键问题

在继续实现前，建议先回答以下问题：

1. ~~**v1.0 的最小可用场景是什么？**~~ ✅ **已解答**：Plan → 全自主开发到部署（全程自主，关键节点自动门控）
2. ~~**为什么需要 8 个 Agent 而不是 1 个？**~~ ✅ **已解答**：v1.0 不需要 8 个，用 3 个（Builder/Reviewer/Deployer），按上下文耦合度分组，数据驱动拆分
3. ~~**Phase 摘要丢信息怎么办？**~~ ✅ **已解答**：用结构化交接协议（BuilderOutput/ReviewerOutput）替代 LLM 摘要，传递 git diff / pytest / coverage 等确定性数据
4. ~~**如何评估 Agent 质量？**~~ ✅ **已补充**：v1.0 内置 Eval 框架，10-20 个标准任务 + 5 维度评分（成功率/质量/效率/审查独立性/自修复率），见架构文档 §11.5
5. **Token budget 怎么分配？** → 📌 **推迟到 v2.0**，v1.0 通过 Builder 滑动窗口 + 工具结果压缩解决，不做精确 token 预算分配。v2.0 Token Budget Manager 已记入架构文档 §7.3.1
6. ~~**如果只能留 3 个模块，留哪 3 个？**~~ ✅ **已解答**：Tools + Memory + Agents（3-Agent 流水线），v1.0 scope 已重新定义

---

*评审人: AI Architecture Reviewer*
*日期: 2026-04-16*
