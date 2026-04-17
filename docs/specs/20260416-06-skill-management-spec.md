# Skill 管理设计规格

> 版本: v1.1.0
> 日期: 2026-04-16
> 最后更新: 2026-04-18
> 状态:
>   - v0.1 已实现: SkillManager (from_markdown / load_all_skills / get_skill_content)
>     实现文件: `src/sloth_agent/memory/skills.py` | 测试: `tests/memory/test_skills.py`
>   - v0.2 已实现: Chat REPL `/skills` 命令（扫描 local_skills/ 目录）
>     实现文件: `src/sloth_agent/chat/repl.py`
>   - v0.3 规划中: SkillValidator + SkillRouter + 内置 skill + SkillInjector + SkillRegistry

---

## 1. 需求描述

### 1.1 问题

现有 `SkillManager` 功能不完整：
- 只有基础的 CRUD，没有技能加载到 LLM 的机制
- `consider_skill_extension` 和 `consider_skill_fix` 是 TODO
- 没有技能路由（chat mode 中如何识别和激活技能）
- 与 Phase-Role-Architecture 的 37 skills 注册表没有关联
- Claude Code skill 格式（`SKILL.md` + frontmatter）与 Sloth Agent skill 格式不统一

### 1.2 目标

| 版本 | 能力 | 说明 |
|------|------|------|
| **v1.0** | 统一 skill 格式 + 加载机制 | 兼容 Claude Code SKILL.md 格式，支持从文件系统加载 |
| **v1.1** | 技能路由 + 自动激活 | Chat mode 中识别用户意图，自动匹配并激活技能 |
| **v1.2** | 技能自动进化 | 从错误和经验中自动生成/修正技能 |

---

## 2. 架构设计

### 2.1 Skill 来源

```
┌─────────────────────────────────────────────────────────────┐
│                    Skill 来源                                │
├──────────────┬──────────────┬────────────────────────────────┤
│ Superpowers  │ gstack       │ 用户 / 进化                     │
│ (14 个)      │ (23 个)      │                                │
│ skills/      │ skills/      │ skills/user/  skills/evolved/  │
│ superpowers/ │ gstack/      │                                │
└──────────────┴──────────────┴────────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │    SkillRegistry      │
              │ (37 个预定义 skills)   │
              │ src/workflow/registry │
              └───────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │    SkillManager       │
              │ (加载 + 路由 + 进化)   │
              │ src/memory/skills.py  │
              └───────────────────────┘
```

**触发方式**：

| 来源 | 数量 | 自动触发 | 手动触发（/skill） | 可自我进化 |
|------|------|---------|-------------------|-----------|
| Superpowers | 14 | 是 | 是 | 是（就地修订） |
| gstack | 23 | 否 | 是 | 是（就地修订） |
| 用户自定义 | 不限 | 否 | 是 | 是 |
| 自动进化 | 不限 | 否 | 是 | 是 |

> Superpowers 同时支持自动触发和手动触发：自动触发时由 ChatSession 根据意图匹配激活；手动触发时通过 `/skill <name>` 调用。

### 2.2 Skill 格式统一

Sloth Agent 统一采用 Claude Code skill 格式：

```
{skill_dir}/
├── SKILL.md                    # 主文件，YAML frontmatter + 指令内容
├── references/                 # 参考资料（可选）
│   └── *.md
└── templates/                  # 模板文件（可选）
    └── *.md
```

**SKILL.md 格式**:

```yaml
---
name: skill-id
description: One-line description
trigger: auto | manual | auto+manual | error-driven
source: builtin | user | evolved
version: 1.0.0
allowed-tools: [Bash, Read, Edit, ...]
---

# Skill Name

Skill instructions go here...

## When to use

...

## Steps

1. step 1
2. step 2
```

**`trigger` 字段说明**：
- `auto` — 由 ChatSession 自动匹配触发（仅 Superpowers 中的部分技能）
- `manual` — 只能通过 `/skill <name>` 或 LLM 主动调用触发
- `auto+manual` — 同时支持自动和手动触发（Superpowers 的全部技能）
- `error-driven` — 在错误处理流程中被触发

**`source` 字段说明**：
- `builtin` — 内建技能（Superpowers / gstack），随 repo 分发
- `user` — 用户自定义技能
- `evolved` — 自动进化生成的新技能

### 2.3 与 Phase-Role-Architecture 的 Skill 模型的关系

Phase-Role-Architecture 中的 `Skill` 是**元数据模型**：

```python
@dataclass
class Skill:
    id: str           # "brainstorming"
    name: str         # "Brainstorming"
    source: str       # "superpowers"
    trigger: str      # "auto+manual"
    description: str  # "通过提问精炼需求"
```

SkillManager 中的 `Skill` 是**完整模型**，包含内容：

