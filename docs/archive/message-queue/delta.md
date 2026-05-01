# Delta: 消息队列机制

> 关联模块: specs/chat/spec.md, specs/brainstorm/spec.md

## ADDED Requirements

### REQ-MQ-01: 消息队列

用户在系统响应期间发送的消息自动入队。系统响应完成后自动取出队首消息并发送。队列按 FIFO 顺序处理。

### REQ-MQ-02: 队列状态反馈

输入框上方显示队列长度提示（如 "2 messages queued"）。队列为空时不显示。

### REQ-MQ-03: 随时发送

输入框在系统响应期间始终可编辑、可发送。发送时系统忙则入队，系统空闲则立即发送。

### REQ-MQ-04: 统一队列逻辑

Chat 模式和 Brainstorm 模式共用同一套队列机制。两种模式下发送和处理逻辑一致。

## MODIFIED Requirements

无。

## REMOVED Requirements

无。
