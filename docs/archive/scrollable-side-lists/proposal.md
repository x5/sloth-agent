# Proposal: Scrollable Side Lists

> 日期: 2026-05-02
> 关联模块: docs/specs/desktop/spec.md

## 背景

桌面应用左侧 Inspiration 列表在窗口高度缩小时，没有出现纵向滚动，而是把每个 item 沿纵向压缩，最终发生内容重叠。由于 Agents 列表和 Settings 列表沿用了相同的列式布局与卡片视觉模式，它们也存在同类风险。

## 问题

当前实现里，列表容器虽然配置了 `overflow-y: auto`，但滚动链路中的 flex 子项仍允许沿主轴收缩，导致空间不足时优先压扁卡片，而不是触发滚动。

## 解决方案

统一三类列表的布局约束：

- 列容器和滚动容器都显式允许高度收缩：`min-height: 0`
- 列表 item / provider card 显式禁止沿主轴收缩：`flex: 0 0 auto`
- Inspiration / Agents / Settings 共享同一套滚动容器行为，保持代码和 UI 一致

## 不改动

- 不调整卡片视觉风格、间距、配色
- 不改动数据流、store、交互逻辑
- 不新增复杂的 JS 尺寸计算，保持纯 CSS 修复
