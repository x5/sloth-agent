# Sloth Agent - 用户使用手册

> 从零开始使用 Sloth Agent 框架的完整指南

---

## 目录

1. [快速开始](#1-快速开始)
2. [场景一：从零创建新项目](#2-场景一从零创建新项目)
3. [场景二：集成到已有项目](#3-场景二集成到已有项目)
4. [日常使用流程](#4-日常使用流程)
5. [配置说明](#5-配置说明)
6. [审批与监控](#6-审批与监控)

---

## 1. 快速开始

### 1.1 安装框架

```bash
# 方式一：从零开始
git clone <sloth-agent-repo> your-project
cd your-project
python run.py  # 自动检测并安装 uv

# 方式二：集成到已有项目
cd /path/to/your-existing-project
git clone <sloth-agent-repo> .
python run.py
```

### 1.2 配置 API 密钥

```bash
# 复制环境变量模板
cp configs/.env.example configs/.env

# 编辑填入密钥
vim configs/.env
```

```bash
# 至少配置一个模型
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxx

# 可选：配置其他模型
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxx    # Qwen
MOONSHOT_API_KEY=sk-xxxxxxxxxxxxxx     # Kimi
MINIMAX_API_KEY=xxxxxxxxxxxxxx
ZHIPU_API_KEY=xxxxxxxxxxxxxx

# 配置飞书审批（可选）
FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/your-webhook
```

### 1.3 验证安装

```bash
python run.py --help
```

---

## 2. 场景一：从零创建新项目

### 2.1 项目目录结构

```
my-project/
├── src/                   # 框架源代码
│   ├── src/                    # 框架源码
│   ├── configs/               # 配置
│   ├── skills/                # 技能库
│   ├── memory/                # 记忆数据
│   ├── checkpoints/           # 断点
│   ├── logs/                  # 日志
│   └── workspace/             # 工作区
│
├── docs/                       # 文档（框架生成）
│   ├── specs/                 # 规格文档
│   ├── plans/                 # 每日计划
│   └── reports/               # 工作报告
│
└── [你的项目文件...]            # 实际项目代码放在项目根目录
```

### 2.2 创建规格文档

在 `docs/specs/` 下创建规格文档：

```bash
mkdir -p docs/specs
vim docs/specs/project-spec.md
```

示例内容：

```markdown
# My Project Specification

## 项目概述
- 项目名称：我的网站
- 项目类型：Web 应用

## 功能需求
1. 用户认证（登录/注册）
2. 简单的 CRUD 任务管理
3. 数据仪表盘展示

## 技术栈
- 前端：React + TypeScript
- 后端：Python FastAPI
- 数据库：SQLite

## 成功标准
- 测试覆盖率达到 80%
```

### 2.3 启动框架

```bash
python run.py
```

框架会自动：
1. 检测并安装 uv（如需要）
2. 创建虚拟环境
3. 安装依赖
4. 启动 Agent

### 2.4 第一天工作流程

```
Night Phase (22:00)
├── 框架读取 docs/specs/project-spec.md
├── 检索 memory/ 中的经验
├── 生成 docs/plans/plan-2026-04-15.json
│   ├── Task 1: 初始化项目结构
│   ├── Task 2: 实现用户认证
│   └── Task 3: 编写单元测试
└── 飞书/邮件 发送审批给你

你审批通过后，框架进入等待

Day Phase (09:00)
├── 框架开始执行计划
├── 每完成一个任务保存 Checkpoint
├── 如果出错，自动重试或回滚
└── 完成后生成报告

生成报告 docs/reports/report-2026-04-15.json
```

---

## 3. 场景二：集成到已有项目

### 3.1 集成步骤

```bash
cd /path/to/existing-project

# 添加框架
git clone <sloth-agent-repo> .

# 配置
cp configs/.env.example configs/.env
vim configs/.env

# 创建规格目录
mkdir -p docs/specs docs/plans docs/reports

# 创建规格文档
vim docs/specs/existing-project-spec.md

# 启动
python run.py
```

### 3.2 重要配置

编辑 `configs/agent.yaml`：

```yaml
agent:
  name: "my-project-agent"
  workspace: ".."  # 指向实际项目根目录
```

### 3.3 .gitignore 配置

确保 `.gitignore` 包含：

```gitignore
# Sloth Agent（不要提交框架数据）
memory/
checkpoints/
logs/
.env
workspace/
.env
```

---

## 4. 日常使用流程

### 4.1 每日早晨（可选）

```bash
# 查看今晚生成的计划
cat docs/plans/plan-$(date +%Y-%m-%d).json

# 或通过飞书/邮件查看
```

### 4.2 审批计划

收到飞书/邮件通知后：

| 操作 | 说明 |
|------|------|
| **批准** | 点击批准，框架开始执行 |
| **修改** | 回复消息提出修改意见 |
| **拒绝** | 当天不执行 |

### 4.3 白天监控（可选）

```bash
# 查看当前进度
cat checkpoints/latest.json

# 查看执行日志
tail -f logs/agent.log
```

### 4.4 傍晚查看报告

```bash
cat docs/reports/report-$(date +%Y-%m-%d).json
```

报告示例：

```json
{
  "report_id": "report-2026-04-15",
  "date": "2026-04-15",
  "tasks_summary": {
    "task-1": {"state": "succeed", "description": "初始化项目"},
    "task-2": {"state": "succeed", "description": "实现认证"},
    "task-3": {"state": "failed", "error": "测试覆盖率不足"}
  },
  "errors_encountered": [
    {"error_type": "BuildError", "recovered": true}
  ],
  "skills_created": ["error-recovery-build-failures"],
  "skills_revised": ["debug-patterns"]
}
```

### 4.5 查看和编辑技能

```bash
# 查看所有技能
ls skills/*/

# 查看特定技能
cat skills/error-recovery/debug-network-errors.md

# 手动编辑
vim skills/error-recovery/debug-network-errors.md
```

---

## 5. 配置说明

### 5.1 配置文件位置

| 文件 | 说明 |
|------|------|
| `configs/agent.yaml` | 主配置 |
| `configs/llm_providers.yaml` | 模型配置 |
| `configs/.env` | API 密钥（不提交） |

### 5.2 关键配置项

```yaml
# 执行时间窗口
execution:
  auto_execute_hours: "09:00-18:00"  # 全自动执行
  require_approval_hours: "18:00-09:00"  # 这段时间需审批

# Watchdog（不建议修改）
watchdog:
  heartbeat_interval: 180  # 3分钟
  max_missing_heartbeats: 3  # 9分钟无响应才重启

# TDD
tdd:
  enforced: true
  coverage_threshold: 80  # 测试覆盖率门槛
```

---

## 6. 常见问题

### Q: 框架卡住了怎么办？

```bash
# 框架会自动重启（Watchdog 机制）
# 手动重启
pkill -f "agent_evolve"
python run.py
```

### Q: 如何跳过某些任务？

编辑 `docs/plans/plan-YYYY-MM-DD.json`：

```json
{
  "task_id": "task-3",
  "state": "skipped",
  "reason": "manual_skip"
}
```

### Q: 如何回滚已完成的任务？

```bash
git log --oneline
git revert <commit-hash>
```

---

## 下一步

- 查看 [系统设计文档](spec/sloth-agent-design.md)
- 查看 [示例 SPEC](specs/example-spec.md)

---

*文档版本: v0.1.0*
*最后更新: 2026-04-14*
