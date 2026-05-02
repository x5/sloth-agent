# Delta: Scrollable Side Lists

> 日期: 2026-05-02
> 关联模块: docs/specs/desktop/spec.md

## ADDED Requirements

- 侧栏列表滚动一致性
  - Inspiration 列表、Agents 列表、Settings 列表在窗口高度不足时，必须保持 item 高度稳定并显示纵向滚动，而不是压缩卡片内容。
  - 共享滚动列表容器必须满足：
    - 外层列容器可收缩：`min-height: 0`
    - 滚动容器可收缩且纵向滚动：`min-height: 0` + `overflow-y: auto`
    - 列表项不可沿主轴收缩：`flex: 0 0 auto`

## MODIFIED Requirements

- 桌面应用列表列行为
  - `ProjectList`、`AgentPoolList`、`SettingsNav`、`ProviderList` 视为同一类侧栏滚动列表，需复用一致的纵向滚动与 item 稳定性约束。
