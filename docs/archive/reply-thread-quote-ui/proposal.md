# Proposal: Reply Thread 引用预览 UI

> 日期: 2026-05-02
> 关联模块: docs/specs/brainstorm/spec.md

## 背景

Iter-6 实现了 Reply Thread 功能：有 `parent_message_id` 的消息会在左侧显示一条彩色竖线，颜色由根消息 ID 经 FNV-1a 哈希得出，代表"同一回复链"。

## 问题

彩色竖线对用户完全不透明：
- 用户不知道竖线代表什么含义
- 无法从竖线知晓"这条消息在回复谁的哪句话"
- 这种呈现方式只有阅读过代码的人才能猜到语义

## 解决方案

参考 WhatsApp / Telegram / Discord 的引用回复模式：

**移除** 消息外层彩色竖线  
**改为** 气泡内顶部显示引用预览块，包含：
- 被引用人名（accent 色）
- 被引用内容前 80 字
- 引用块左侧保留线程颜色竖线（accent 色，视觉上仍标识回复链）

## 影响范围

- `frontend/src/components/ChatArea.tsx` — 渲染逻辑
- `frontend/src/App.css` — 新增 `.chat-message__quote` 相关样式
- `docs/specs/brainstorm/spec.md` — 更新彩色线程描述
