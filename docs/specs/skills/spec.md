# 技能管理

> 归档参考: archive/initial-specs/20260416-06-skill-management-spec.md
> 最后更新: 2026-05-01

## 概述

技能系统采用 SKILL.md 格式（兼容 Claude Code），运行时注入到 LLM system prompt 中。支持 3 级自动匹配。

## 已实现

### 技能注册与注入 (`src/sloth_agent/memory/`)

- `skill_registry.py` — 从 `skills/` 目录加载所有 SKILL.md
- `skill_router.py` — 3 级匹配（精确/模糊/默认）
- `skill_injector.py` — 运行时将匹配的技能注入 prompt
- `skill_validator.py` — 验证 SKILL.md 格式

### 技能目录 (`skills/builtin/`)

- 40+ 内置 SKILL.md 定义
- 兼容 Claude Code 格式
- 覆盖 brainstorm、plan、review、debug、test 等场景

### 批量技能复用

参考 gstack (23 skills) + Superpowers (14 skills)，已整合为统一技能池。

## 待实现

- 技能自动进化（根据使用频率和成功率自动调整）
- 用户自定义技能的热加载

## 关键接口

- `SkillRegistry.load_from_directory(path) → SkillRegistry`
- `SkillRouter.match(task_context) → list[Skill]`
- `SkillInjector.inject(skills, prompt) → str`
