# Delta: Reply Thread 引用预览 UI

> 关联模块: docs/specs/brainstorm/spec.md
> 日期: 2026-05-02

## MODIFIED Requirements

- **彩色线程呈现方式**（原：消息左侧外层 3px 彩色竖线；改：气泡内引用预览块）

  原内容：
  > 有 `parent_message_id` 的消息显示 3px 左侧竖线（仅 brainstorm 模式）

  修改后：
  > 有 `parent_message_id` 的消息，在气泡内顶部显示引用预览块（`.chat-message__quote`）：
  > - 引用块左侧显示 3px 线程颜色竖线（`borderLeftColor: threadAccent`）
  > - 上方一行显示被引用消息的发言人名（`chat-message__quote-author`，accent 色）
  > - 下方显示被引用内容前 80 字（`chat-message__quote-text`，超出截断加 `…`）
  > - 不再在消息外层 div 添加 `borderLeft` inline style

## ADDED Requirements

- **`.chat-message__quote` CSS 规则**
  - `border-left: 3px solid var(--color-accent)`（可被 inline `borderLeftColor` 覆盖为线程色）
  - `background: var(--color-accent-bg-light)`
  - 内含 `.chat-message__quote-author`（11px bold accent 色）和 `.chat-message__quote-text`（12px secondary，`-webkit-line-clamp: 2`）

## REMOVED Requirements

- 消息外层 div 的 `style={threadLine ? { borderLeft: ... } : undefined}` 注入
- `threadLine` 变量（已改名为 `threadAccent`，语义更准确）