```python
class Skill:
    id: str
    name: str
    source: str
    trigger: str
    description: str
    content: str           # SKILL.md 的正文
    allowed_tools: list    # 允许使用的工具
    references: list       # 参考资料路径
    templates: list        # 模板文件路径
```

**统一方案**：元数据从 `SkillRegistry` 获取，内容从文件系统加载。两者通过 `skill_id` 关联。

---

## 3. 模块定义

### 3.1 SkillManager

**文件**: `src/memory/skills.py`（重写）

```
职责: Skill 的加载、搜索、路由、进化
```

**核心方法**:

| 方法 | 说明 |
|------|------|
| `load_skill(skill_id)` | 从文件系统加载技能内容 |
| `load_all_skills()` | 加载所有技能（预定义 + 用户 + 进化） |
| `get_skill_content(skill_id)` | 获取技能的完整内容（用于注入 LLM prompt） |
| `search_skills(query)` | 按关键词搜索技能 |
| `match_skill(user_input)` | 从用户输入识别最匹配的技能（v1.1） |
| `save_skill(skill)` | 保存技能到文件系统 |
| `revise_skill(skill_id, new_content, reason)` | 修订技能（就地覆盖 SKILL.md） |
| `generate_skill_from_error(error)` | 从错误生成新技能 |
| `list_skills()` | 列出所有技能 |

### 3.2 SkillRouter

**文件**: `src/memory/skill_router.py`（新增，v1.1）

```
职责: 从用户输入识别意图，匹配最合适的技能
```

**核心方法**:

| 方法 | 说明 |
|------|------|
| `match_skill(user_input)` | 返回最匹配的技能 ID |
| `get_skill_prompt(skill_id)` | 获取技能的系统提示 |

**匹配策略（v1.1）**:
1. 关键词匹配：用户输入包含 skill 名称或触发词
2. 斜杠命令：`/skill brainstorming` 直接匹配
3. FTS 搜索：在技能描述中搜索关键词

**匹配策略（v1.2）**:
4. 向量检索：使用嵌入模型做语义匹配

### 3.3 技能来源目录

| 来源 | 目录 | 说明 |
|------|------|------|
| Superpowers | `skills/superpowers/` | 14 个内建技能，auto+manual 触发 |
| gstack | `skills/gstack/` | 23 个内建技能，manual 触发 |
| 用户自定义 | `skills/user/` | 用户创建的技能 |
| 自动进化 | `skills/evolved/` | 从错误/经验生成的**新**技能 |

> 内建技能的自我进化直接原地修改 `skills/superpowers/{skill}/SKILL.md` 或 `skills/gstack/{skill}/SKILL.md`，版本号递增。只有 37 个预定义之外的全新技能才放到 `skills/evolved/`。

---

## 4. 技能加载流程

```
Sloth Agent 启动:
  1. SkillRegistry.get_all() → 获取 37 个预定义技能元数据
  2. SkillManager.load_all_skills() → 从文件系统加载技能内容
     ├── 扫描内建目录（superpowers/, gstack/）
     ├── 扫描用户目录（user/）
     └── 扫描进化目录（evolved/）
  3. 合并元数据和内容 → 完整技能库
  4. 构建搜索索引（FTS）
```

**技能注入到 LLM prompt**:

```
当用户触发 /skill brainstorming 时:
  1. SkillRouter.match_skill("brainstorming") → "brainstorming"
  2. SkillManager.get_skill_content("brainstorming") → 完整内容
  3. 注入系统提示:
     "你正在使用 brainstorming 技能：
      {skill_content}
      请按照上述技能描述的步骤执行。"
```

---

## 5. 技能进化流程

```
触发条件（4 种）:
  ├── Error-Driven: 执行出错 → SkillManager.generate_skill_from_error(error)
  ├── Experience-Accumulation: 连续成功 10+ 次 → 提取可复用模式
  ├── Periodic-Audit: 每周一 09:00 → 对比技能库与实际使用率
  └── Knowledge-Gap: 发现无对应技能处理的任务 → 创建新技能

进化路径:
  ├── 已有技能（37 个预定义之一）→ 就地修订 SKILL.md，版本号递增
  └── 全新技能 → 保存到 skills/evolved/，分配新 skill_id

生成流程:
  1. 诊断: 分析错误/经验/缺口
  2. 生成: LLM 生成技能内容（SKILL.md 格式）
  3. 验证: SkillValidator 检查格式合规性
  4. 存储: 保存到对应目录（原地 或 evolved/）
  5. 索引: 更新搜索索引
```

### 5.1 SkillValidator

**文件**: `src/memory/skill_validator.py`（新增）

```
职责: 验证技能文件的合规性
```

**验证规则**:

