# Sloth Agent 文档命名规范

> 版本: v1.0.0
> 日期: 2026-04-15

---

## 1. 概述

Sloth Agent 使用统一的文档命名规范，确保文档易于查找、排序和自动化处理。

---

## 2. 命名格式

### 2.1 基本格式

```
YYYYMMDD-event-description-type.md
```

| 组成部分 | 说明 | 格式要求 |
|---------|------|---------|
| `YYYYMMDD` | 8位日期 | 必须是当天日期 |
| `event-description` | 事件描述 |  kebab-case (小写+连字符) |
| `type` | 文档类型 | 见下方类型列表 |
| `.md` | Markdown 扩展名 | 固定为 .md |

### 2.2 文档类型

| 类型 | 说明 | 存放目录 |
|------|------|---------|
| `design-spec` | 设计规格文档 | `docs/specs/` |
| `implementation-plan` | 实现计划 | `docs/plans/` |
| `report` | 工作报告 | `docs/reports/` |
| `user-guide` | 用户手册 | `docs/guides/` |

---

## 3. 示例

### 正确命名

```
# 设计规格
20260416-02-tools-invocation-spec.md
20260415-card-game-design-spec.md
20260416-wuxing-app-design-spec.md

# 实现计划
20260415-tools-implementation-plan.md
20260415-card-game-implementation-plan.md

# 工作报告
20260415-daily-report.md
20260416-weekly-report.md

# 用户指南
20260414-user-guide.md
20260415-api-guide.md
```

### 错误命名

```
# ❌ 缺少日期
tools-design-spec.md

# ❌ 日期格式错误
2026-04-15-tools-design-spec.md  # 使用了连字符
240415-tools-design-spec.md       # 应该是8位

# ❌ 类型错误
20260415-tools-design.md          # 缺少类型后缀

# ❌ 大小写错误
20260415-Tools-Design-Spec.md    # 应该小写
```

---

## 4. 目录结构

```
docs/
├── specs/           # 设计规格文档
│   ├── 20260416-02-tools-invocation-spec.md
│   └── 20260416-card-game-design-spec.md
│
├── plans/           # 实现计划
│   ├── 20260415-tools-implementation-plan.md
│   └── 20260415-card-game-implementation-plan.md
│
├── reports/         # 工作报告
│   ├── 20260415-daily-report.md
│   └── 20260416-weekly-report.md
│
└── guides/         # 用户指南
    ├── 20260414-user-guide.md
    └── 20260415-api-guide.md
```

---

## 5. 代码集成

Sloth Agent 框架内置了命名规范的检查和处理：

```python
from sloth_agent.core.naming import DocumentNaming

# 创建符合规范的文件名
filename = DocumentNaming.make_filename(
    date="20260415",
    description="tools-design",
    doc_type="design-spec"
)
# 结果: "20260415-tools-design-design-spec.md"

# 检查文件名是否合法
DocumentNaming.is_valid("20260416-02-tools-invocation-spec.md")
# 结果: True

# 解析文件名
DocumentNaming.parse_filename("20260416-02-tools-invocation-spec.md")
# 结果: {"date": "20260415", "description": "tools-design", "type": "design-spec"}

# 获取某类型最新文档
latest = DocumentNaming.get_latest(Path("docs/specs"), doc_type="design-spec")
```

---

## 6. 自动规则

1. **Spec 文件**: 每次重大设计变更应创建新的 spec
2. **Plan 文件**: 每个 spec 对应一个 implementation-plan
3. **Report 文件**: 每日自动生成，格式 `YYYYMMDD-daily-report.md`
4. **清理**: 过期的 spec/plan 应该标记为废弃，而非删除

---

## 7. 版本控制

- 同一事件的后续版本使用同一日期
- 如需更新：`20260416-02-tools-invocation-spec.md` → 保持原名，更新内容
- 重大变更：创建新的 spec，如 `20260420-tools-invocation-spec-v2.md`

---

*规范版本: v1.0.0*
*创建日期: 2026-04-15*
