# Delta: Brainstorm Interrupt Icon

> 日期: 2026-05-02

## MODIFIED Requirements

### REQ-DESKTOP-BRAINSTORM-INTERRUPT-UI

在 brainstorm mode 下，输入区必须提供一个与 brainstorm 闪电按钮并排的 interrupt icon button，用于中断当前讨论轮次。

#### 验收标准

- interrupt button 位于输入工具组内，紧邻 brainstorm 闪电按钮
- 按钮使用“捂嘴”语义 icon，而不是红色文字按钮
- 当当前轮次可中断时，按钮呈 brainstorm 紫色可点击态
- 当 interrupt 已触发或当前无可中断轮次时，按钮仍然可见，但必须呈灰色不可点击态
