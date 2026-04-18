# 20260416-06-skill-management-implementation-plan.md

> Spec 来源: `docs/specs/20260416-06-skill-management-spec.md`
> Plan 文件: `docs/plans/20260416-06-skill-management-implementation-plan.md`
> 对应 Arch: `docs/specs/00000000-00-architecture-overview.md` §6.0, §7.2 shared/skills

---

## v0.1.0 实现状态（已完成）

v0.1.0 实现 SKILL.md 加载与按需注入机制：从文件系统扫描、解析 frontmatter、提供技能内容供 prompt 注入。不实现 skill_router、自动匹配、向量检索（v0.3.0+）。

### 步骤 1: 实现 SkillManager（SKILL.md 加载）✅

**文件**: `src/sloth_agent/memory/skills.py` — 已实现

**已实现**:
- `Skill` dataclass：`id`, `name`, `source`, `trigger`, `description`, `content`, `allowed_tools`
- `Skill.from_markdown()`：解析 YAML frontmatter + 正文
- `SkillManager`：`load_all_skills()`, `get_skill_content()`, `list_skills()`

**验收**: 能正确加载测试 fixture 下的 SKILL.md 文件。✅ 3 tests pass

### 步骤 2: 实现 SKILL.md 按需注入 ✅

**文件**: `src/sloth_agent/core/context_window.py` — 已实现基础注入

**已实现**: ContextWindowManager 支持 skill 内容拼接为 system prompt 字符串

**验收**: 指定 skill_id 列表后能正确拼接。✅

### 步骤 3: 单元测试 ✅

| 文件 | 覆盖 | 测试数 |
|------|------|--------|
| `tests/memory/test_skills.py` | SKILL.md 加载、解析、内容获取 | 3 ✅ |

---

## v0.2.0 实现状态（已完成）

v0.2.0 在 Chat REPL 中增加 `/skills` 命令，扫描 `local_skills/` 目录并列出可用 skill。

### Chat REPL `/skills` 命令 ✅

**文件**: `src/sloth_agent/chat/repl.py` — 已实现

**已实现**: `/skills` 列出 `local_skills/` 下的 skill 名称和描述

**验收**: REPL 中可列出本地 skill。✅

---

## v0.3.0 规划（待实现）

> 目标：完善 skill 管理机制 — 内置 skill + 路由匹配 + prompt 注入 + 格式验证 + 注册表
> 依赖: v0.1.0/v0.2.0 已完成基础加载和 REPL 列出能力

### Task S1: SkillValidator

> Spec: `20260416-06-skill-management-spec.md` §10.4

**文件**: `src/sloth_agent/memory/skill_validator.py`（新建）

验证 SKILL.md 文件格式和内容：
- frontmatter 必须包含 `name`, `trigger`, `version`, `description`
- 不能包含 `TBD`/`TODO`/`未完成` 占位符
- 重复检测（不能与已有 skill 描述重复度过高）
- 文件路径合法性

**CLI**: `sloth skills validate <path>` — 验证单个或目录下所有 SKILL.md

**文件清单**:
| 文件 | 动作 |
|------|------|
| `src/sloth_agent/memory/skill_validator.py` | 新建 |
| `src/sloth_agent/cli/skill_cmd.py` | 新建 (validate 子命令) |
| `tests/memory/test_skill_validator.py` | 新建 |

---

### Task S2: SkillRouter

> Spec: `20260416-06-skill-management-spec.md` §3.2

**文件**: `src/sloth_agent/memory/skill_router.py`（新建）

用户输入 → 匹配最佳 skill：
- 精确名称匹配 → 1.0 置信度
- 触发词匹配 → 0.8
- 描述关键词匹配（FTS） → 0.5
- 无匹配 → None

**与 Chat REPL 集成**: 用户输入时自动匹配并建议可用 skill

**文件清单**:
| 文件 | 动作 |
|------|------|
| `src/sloth_agent/memory/skill_router.py` | 新建 |
| `src/sloth_agent/chat/repl.py` | 修改 (集成 skill 匹配) |
| `tests/memory/test_skill_router.py` | 新建 |

