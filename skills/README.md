# Skills

Sloth Agent 内建 37 个技能，支持用户自定义和自动进化。

## 目录结构

```
skills/
├── superpowers/         # 14 个内建技能（auto+manual 触发）
├── gstack/              # 23 个内建技能（manual 触发）
├── user/                # 用户自定义技能
└── evolved/             # 自动进化生成的全新技能
```

## 触发方式

- **auto+manual** — Superpowers 全部 14 个技能，支持自动匹配和 `/skill <name>` 手动调用
- **manual** — gstack 全部 23 个技能，仅支持 `/skill <name>` 手动调用

## 技能进化

内建技能（Superpowers / gstack）的自我进化直接原地修改对应 SKILL.md 文件，版本号递增。
37 个预定义之外的全新技能保存到 `evolved/` 目录。
