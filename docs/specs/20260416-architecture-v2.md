# Sloth Agent 轻量级架构设计 v2

> 版本: v2.0.0-draft
> 日期: 2026-04-16
> 状态: 草案
> 参考: OpenClaw, Hermes Agent, Claude Code, Codex

---

## 1. 核心洞察

### 1.1 最佳实践共性

分析 Claude Code、OpenClaw、Hermes Agent 的共性：

```
┌─────────────────────────────┐
│     Orchestrator Loop       │  ← 核心：一个循环
│                             │
│   observe → think → act     │  ← 观察、思考、行动
│   observe → think → act     │
│   ...                       │
│                             │
│   Tools Layer               │  ← 工具抽象层
│   Skills Layer              │  ← 技能指令层
│   Memory Layer              │  ← 持久记忆层
└─────────────────────────────┘
```

**不是** 8 个专用 Agent，**不是** 8 个固定 Phase，**不是** 3 种存储引擎。

**是一个 Agent + 可组合工具 + 可插拔技能 + 渐进式记忆。**

### 1.2 为什么 Phase-Role 抽象过早

| 参考框架 | Agent 数量 | Phase 概念 | 如何组织流程 |
|----------|-----------|-----------|-------------|
| Claude Code | 1 | 无 | 用户指令 + 工具组合 |
| OpenClaw | 1 | 无 | 技能组合链 |
| Hermes Agent | 1 + 子代理 | 无 | 技能积累 + 经验学习 |
| **我们 v1** | **8** | **8** | 固定场景编排 |

Phase 的本质是**技能的有序调用**。不需要专用 Agent 角色来实现。同一个 Agent 在需求分析阶段用 brainstorming 技能，在编码阶段用 TDD 技能，在审查阶段用 review 技能——靠的是**注入不同的系统提示词和技能上下文**，而不是创建不同的 Agent 实例。

### 1.3 v2 架构原则

1. **一个 Agent**：统一入口，通过 prompt 切换角色行为
2. **工具优先**：LLM 通过工具层执行，不直接写文件/跑命令
3. **技能即指令**：SKILL.md 就是 prompt 模板，运行时注入
4. **渐进式记忆**：从 FS 开始，需要时加 SQLite，再需要时加向量
5. **场景即工作流**：场景定义 = 技能调用序列 + 门控条件

---

## 2. 架构总览

```
┌────────────────────────────────────────────────────────────────┐
│                      CLI Gateway                                │
│                   (typer: run/chat/daemon)                       │
└──────────────────────────┬─────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────┐
│                    Orchestrator (核心循环)                       │
│                                                                  │
│  while active:                                                   │
│    1. observe()   — 读取上下文、状态、记忆                        │
│    2. think()     — LLM 决定下一步行动                            │
│    3. act()       — 通过 ToolOrchestrator 执行                    │
│    4. persist()   — 保存状态、更新记忆                            │
│    5. check()     — 门控验证，决定是否继续                        │
└────────────┬──────────────┬──────────────┬──────────────────────┘
             │              │              │
             ▼              ▼              ▼
┌─────────────┐  ┌──────────────┐  ┌──────────────────┐
│ LLM Router  │  │ Tool         │  │ Skill            │
│             │  │ Orchestrator │  │ Injector         │
│ 多模型路由   │  │              │  │                  │
│ 自动降级     │  │ 意图→风险→   │  │ 匹配技能          │
│ 流式响应     │  │ 执行→结果    │  │ 注入 prompt       │
└─────────────┘  └──────────────┘  └──────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────────────┐
│                    Persistence Layer                            │
│                                                                  │
│  File System (主)   SQLite (索引，可选)   ChromaDB (向量，可选)  │
└────────────────────────────────────────────────────────────────┘
```

---

## 3. 目录结构