---

### Task S3: 内置 Skill

> Spec: `20260416-06-skill-management-spec.md` §2.1, §11

**目录**: `skills/builtin/`（新建）

第一阶段内置 5 个核心 skill：

| 技能 | 目录 | 触发方式 | 说明 |
|------|------|---------|------|
| `test-driven-development` | `skills/builtin/tdd/` | manual | RED-GREEN-REFACTOR 循环 |
| `systematic-debugging` | `skills/builtin/debugging/` | manual | 四阶段根因分析 |
| `writing-plans` | `skills/builtin/planning/` | manual | 微任务分解 |
| `code-review` | `skills/builtin/code-review/` | manual | 代码审查 checklist |
| `unit-test` | `skills/builtin/unit-test/` | manual | 单元测试编写规范 |

**文件清单**:
| 文件 | 动作 |
|------|------|
| `skills/builtin/tdd/SKILL.md` | 新建 |
| `skills/builtin/debugging/SKILL.md` | 新建 |
| `skills/builtin/planning/SKILL.md` | 新建 |
| `skills/builtin/code-review/SKILL.md` | 新建 |
| `skills/builtin/unit-test/SKILL.md` | 新建 |
| `tests/skills/` | 新建 (内置 skill 测试) |

---

### Task S4: Skill 注入 LLM Prompt

> Spec: `20260416-06-skill-management-spec.md` §3.1, §4

**文件**: `src/sloth_agent/memory/skill_injector.py`（新建）

将匹配的 skill 内容注入 system prompt：
- 接收 SkillRouter 的匹配结果
- 控制注入的 token 量（单个 skill 不超过 4K tokens）
- 多个 skill 时按置信度排序，取 top-N
- 与 Builder/Reviewer/Chat REPL 集成

**CLI 增强**:
- `sloth skills list` — 列出所有可用 skill（builtin + user）
- `sloth skills show <name>` — 显示单个 skill 详情
- `sloth skills search <query>` — 搜索 skill

**文件清单**:
| 文件 | 动作 |
|------|------|
| `src/sloth_agent/memory/skill_injector.py` | 新建 |
| `src/sloth_agent/core/context_window.py` | 修改 (集成 skill 注入) |
| `src/sloth_agent/cli/skill_cmd.py` | 新建 |
| `tests/memory/test_skill_injector.py` | 新建 |

---

### Task S5: Skill 注册表

> Spec: `20260416-06-skill-management-spec.md` §11

**文件**: `src/sloth_agent/memory/skill_registry.py`（新建）

集中管理所有 skill 元数据：
- 加载 builtin + user + local 三类 skill
- 提供 `get_all()`, `get(id)`, `search(query)` 接口
- 与 `SkillManager` 解耦：Manager 负责文件加载，Registry 负责路由查询
- 支持 skill 启用/禁用开关

**文件清单**:
| 文件 | 动作 |
|------|------|
| `src/sloth_agent/memory/skill_registry.py` | 新建 |
| `src/sloth_agent/cli/skill_cmd.py` | 修改 |
| `src/sloth_agent/cli/app.py` | 修改 (注册 skills 子命令) |
| `tests/memory/test_skill_registry.py` | 新建 |

---

## 依赖关系

```
S1 (Validator) ──┐
S2 (Router)  ────┼──→ S4 (Injector) ──→ S5 (Registry)
S3 (Builtins) ───┘
```

S1/S2/S3 可并行。S4 依赖 S1+S2+S3。S5 依赖 S4。

---

## 预期验收标准

- [ ] 5 个内置 skill 可通过 `sloth skills list` 查看
- [ ] SkillValidator 拒绝无效 SKILL.md 文件
- [ ] SkillRouter 能根据用户输入匹配到正确 skill
- [ ] 匹配的 skill 内容注入 Builder/Reviewer/Chat 的 system prompt
- [ ] CLI `sloth skills` 子命令完整可用（list/show/search/validate）
- [ ] 对应测试覆盖：约 30-40 个测试用例

---

*Plan 版本: v1.0.0 | 创建: 2026-04-17 | 最后更新: 2026-04-18*
