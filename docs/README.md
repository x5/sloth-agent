# Sloth Agent

> 自驱动、自进化的 AI Agent 框架

---

## 安装（全局工具）

```bash
# 1. 克隆到全局目录
git clone git@github.com:x5/sloth-agent.git ~/.sloth-agent

# 2. 使用 uv 安装
cd ~/.sloth-agent
uv venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e .

# 3. 为项目初始化
sloth init --project ~/my-project
```

---

## 文档命名规范

Sloth Agent 使用统一的文档命名规范：

### 格式

```
YYYYMMDD-event-description-type.md
```

### 类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `design-spec` | 设计规格文档 | `20260415-tools-design-spec.md` |
| `implementation-plan` | 实现计划 | `20260415-tools-implementation-plan.md` |
| `report` | 工作报告 | `20260416-daily-report.md` |
| `user-guide` | 用户手册 | `20260414-user-guide.md` |

### 目录结构

```
docs/
├── specs/           # 设计规格文档
│   └── YYYYMMDD-*-design-spec.md
├── plans/           # 实现计划
│   └── YYYYMMDD-*-implementation-plan.md
├── reports/         # 工作报告
│   └── YYYYMMDD-*-report.md
└── guides/         # 用户指南
    └── YYYYMMDD-*-user-guide.md
```

---

## 全局目录结构

```
~/.sloth-agent/                  # 全局安装目录
├── src/                        # 框架源码
├── configs/                    # 全局配置
├── skills/                     # 全局 Skills 库
├── memory/                     # 全局记忆
├── checkpoints/                # 全局断点
├── logs/                       # 全局日志
└── run.py                      # 入口脚本

[项目目录]/
├── .sloth/                     # 项目配置（加入 .gitignore）
│   └── project.yaml
├── docs/                       # 项目文档
├── TODO.md                     # 项目任务
└── [项目源代码...]
```

---

## 快速开始

### 1. 安装框架（全局）

```bash
git clone git@github.com:x5/sloth-agent.git ~/.sloth-agent
cd ~/.sloth-agent && uv pip install -e .
```

### 2. 初始化项目

```bash
sloth init --project ~/my-project
```

### 3. 创建规格文档

按照命名规范创建规格文档：

```bash
# 文件名格式: YYYYMMDD-project-description-design-spec.md
vim docs/specs/20260415-myproject-design-spec.md
```

### 4. 运行

```bash
# Night Phase: SPEC -> PLAN -> 审批
sloth run --project ~/my-project --phase night

# Day Phase: 执行 PLAN -> 生成报告
sloth run --project ~/my-project --phase day
```

---

## 框架特性

- **每日循环**: 夜间生成计划 → 白天自动执行 → 生成报告
- **自进化**: 从执行中学习，沉淀 Skills，修正错误
- **人类把关**: 人类只负责审批 SPEC 和 PLAN，Agent 自主执行
- **多模态**: 支持代码开发、内容创作、数据分析等综合任务
- **高可靠**: TDD 开发、Watchdog 监控（3分钟心跳）、Checkpoint 恢复
- **多模型**: 支持 DeepSeek, Qwen, Kimi, MiniMax, GLM
- **全局安装**: 一次安装，所有项目通用
- **多项目支持**: 通过 `.sloth/project.yaml` 配置各项目

---

## 配置说明

### ~/.sloth-agent/configs/agent.yaml（全局）

```yaml
agent:
  name: "sloth-agent"
  workspace: "./workspace"

watchdog:
  heartbeat_interval: 180  # 3分钟心跳

tdd:
  enforced: true
  coverage_threshold: 80
```

### ~/.sloth-agent/configs/llm_providers.yaml

支持模型：DeepSeek, Qwen, Kimi, MiniMax, GLM

### [项目]/.sloth/project.yaml（项目级）

```yaml
project:
  name: my-project
  path: /home/user/my-project
  docs_dir: docs

llm:
  default_provider: deepseek
```

---

## 注意事项

1. **.sloth/ 应该加入 .gitignore**
2. **框架不会修改你的项目文件**，除非你在规格文档中明确要求
3. **高风险操作（L3/L4）需要额外审批**

---

## 文档

### 规范文档 (specs/)

| 文档 | 说明 |
|------|------|
| [Workflow Process Spec](specs/20260415-workflow-process-spec.md) | 7步强制流程、TDD铁律、全局安装架构 |
| [Workflow Tools & Hooks Spec](specs/20260415-workflow-tools-hooks-spec.md) | 每步工具/脚本/钩子映射 |
| [Tools Design Spec](specs/20260415-tools-design-spec.md) | 工具系统设计 |
| [Naming Convention Guide](../docs/20260415-naming-convention-user-guide.md) | 文档命名规范 |

### 实现计划 (plans/)

| 文档 | 说明 |
|------|------|
| [Tools Implementation Plan](plans/20260415-tools-implementation-plan.md) | 工具系统实现计划 |
| [Workflow Implementation Plan](plans/20260415-workflow-implementation-plan.md) | 工作流引擎实现计划 |

### 用户指南 (guides/)

- [用户手册](guides/user-guide.md)
- [系统设计文档](specs/sloth-agent-design-spec.md)
