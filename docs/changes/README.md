# Delta Spec 变更目录

## 用法

每次需求变更在此目录下创建子目录：

```
docs/changes/<change-name>/
├── proposal.md    # 为什么改、改什么范围
├── delta.md       # 增量规格（ADDED/MODIFIED/REMOVED）
└── tasks.md       # 实现任务清单
```

## Delta 格式

```markdown
# Delta: <变更标题>

> 关联模块: specs/<module>/spec.md
> 日期: YYYY-MM-DD

## ADDED Requirements
- REQ-XXX: 新增需求描述

## MODIFIED Requirements
- REQ-XXX: 修改后的需求描述（原内容：xxx）

## REMOVED Requirements
- REQ-XXX: 删除原因
```

## 工作流

1. **开始变更** — 在 `docs/changes/` 下创建变更目录，写 proposal + delta + tasks
2. **实现** — 按 tasks.md 逐项完成
3. **合并** — 将 delta 内容合并到 `docs/specs/<module>/spec.md`
4. **归档** — 变更目录移到 `docs/archive/<change-name>/`
