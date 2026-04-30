# Sloth Agent — CLAUDE.md

## 项目概况

Sloth Agent 是一站式自主开发 AI Agent 框架。输入一份 Plan，输出已开发、测试通过、部署上线的完整项目。

- **核心运行时**: Python 3.10+ (`src/sloth_agent/`)
- **后端 Sidecar**: Python 3.12+ FastAPI (`backend/`)
- **前端**: React 18 + TypeScript + Vite (`frontend/`)
- **桌面壳**: Tauri v2 Rust (`src-tauri/`)
- **包管理**: `uv` (Python), `pnpm` 或 `npm` (前端)

## 文档结构

```
docs/
├── specs/           # 源头真相 — 每个模块一个目录，见下方模块列表
├── changes/         # 进行中的 Delta 变更
├── archive/         # 历史归档（旧 spec + 已合并的 change）
├── plans/           # 大功能的项目级计划（跨多迭代才需要）
├── design/          # 设计文档（UI 布局、架构图）
├── qa/              # 验证清单
├── ref/             # 参考资料（gstack、superpowers）
├── guides/          # 用户指南
├── reports/         # 架构审查报告
├── releases/        # 发布说明
├── articles/        # 文章
└── discussions/     # 讨论记录
```

### 模块 Spec 索引

| 模块 | 路径 | 状态 |
|------|------|------|
| 架构总览 | `docs/specs/architecture/spec.md` | 已实现 |
| 运行时内核 | `docs/specs/runtime/spec.md` | 已实现 |
| Tool 子系统 | `docs/specs/tools/spec.md` | 已实现 |
| 技能管理 | `docs/specs/skills/spec.md` | 已实现 |
| 对话模式 | `docs/specs/chat/spec.md` | 已实现 |
| LLM 路由 | `docs/specs/llm/spec.md` | 已实现 |
| 成本追踪 | `docs/specs/cost/spec.md` | 已实现 |
| 错误处理 | `docs/specs/errors/spec.md` | 已实现 |
| 记忆管理 | `docs/specs/memory/spec.md` | 部分实现 |
| Brainstorm | `docs/specs/brainstorm/spec.md` | 实现中 |
| 桌面应用 | `docs/specs/desktop/spec.md` | 实现中 |
| 会话管理 | `docs/specs/session/spec.md` | 部分实现 |
| 沙箱安全 | `docs/specs/sandbox/spec.md` | 部分实现 |
| 安装初始化 | `docs/specs/onboarding/spec.md` | 部分实现 |
| 评估框架 | `docs/specs/eval/spec.md` | 部分实现 |
| 守护进程 | `docs/specs/daemon/spec.md` | 部分实现 |
| 多 Agent 协调 | `docs/specs/coordination/spec.md` | 未实现 |
| 可观测性 | `docs/specs/observability/spec.md` | 未实现 |
| 报告生成 | `docs/specs/reports/spec.md` | 未实现 |
| 通知集成 | `docs/specs/notifications/spec.md` | 未实现 |
| 事件系统 | `docs/specs/events/spec.md` | 未实现 |
| 知识库 | `docs/specs/knowledge/spec.md` | 未实现 |
| 飞书集成 | `docs/specs/feishu/spec.md` | 未实现 |

## 开发工作流（Delta Spec）

### 核心原则

- **Spec 是源头真相**。`docs/specs/<module>/spec.md` 描述系统的当前真实状态，不是愿景。
- **改代码前先改 Spec**。任何需求变更必须先写成 Delta。
- **一次变更 = 一个 change 目录**。完成后立即归档。

### 标准流程

```
新需求 / 新功能
    │
    ▼
① 确定影响哪些模块，阅读对应 docs/specs/<module>/spec.md
    │
    ▼
② 在 docs/changes/<change-name>/ 下创建 Delta 目录
    ├── proposal.md     # 为什么做、变更范围
    ├── delta.md        # ADDED / MODIFIED / REMOVED 条款
    └── tasks.md        # 实现任务清单（勾选制）
    │
    ▼
③ 按 tasks.md 逐项实现
    │
    ▼
④ 完成后，将 delta.md 合并到 docs/specs/<module>/spec.md
    - ADDED    → 追加到对应模块 spec 的「已实现」节
    - MODIFIED → 替换对应条款
    - REMOVED  → 从模块 spec 中删除对应条款
    │
    ▼
⑤ 运行验证（测试 + 检查清单）
    │
    ▼
⑥ 把 docs/changes/<change-name>/ 整个目录移到 docs/archive/
```

### Delta 文件格式

`proposal.md`:
```markdown
# 变更提案: <标题>
> 日期: YYYY-MM-DD
> 影响模块: specs/<module>/spec.md

## 动机
为什么需要这个变更。

## 范围
改什么、不改什么。
```

`delta.md`:
```markdown
# Delta: <标题>
> 关联模块: specs/<module>/spec.md

## ADDED Requirements
- REQ-XXX: 新增需求

## MODIFIED Requirements
- REQ-XXX: 修改后内容（原: xxx）

## REMOVED Requirements
- REQ-XXX: 删除原因
```

`tasks.md`:
```markdown
# 实现任务
- [ ] 任务 1
- [ ] 任务 2
```

### 什么时候需要 Plan

| 变更规模 | 流程 |
|---------|------|
| 小改动（单模块、1-3 天） | Delta → tasks.md → 实现 → 归档 |
| 中改动（多模块、< 1 周） | Delta → tasks.md → 实现 → 归档 |
| **大功能（跨多迭代、> 1 周）** | Delta → **Plan** → tasks.md → 实现 → 归档 |

Plan 保留给需要项目管理级追踪的大功能（如 MVP 桌面应用 9 个 Iter），放在 `docs/plans/`。小变更的 tasks.md 直接写在 Delta 目录里。

### 引用约定

- 代码中文档引用：`docs/specs/<module>/spec.md`（如 `docs/specs/tools/spec.md`）
- 模块间交叉引用：同上格式
- Spec 文件头部必须标注归档参考和最后更新日期
- 历史文档中的旧 spec 路径不需要更新（它们是历史快照）

## 执行约束

### 代码修改前检查

修改 `src/` 代码前必须确认：
1. 对应模块已在 `docs/specs/<module>/spec.md` 中注册
2. 如果是新模块，先在 `docs/specs/architecture/spec.md` 中注册，再创建模块 spec

### Python 命令

所有 Python 命令必须通过 `uv run python` 执行，不使用裸 `python`。

### 验证

每次实现完成后：
1. 运行测试：`uv run pytest tests/ -v`
2. 检查 spec 一致性：确认 delta.md 中的条款已正确合并
3. 更新 spec 的「最后更新」日期
