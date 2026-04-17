# 20260416-06-skill-management-implementation-plan.md

> Spec 来源: `docs/specs/20260416-06-skill-management-spec.md`
> Plan 文件: `docs/plans/20260416-06-skill-management-implementation-plan.md`
> 对应 Arch: `docs/specs/00000000-00-architecture-overview.md` §7.2 shared/skills

---

## 1. 目标

v1.0 实现 SKILL.md 加载与按需注入机制：从文件系统扫描、解析 frontmatter、提供技能内容供 prompt 注入。不实现 skill_router、自动匹配、向量检索（v1.1+）。

---

## 2. 步骤（按顺序执行）

### 步骤 1: 实现 SkillManager（SKILL.md 加载）

**文件**: `src/sloth_agent/memory/skills.py`（重写）

**内容** (spec §2.2, §3.1, v1.0 范围):

```python
@dataclass
class Skill:
    """完整技能模型，包含内容。"""
    id: str
    name: str
    source: str       # builtin | user | evolved
    trigger: str      # auto | manual | auto+manual | error-driven
    description: str
    content: str      # SKILL.md 正文（frontmatter 之后的内容）
    allowed_tools: list[str] = field(default_factory=list)

    @classmethod
    def from_markdown(cls, markdown_text: str) -> "Skill":
        """从 SKILL.md 文本解析技能。"""

class SkillManager:
    """Skill 的加载、内容获取。"""

    def __init__(self, skills_dirs: list[Path]):
        """
        Args:
            skills_dirs: 技能搜索目录列表，
                         如 [skills/superpowers/, skills/gstack/]
        """
        self.skills_dirs = skills_dirs

    def load_all_skills(self) -> list[Skill]:
        """从所有搜索目录扫描 SKILL.md 并加载。"""
        skills = []
        for skills_dir in self.skills_dirs:
            for skill_file in skills_dir.rglob("SKILL.md"):
                skills.append(Skill.from_markdown(skill_file.read_text()))
        return skills

    def get_skill_content(self, skill_id: str) -> str | None:
        """获取指定技能的完整内容（用于注入 LLM prompt）。"""
        for skill in self.load_all_skills():
            if skill.id == skill_id:
                return skill.content
        return None

    def list_skills(self) -> list[str]:
        """列出所有技能 ID。"""
        return [s.id for s in self.load_all_skills()]
```

**验收**: 能正确加载 `skills/superpowers/` 和 `skills/gstack/` 下的所有 SKILL.md 文件，`get_skill_content()` 返回非空内容。

---

### 步骤 2: 实现 SKILL.md 按需注入

**文件**: `src/sloth_agent/core/context_window.py`（修改）

**内容** (spec §4):

```python
class ContextWindowManager:
    def inject_skills(self, skill_ids: list[str], skill_manager: SkillManager) -> str:
        """将指定技能内容拼接为可注入 system prompt 的字符串。"""
        parts = []
        for sid in skill_ids:
            content = skill_manager.get_skill_content(sid)
            if content:
                parts.append(f"## Skill: {sid}\n{content}")
        return "\n".join(parts)
```

Builder phase 的 system prompt 应包含当前任务相关的 SKILL.md 内容。

**验收**: 指定 skill_id 列表后，能正确拼接为可注入 system prompt 的字符串。

---

### 步骤 3: 编写单元测试

| 文件 | 覆盖 | 测试数 |
|------|------|--------|
| `tests/memory/test_skills.py` | SKILL.md 加载、解析、内容获取 | 3 |
| `tests/core/test_skill_injection.py` | skill 注入正确性 | 1 |

**具体测试**：

```
test_skills.py:
  - test_load_all_skills: 能扫描加载所有 SKILL.md，数量正确
  - test_get_skill_content: 获取指定技能内容，返回非空字符串
  - test_skill_from_markdown: 从 SKILL.md 解析，frontmatter 和内容正确分离

test_skill_injection.py:
  - test_inject_skills: 指定 skill_id 列表后，正确拼接为可注入 prompt 的字符串
```

---

## 3. 文件清单

| 文件 | 动作 |
|------|------|
| `src/sloth_agent/memory/skills.py` | **重写** — SKILL.md 加载机制 |
| `src/sloth_agent/core/context_window.py` | **修改** — skill 注入方法 |
| `tests/memory/test_skills.py` | **新建** |
| `tests/core/test_skill_injection.py` | **新建** |

---

## 4. 与现有代码的关系

| 现有文件 | 动作 | 原因 |
|----------|------|------|
| `src/memory/skills.py` | **重写** | 现有格式与 Claude Code SKILL.md 不统一 |
| `src/memory/skill_router.py` | **保留不动** | v1.1 实现 |
| `src/memory/skill_validator.py` | **保留不动** | v1.0 只需基础加载，不需要验证器 |

---

## 5. 验收标准

- [ ] `Skill.from_markdown()` 正确解析 frontmatter 和正文
- [ ] `SkillManager.load_all_skills()` 能扫描 `skills/` 下所有 SKILL.md
- [ ] `SkillManager.get_skill_content(skill_id)` 能获取指定技能的完整内容
- [ ] `ContextWindowManager.inject_skills()` 正确拼接为可注入 prompt 的字符串
- [ ] 所有测试通过（共 4 tests）

---

*Plan 版本: v1.0.0 | 创建: 2026-04-17*
