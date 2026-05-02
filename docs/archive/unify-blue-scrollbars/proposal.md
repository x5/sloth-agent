# Proposal: Unify Blue Scrollbars

> 日期: 2026-05-02
> 关联模块: docs/specs/desktop/spec.md

## 背景

当前桌面应用内已经存在 chat message 窗口的蓝色滚动条样式，但 Inspiration / Agents / Settings 等其他滚动区域仍使用默认或灰色滚动条，视觉上不统一。

## 解决方案

把 chat message 窗口的蓝色滚动条提炼为共享样式，并应用到主要滚动容器：
- 聊天消息区
- Inspiration / Agents 列表
- Settings 列表与 Provider 列表
- 详情滚动区与主要下拉列表

## 不改动

- 不修改滚动条尺寸与交互逻辑
- 不引入 JS
- 不改动列表布局，仅统一视觉样式