```
src/sloth_agent/
├── __main__.py                  # 入口（typer app，已有）
│
├── cli/                         # CLI 层（已有 + 扩展）
│   ├── app.py                   # CLI 子命令
│   ├── chat.py                  # REPL 交互
│   ├── context.py               # 对话上下文
│   └── install.py               # 安装引导（spec 已定义）
│
├── core/                        # 核心层（重构）
│   ├── __init__.py
│   ├── config.py                # 配置模型（已有）
│   ├── orchestrator.py          # ★★★ 核心循环（新增，替代 agent.py）
│   ├── agent.py                 # 统一 Agent（简化，保留）
│   └── state.py                 # 运行状态（已有）
│
├── tools/                       # 工具层（重构 + 扩展）
│   ├── __init__.py
│   ├── registry.py              # 工具注册（从 core/tools/ 迁移）
│   ├── orchestrator.py          # 工具调度链（spec 已定义）
│   ├── intent_resolver.py       # 意图解析
│   ├── risk_gate.py             # 风险门控
│   ├── executor.py              # 执行器（增强）
│   └── builtin/                 # 内置工具
│       ├── file_ops.py          # 读写编辑
│       ├── shell.py             # Bash 执行
│       ├── git_ops.py           # Git 操作
│       └── search.py            # 文件搜索
│
├── skills/                      # 技能层（已有 + 扩展）
│   ├── __init__.py
│   ├── loader.py                # SKILL.md 加载
│   ├── router.py                # 技能路由/匹配
│   ├── injector.py              # 技能 prompt 注入
│   └── evolution.py             # 技能自进化
│
├── memory/                      # 记忆层（已有 + 扩展）
│   ├── __init__.py
│   ├── store.py                 # FS 存储（已有）
│   ├── session.py               # Session 管理（spec 已定义）
│   ├── summarizer.py            # 上下文摘要
│   └── index.py                 # SQLite 索引（可选）
│
├── providers/                   # 外部服务（已有）
│   ├── __init__.py
│   └── llm_providers.py         # LLM 路由（已有）
│
├── workflow/                    # 工作流层（从 phase 简化）
│   ├── __init__.py
│   ├── scenario.py              # 场景定义
│   ├── pipeline.py              # 技能调用管道
│   └── gates.py                 # 门控验证
│
├── daemon/                      # 常驻进程（spec 已定义）
│   ├── __init__.py
│   ├── health.py                # 健康检查
│   └── watchdog.py              # 看门狗（已有，增强）
│
└── security/                    # 安全层（spec 已定义）
    ├── __init__.py
    ├── path_validator.py        # 路径校验
    ├── sandbox.py               # 沙箱
    └── auditor.py               # 审计日志
```

---

## 4. 核心循环（Orchestrator）

```python
class Orchestrator:
    """Sloth Agent 核心循环。

    替代原有的 AgentEvolve.run()。
    支持自主模式和对话模式的统一入口。
    """

    def __init__(self, config: Config):
        self.config = config
        self.agent = Agent(config)
        self.tool_orchestrator = ToolOrchestrator(config)
        self.skill_injector = SkillInjector(config)
        self.memory = MemoryStore(config)
        self.state = AgentState()

    def run(self, mode: str = "autonomous") -> None:
        """主循环。"""
        if mode == "autonomous":
            self._autonomous_loop()
        else:
            self._chat_loop()

    def _autonomous_loop(self) -> None:
        """自主模式循环。"""
        while not self.state.should_stop:
            # 1. 观察：读取当前状态、记忆、上下文
            context = self.observe()

            # 2. 思考：LLM 决定下一步
            action = self.agent.think(context)

            # 3. 执行：通过工具层执行
            result = self.act(action)

            # 4. 持久化：保存状态
            self.persist(result)

            # 5. 门控：检查是否满足继续条件
            if not self.check_gates(result):
                self.handle_gate_failure(result)

    def _chat_loop(self) -> None:
        """对话模式循环。"""
        # 复用现有 ChatSession.loop()
        pass

    def observe(self) -> Context:
        """收集上下文：状态、记忆、前序结果。"""
        return Context(
            state=self.state,
            memory=self.memory.get_recent(),
            workspace=self._scan_workspace(),
        )

    def act(self, action: Action) -> Result:
        """执行行动。"""
        if action.type == "tool_call":
            return self.tool_orchestrator.invoke(action.intent)
        elif action.type == "skill_activate":
            return self.skill_injector.activate(action.skill_id)
        elif action.type == "phase_transition":
            return self._transition_phase(action.phase_id)

    def check_gates(self, result: Result) -> bool:
        """验证门控。"""
        for gate in self.state.active_gates:
            if not gate.check(result):
                return False
        return True
```

**关键设计：Orchestrator 是唯一的控制流入口。**

自主模式和对话模式的区别仅在于：
- 自主模式：`think()` 返回的是自动化决策
- 对话模式：`think()` 返回的是 LLM 对用户的回复

---

## 5. 与 v1 的映射关系

| v1 概念 | v2 对应 | 变化 |
|---------|---------|------|
| 8 个 Agent 角色 | 1 个 Agent + 系统提示切换 | 简化 |
| 8 个 Phase | 技能调用序列（workflow/pipeline） | 简化 |
| PhaseRegistry | Scenario + Pipeline | 合并 |
| SkillRegistry | SkillLoader + Router | 拆分 |
| ToolRegistry | ToolOrchestrator（4 层链） | 增强 |
| MemoryStore（3 层） | MemoryStore（FS 主，其他可选） | 简化 |
| AgentEvolve.run() | Orchestrator.run() | 替换 |
| ChatSession | Orchestrator._chat_loop() | 保留 |
| Watchdog | Daemon + Watchdog | 增强 |

---

## 6. 需要保留的 v1 设计

以下 v1 设计是正确的，应保留：