| 检查项 | 条件 | 不通过则 |
|--------|------|---------|
| frontmatter | 必须包含 name, source, version | 拒绝保存 |
| 内容 | 不能为空 | 拒绝保存 |
| 占位符 | 不能有 TBD/TODO/未完成 | 拒绝保存 |
| 重复 | 不能与已有技能同名 | 拒绝保存，建议用 revise |

---

## 6. 文件结构

```
src/
  memory/
    skills.py              # 重写，SkillManager
    skill_router.py        # 新增 (v1.1), SkillRouter
    skill_validator.py     # 新增, SkillValidator
skills/                    # 技能目录
  ├── superpowers/         # 14 个内建技能（auto+manual，可就地进化）
  ├── gstack/              # 23 个内建技能（manual，可就地进化）
  ├── user/                # 用户自定义
  └── evolved/             # 全新技能（37 个预定义之外的）
tests/
  memory/
    test_skills.py         # 新增
    test_skill_router.py   # 新增 (v1.1)
    test_skill_validator.py # 新增
```

---

## 7. 测试策略

| 测试 | 说明 |
|------|------|
| `test_load_skill` | 从文件加载技能，内容正确 |
| `test_load_all_skills` | 加载所有技能，数量 >= 37 |
| `test_get_skill_content` | 获取技能内容，非空 |
| `test_search_skills` | 按关键词搜索，返回相关技能 |
| `test_save_skill` | 保存技能，文件存在 |
| `test_revise_skill` | 修订技能，版本号递增 |
| `test_skill_validator_valid` | 合规技能通过验证 |
| `test_skill_validator_invalid` | 不合规技能被拒绝 |

---

## 8. 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| 技能文件格式不一致 | 加载失败 | SkillValidator 严格验证 |
| 技能内容过大 | 超出 LLM context | 截断或分段注入 |
| 自动进化生成错误内容 | 技能质量下降 | 验证 + 人工审核（v1.2） |

---

---

## 10. Skill 自动进化机制（从跨模块规范迁入）

### 10.1 触发机制（4 种）

| 触发类型 | 条件 | 优先级 |
|---------|------|--------|
| **Error-Driven** | 执行出错时 | P0 |
| **Experience-Accumulation** | 连续成功执行 10+ 次后 | P2 |
| **Periodic-Audit** | 每周一 09:00 自动审计 | P1 |
| **Knowledge-Gap** | 发现无对应 Skill 处理的任务类型 | P2 |

### 10.2 进化流程

```
┌─────────────────────────────────────────────────────────────┐
│  SkillEvolutionEngine                                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [触发] ──▶ [诊断] ──▶ [生成/修正] ──▶ [验证] ──▶ [存储]   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 1: 触发诊断 (Diagnosis)                              │
├─────────────────────────────────────────────────────────────┤
│  - Error-Driven: 分析错误类型和上下文                        │
│  - Experience: 统计成功模式，提取可复用流程                  │
│  - Audit: 对比 Skill 库与实际使用率                          │
│  - Gap: 发现新任务类型无对应 Skill                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 2: 生成/修正 (Generation/Revision)                   │
├─────────────────────────────────────────────────────────────┤
│  SkillGenerator:                                            │
│    - 根据错误上下文生成新 Skill                              │
│    - 输出: YAML 格式 Skill 定义                              │
│                                                              │
│  SkillReviser:                                             │
│    - 修正已有 Skill 的错误描述                               │
│    - 扩展 Skill 的适用范围                                  │
│    - 更新过时的示例或命令                                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 3: 验证 (Validation)                                 │
├─────────────────────────────────────────────────────────────┤
│  SkillValidator:                                            │
│    - frontmatter 完整性                                       │
│    - required_sections 存在                                 │
│    - 无占位符 (TBD/TODO/未完成)                              │
│    - 无重复 Skill 定义                                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 4: 存储 (Storage)                                    │
├─────────────────────────────────────────────────────────────┤
│  SkillRepository:                                           │
│    - 保存到 skills/ 目录                                    │
│    - 更新 skills/index.md                                   │
│    - 触发 SkillManager 重新加载                              │
└─────────────────────────────────────────────────────────────┘
```

### 10.3 Skill 结构定义

```yaml
---
name: skill-name
description: One-line description
trigger: error-driven|experience|periodic-audit|knowledge-gap
frequency: high|medium|low
last_revised: YYYYMMDD
version: x.y.z
---

# Trigger Context
- 错误类型:
- 错误消息:

# Resolution
## Steps
1. step 1
2. step 2

## Commands
- command 1
- command 2

## Validation
- 验证命令

# Examples
- example 1
- example 2
```

### 10.4 SkillValidator 验证规则

