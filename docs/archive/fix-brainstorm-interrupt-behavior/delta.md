# Delta: Fix Brainstorm Interrupt Behavior

> 日期: 2026-05-02

## MODIFIED Requirements

### REQ-DESKTOP-BRAINSTORM-INTERRUPT-SEMANTICS

在 brainstorm mode 下，interrupt button 只能表示“打断当前正在进行的 agent 回复”，不能表示结束 brainstorm mode。

#### 验收标准

- 只有在当前存在 active agent 正在输出时，interrupt button 才呈紫色可点击态
- 仅建立 persistent brainstorm 连接但尚无 agent 开始输出时，interrupt button 必须保持灰色不可点击态
- 点击 interrupt 后，当前 round 停止，brainstorm mode 仍保持激活
- 点击 interrupt 后，闪电按钮仍保持 brainstorm mode 的独立 start / end 语义
