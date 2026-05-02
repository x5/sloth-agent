# Proposal: Fix Brainstorm Interrupt Behavior

> 日期: 2026-05-02

## 为什么改

上一轮 UI 调整把 interrupt 的判断条件错误绑定到了 persistent connection 状态，导致 brainstorm mode 一建立连接就亮起；同时点击时走了 disconnect 语义，实际上结束了当前 brainstorm 的连接语义，而不是只打断当前正在回复的 agent。

## 改什么

- interrupt 仅在当前存在 active agent 输出时高亮并可点击
- interrupt 点击只打断当前 round / 当前 agent 输出，不结束 brainstorm mode
- 为 persistent brainstorm 增加 round-level interrupt 能力

## 不改什么

- 不改 brainstorm 闪电按钮的 start / end mode 语义
- 不改 divider 持久化逻辑
- 不改消息时间线展示