| 设计 | 原因 |
|------|------|
| SKILL.md 格式 | 与 Claude Code 生态兼容 |
| 文件系统为主存储 | 可回溯、可审计、可手动编辑 |
| jsonl 对话格式 | 流式写入、不丢失 |
| 多 LLM Provider + fallback | 中国模型生态必要 |
| TDD 门控 | 质量保证底线 |
| 日夜时间窗口 | 黑灯工厂核心需求 |
| 技能进化触发条件 | 自进化能力基础 |

---

## 7. 需要合并/调整的 v1 设计

| 设计 | 问题 | 调整方案 |
|------|------|---------|
| 8 个专用 Agent | 过度设计，参考框架都用 1 个 Agent | 合并为 1 个 Agent，通过 prompt 切换行为 |
| Phase 作为独立实体 | Phase 本质是技能序列，不是独立概念 | Phase → Pipeline（技能调用序列 + 门控） |
| ScenarioValidator 的 input/output schema 匹配 | 过于严格，LLM 输出不固定 | 改为 output 契约检查（是否存在必需产出） |
| Memory 3 层同时实现 | 起步太重 | 先 FS，需要时加 SQLite，再需要时加向量 |
| 每个 Phase 独立 LLM 切换 | 切换开销大，上下文丢失 | Agent 内通过 tool 参数指定模型，不切换实例 |
| Gate 定义为 Python lambda | 不可配置 | Gate 改为 YAML 可配置 |

---

## 8. 需要新增的组件

| 组件 | 优先级 | 说明 |
|------|--------|------|
| Orchestrator 核心循环 | P0 | 统一入口，替代 AgentEvolve |
| ToolOrchestrator 4 层链 | P0 | IntentResolver → RiskGate → Executor → Formatter |
| SkillInjector | P0 | 技能 prompt 注入机制 |
| Pipeline（替代 Phase） | P1 | 技能调用序列 + 门控 |
| Daemon 守护进程 | P1 | 常驻运行 + 健康检查 |
| Security 沙箱 | P1 | 路径校验 + 命令黑名单 |
| Memory Session 管理 | P2 | Session 生命周期（spec 已有） |
| 技能自进化 | P2 | 错误驱动的技能改进 |

---

## 9. 实施路径

### Phase 1: 核心替换（2-3 天）

1. 创建 `Orchestrator` 类，整合现有 LLM + Tool + Memory
2. 创建 `ToolOrchestrator`，实现 4 层调用链
3. 创建 `SkillInjector`，实现 SKILL.md 加载和注入
4. 保留 `ChatSession` 作为对话入口
5. 将 `AgentEvolve.run()` 标记为 deprecated

### Phase 2: 工作流重构（2-3 天）

1. 将 Phase 定义迁移为 Pipeline 定义
2. 实现 Pipeline 执行器（技能序列 + 门控）
3. 保留 8 个场景定义，但用 Pipeline 代替 Phase
4. Gate 改为 YAML 可配置

### Phase 3: 常驻 + 安全（2-3 天）

1. 实现 Daemon 守护进程
2. 实现健康检查
3. 实现 Security 沙箱
4. 实现安装引导

### Phase 4: 记忆 + 进化（1-2 天）

1. 完善 Memory Session 管理
2. 实现技能自进化
3. 可选：SQLite 索引层

---

## 10. 风险与权衡

| 风险 | 缓解 |
|------|------|
| 从 Phase 迁移到 Pipeline 需要重写场景定义 | 场景定义是 YAML 数据，迁移成本低 |
| Orchestrator 统一入口后，自主/对话模式耦合 | 通过 mode 参数分离，代码结构清晰 |
| ToolOrchestrator 4 层链增加延迟 | 意图解析可缓存，风险门控可跳过（低风险工具） |
| 1 个 Agent vs 8 个 Agent 的能力差异 | 通过 prompt 注入 + 技能激活实现同等行为，参考 Claude Code |

---

## 11. 与参考框架的对齐

| 特性 | OpenClaw | Hermes Agent | Claude Code | **我们 v2** |
|------|----------|-------------|-------------|-------------|
| 单 Agent 核心循环 | ✅ | ✅ | ✅ | ✅ |
| 技能/工具抽象层 | ✅ Skills | ✅ Skills | ✅ Tools | ✅ Tools + Skills |
| 持久记忆 | ✅ | ✅ 自积累 | Session | ✅ FS + Session |
| 多模型支持 | ✅ | ✅ | ❌ | ✅ |
| 安全沙箱 | ✅ Risk | ✅ | Risk levels | ✅ 5 层安全 |
| 自进化能力 | ❌ | ✅ | 部分 | ✅ 技能进化 |
| 守护进程 | ✅ Gateway | ✅ Persistent | ❌ | ✅ Daemon |
| 可观测性 | ✅ | ✅ | ❌ | ✅ 指标收集 |
| 工作流编排 | ✅ Multi-agent | ❌ | ❌ | ✅ Pipeline |

**我们的差异化优势**：多模型支持 + 技能自进化 + 工作流编排 + 中国模型生态。

---

*文档版本: v2.0.0-draft*
*创建日期: 2026-04-16*
