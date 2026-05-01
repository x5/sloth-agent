# 变更提案: 消息队列机制

> 日期: 2026-05-02
> 影响模块: specs/chat/spec.md, specs/brainstorm/spec.md

## 动机

当前 chat 和 brainstorm 模式下，系统响应期间用户无法发送新消息。发送按钮被禁用，输入框虽然可编辑但无法触发发送。这导致用户体验断裂——用户必须等待每条回复完成后才能发送下一条。

用户期望：随时可以发送消息。系统忙时消息入队暂存，响应完成后自动处理队列中的下一条。

## 范围

**改什么：**
- ChatArea.tsx：引入消息队列（ref + state），改造 handleSend 逻辑
- App.css：队列提示样式
- chat/spec.md：新增消息队列需求条款
- brainstorm/spec.md：新增消息队列需求条款

**不改什么：**
- 后端 API 无变化
- BrainstormEngine 无变化
- Zustand store 无变化（队列是 ChatArea 本地状态）
