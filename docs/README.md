# Sloth Agent

> 自驱动、自进化的 AI Agent 框架

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

## 目录结构

```
your-project/
├── .sloth-agent/              # 框架全部文件（加入 .gitignore）
│   ├── src/                    # 框架源码
│   │   ├── sloth_agent/       # Python 模块
│   │   ├── core/             # 核心模块
│   │   ├── memory/           # 记忆系统
│   │   ├── tools/            # 工具集
│   │   ├── providers/        # LLM 提供商
│   │   ├── human/           # 人类审批
│   │   ├── reliability/      # Watchdog/Checkpoint
│   │   └── tdd/             # TDD 强制
│   ├── configs/              # 配置
│   ├── skills/               # 技能库
│   ├── memory/               # 记忆数据
│   ├── checkpoints/          # 断点快照
│   ├── logs/                 # 日志
│   ├── workspace/            # 工作目录
│   └── run.py                # 启动脚本
│
├── docs/                      # 文档（框架生成）
│   ├── specs/                # 设计规格
│   ├── plans/                # 实现计划
│   ├── reports/              # 工作报告
│   └── guides/               # 用户指南
│
└── [你的项目文件...]
```

---

## 快速开始

### 1. 安装框架

```bash
# 下载框架并初始化
git clone <sloth-agent-repo> .sloth-agent

cd .sloth-agent

# 自动安装 uv 并运行（如果没有 uv 会自动安装）
python run.py
```

### 2. 首次配置

```bash
# 复制环境变量模板
cp configs/.env.example configs/.env

# 编辑 configs/.env 填入 API 密钥
vim configs/.env
```

### 3. 创建规格文档

按照命名规范创建规格文档：

```bash
# 文件名格式: YYYYMMDD-project-description-design-spec.md
vim docs/specs/20260415-myproject-design-spec.md
```

---

## 框架特性

- **每日循环**: 夜间生成计划 → 白天自动执行 → 生成报告
- **自进化**: 从执行中学习，沉淀 Skills，修正错误
- **人类把关**: 人类只负责审批 SPEC 和 PLAN，Agent 自主执行
- **多模态**: 支持代码开发、内容创作、数据分析等综合任务
- **高可靠**: TDD 开发、Watchdog 监控（3分钟心跳）、Checkpoint 恢复
- **多模型**: 支持 DeepSeek, Qwen, Kimi, MiniMax, GLM

---

## 配置说明

### .sloth-agent/configs/agent.yaml

```yaml
agent:
  name: "sloth-agent"
  workspace: "./workspace"  # 实际项目代码位置

watchdog:
  heartbeat_interval: 180  # 3分钟心跳

tdd:
  enforced: true
  coverage_threshold: 80   # 测试覆盖率门槛
```

### .sloth-agent/configs/llm_providers.yaml

支持模型：DeepSeek, Qwen, Kimi, MiniMax, GLM

---

## 注意事项

1. **.sloth-agent/ 应该加入 .gitignore**
2. **框架不会修改你的项目文件**，除非你在规格文档中明确要求
3. **高风险操作（L3/L4）需要额外审批**

---

## 文档

### 规范文档 (specs/)

| 文档 | 说明 |
|------|------|
| [Workflow Process Spec](specs/20260415-workflow-process-spec.md) | 7步强制流程、TDD铁律、四阶段调试 |
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
