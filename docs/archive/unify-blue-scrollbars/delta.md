# Delta: Unify Blue Scrollbars

> 日期: 2026-05-02
> 关联模块: docs/specs/desktop/spec.md

## ADDED Requirements

- 桌面应用主要滚动容器必须统一使用与聊天消息区一致的蓝色细滚动条样式。
- 统一样式要求：
  - `scrollbar-width: thin`
  - `scrollbar-color: rgba(20, 160, 200, 0.3) transparent`
  - WebKit thumb 默认 `rgba(20, 160, 200, 0.3)`，hover 为 `rgba(20, 160, 200, 0.5)`

## MODIFIED Requirements

- Inspiration / Agents / Settings 列表的滚动行为不仅要一致，滚动条视觉也要与 chat message 窗口保持一致。