| 检查项 | 条件 | 不通过则 |
|--------|------|---------|
| frontmatter | 必须包含 name, trigger, version | 拒绝保存 |
| required_sections | 必须有 Trigger Context, Resolution | 拒绝保存 |
| 占位符 | 不能有 TBD/TODO/未完成 | 拒绝保存 |
| 重复检测 | 不能与已有 Skill 描述重复 | 拒绝保存 |

### 10.5 进化记录

每次 Skill 进化生成报告：
```
docs/reports/
└── YYYYMMDD-skill-evolution-report.md
```

---

---

## 11. 37 技能路由表（从 20260416-37-skills-route-table.md 迁入）

> 参考: Superpowers (14 skills) + gstack (23 skills) = 37 skills

### 11.1 Superpowers 技能（14 个，auto+manual）

| 技能 | 阶段 | 说明 |
|------|------|------|
| `brainstorming` | 阶段一 | 通过提问精炼需求，分段呈现设计方案 |
| `writing-plans` | 阶段二 | 将工作分解为 2-5 分钟微任务，包含文件路径、测试、验证步骤 |
| `test-driven-development` | 阶段三 | RED-GREEN-REFACTOR 循环 |
| `subagent-driven-development` | 阶段三 | 每个子任务创建独立子代理执行 |
| `using-git-worktrees` | 阶段三 | 隔离工作空间 |
| `systematic-debugging` | 阶段四 | 四阶段根因分析 |
| `requesting-code-review` | 阶段五 | 独立 reviewer 通道 |
| `verification-before-completion` | 阶段五 | 完成前收集证据 |
| `finishing-a-development-branch` | 阶段七 | 分支收尾，合并/PR 决策 |
| `receiving-code-review` | - | 接收审查反馈 |
| `executing-plans` | - | 批量执行计划，带 checkpoint |
| `dispatching-parallel-agents` | - | 并发子代理工作流 |
| `writing-skills` | - | 创建/修改技能 |
| `using-superpowers` | - | 技能系统介绍 |

### 11.2 gstack 命令（23 个手动命令）

| 技能 | 阶段 | 说明 |
|------|------|------|
| `/office-hours` | 阶段一 | 6 个强制问题诊断产品方向 |
| `/autoplan` | 阶段二 | CEO → 设计 → 工程三阶段自动审查 |
| `/browse` | 阶段四 | 真实 Chromium 浏览器 |
| `/investigate` | 阶段四 | 浏览器级系统调试 |
| `/review` | 阶段五 | 发现通过 CI 但生产会炸的 bug |
| `/codex` | 阶段五 | 通过 OpenAI Codex CLI 交叉分析 |
| `/qa` | 阶段六 | 真实浏览器端到端测试 |
| `/cso` | 阶段六 | OWASP Top 10 + STRIDE 威胁模型 |
| `/plan-design-review` | 阶段六 | 80 项设计审计 |
| `/ship` | 阶段七 | 测试 + 覆盖率 + PR |
| `/land-and-deploy` | 阶段七 | CI + 部署验证 |
| `/canary` | 阶段八 | 控制台错误 + 性能回归监控 |
| `/qa-only` | 阶段六 | 报告模式（不修改代码） |
| `/plan-ceo-review` | 阶段二 | 重新思考问题，4 种模式 |
| `/plan-eng-review` | 阶段二 | 锁定架构、数据流、边界条件 |
| `/plan-devex-review` | 阶段二 | 交互式 DX 审查 |
| `/design-consultation` | 阶段一 | 从零构建设计系统 |
| `/design-shotgun` | 阶段一 | 生成 4-6 个 AI 方案变体 |
| `/design-html` | - | 生成生产级 HTML/CSS |
| `/design-review` | - | 审计 + 修复 |
| `/devex-review` | - | 实时审计 onboarding 流程 |
| `/retro` | - | 每周团队回顾 |

### 11.3 技能与阶段映射

| 阶段 | Superpowers | gstack | 时段 |
| :--- | :--- | :--- | :--- |
| 阶段一 需求分析 | `brainstorming` | `/office-hours` | 晚上 |
| 阶段二 计划制定 | `writing-plans` | `/autoplan` | 晚上 |
| 阶段三 编码实现 | `TDD`, `subagent`, `git-worktrees` | | 白天 |
| 阶段四 调试排错 | `systematic-debugging` | `/browse`, `/investigate` | 白天 |
| 阶段五 代码审查 | `requesting-code-review`, `verification` | `/review`, `/codex` | 白天 |
| 阶段六 质量验证 | | `/qa`, `/cso`, `/plan-design-review` | 白天 |
| 阶段七 发布上线 | `finishing-a-branch` | `/ship`, `/land-and-deploy` | 白天 |
| 阶段八 上线监控 | | `/canary` | 白天 |

---

*规格版本: v1.1.0*
*创建日期: 2026-04-16*
