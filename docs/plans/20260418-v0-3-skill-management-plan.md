# v0.3 Skill Management 实施计划

> Date: 2026-04-18
> Goal: 完善 skill 管理机制 — 内置 skill + 路由匹配 + prompt 注入 + 格式验证
> 对齐规范: `docs/specs/20260416-06-skill-management-spec.md`
> 依赖: v0.2 已完成 SkillManager 基础加载能力

---

## 背景

v0.2 的 skill 系统只有 `SkillManager` 基础加载器，能扫描目录找 `SKILL.md` 文件并解析，但：
- 没有内置 skill 文件（只有 2 个测试 fixture）
- 没有技能路由（无法根据用户输入匹配 skill）
- 没有 skill 注入到 LLM system prompt
- 没有 skill 格式验证

---

## Task S1: SkillValidator

> Spec: `20260416-06-skill-management-spec.md` §10.4
> 新建: `src/sloth_agent/memory/skill_validator.py`

### 实现内容

1. **SkillValidator** — 验证 SKILL.md 文件格式和内容
   - frontmatter 必须包含 `name`, `trigger`, `version`
   - 必须包含 `description`
   - 不能包含 `TBD`/`TODO`/`未完成` 占位符
   - 重复检测（不能与已有 skill 描述重复度过高）
   - 文件路径合法性（必须在合法 skill 目录下）

2. **验证结果数据类**
   - `ValidationResult: valid, errors: list[str], warnings: list[str]`

3. **CLI 命令**
   - `sloth skills validate <path>` — 验证单个或目录下所有 SKILL.md

### 文件清单
| 文件 | 操作 |
|------|------|
| `src/sloth_agent/memory/skill_validator.py` | 新建 |
| `src/sloth_agent/cli/skill_cmd.py` | 修改 (添加 validate 子命令) |
| `tests/memory/test_skill_validator.py` | 新建 |

---

## Task S2: SkillRouter

> Spec: `20260416-06-skill-management-spec.md` §3.2
> 新建: `src/sloth_agent/memory/skill_router.py`

### 实现内容

1. **SkillRouter** — 用户输入 → 匹配最佳 skill
   - 关键词匹配：用户输入包含 skill 名称或触发词
   - 斜杠命令：`/skill <name>` 直接匹配
   - FTS 搜索：在 skill 描述和名称中搜索关键词
   - 返回匹配的 skill 列表 + 置信度评分

2. **匹配策略**
   - 精确名称匹配 → 1.0 置信度
   - 触发词匹配（`manual_trigger_words`） → 0.8
   - 描述关键词匹配 → 0.5
   - 无匹配 → None

3. **与 Chat REPL 集成**
   - REPL 中用户输入时自动匹配并建议可用 skill
   - `/auto-skill` 开关：开启后自动激活匹配到的 skill

### 文件清单
| 文件 | 操作 |
|------|------|
| `src/sloth_agent/memory/skill_router.py` | 新建 |
| `src/sloth_agent/chat/repl.py` | 修改 (集成 skill 匹配) |
| `tests/memory/test_skill_router.py` | 新建 |

---

## Task S3: 内置 Skill

> Spec: `20260416-06-skill-management-spec.md` §2.1, §11
> 新建: `skills/builtin/` 目录 + SKILL.md 文件

### 实现内容

第一阶段内置 5 个核心 skill（从 37 技能表中选最实用的）：

| 技能 | 目录 | 触发方式 | 说明 |
|------|------|---------|------|
| `test-driven-development` | `skills/builtin/tdd/` | manual | RED-GREEN-REFACTOR 循环 |
| `systematic-debugging` | `skills/builtin/debugging/` | manual | 四阶段根因分析 |
| `writing-plans` | `skills/builtin/planning/` | manual | 微任务分解 |
| `code-review` | `skills/builtin/code-review/` | manual | 代码审查 checklist |
| `unit-test` | `skills/builtin/unit-test/` | manual | 单元测试编写规范 |

每个 skill 目录结构：
```
skills/builtin/<name>/
├── SKILL.md           # 主文件
└── references/        # 参考资料（可选）
```

### 文件清单
| 文件 | 操作 |
|------|------|
| `skills/builtin/tdd/SKILL.md` | 新建 |
| `skills/builtin/debugging/SKILL.md` | 新建 |
| `skills/builtin/planning/SKILL.md` | 新建 |
| `skills/builtin/code-review/SKILL.md` | 新建 |
| `skills/builtin/unit-test/SKILL.md` | 新建 |
| `tests/skills/` | 新建 (内置 skill 测试) |

---

## Task S4: Skill 注入 LLM Prompt

> Spec: `20260416-06-skill-management-spec.md` §3.1
> 修改: `src/sloth_agent/core/context_window.py`

### 实现内容

1. **SkillInjector** — 将匹配的 skill 内容注入 system prompt
   - 接收 SkillRouter 的匹配结果
   - 将 skill 内容格式化后追加到 system prompt 末尾
   - 控制注入的 token 量（单个 skill 不超过 4K tokens）
   - 多个 skill 时按置信度排序，取 top-N

2. **与 Builder/Reviewer/Chat REPL 集成**
   - Builder: 在构建 system prompt 时注入活跃 skill
   - Reviewer: 注入代码审查相关 skill
   - Chat REPL: 注入匹配的技能

3. **Skill 管理 CLI 增强**
   - `sloth skills list` — 列出所有可用 skill（builtin + user）
   - `sloth skills show <name>` — 显示单个 skill 详情
   - `sloth skills search <query>` — 搜索 skill

### 文件清单
| 文件 | 操作 |
|------|------|
| `src/sloth_agent/memory/skill_injector.py` | 新建 |
| `src/sloth_agent/core/context_window.py` | 修改 (集成 skill 注入) |
| `src/sloth_agent/cli/skill_cmd.py` | 新建 |
| `tests/memory/test_skill_injector.py` | 新建 |

---

## Task S5: Skill 注册表

> Spec: `20260416-06-skill-management-spec.md` §11
> 新建: `src/sloth_agent/memory/skill_registry.py`

### 实现内容

1. **SkillRegistry** — 集中管理所有 skill 元数据
   - 加载 builtin + user + local 三类 skill
   - 提供 `get_all()`, `get(id)`, `search(query)` 接口
   - 与 `SkillManager` 解耦：Manager 负责文件加载，Registry 负责路由查询
   - 支持 skill 启用/禁用开关

2. **CLI 子命令集成**
   - `sloth skills` 命令改用 SkillRegistry
   - 显示 skill 来源（builtin / user / local）

3. **测试**
   - Registry CRUD
   - 多源 skill 加载（builtin + user）
   - 启用/禁用逻辑

### 文件清单
| 文件 | 操作 |
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

## 预期成果

- 5 个内置 skill 可用
- Skill 路由匹配：用户输入自动识别并建议 skill
- Skill 注入 Builder/Reviewer/Chat 的 system prompt
- CLI `sloth skills` 子命令完整可用
- 用户可自定义 skill（放入 `local_skills/`）
- 对应测试覆盖：约 30-40 个测试用例
