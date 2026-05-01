# 实现任务

- [x] ChatArea.tsx：添加 queueRef + queueLen 状态
- [x] ChatArea.tsx：实现 processQueue 函数（批量合并）
- [x] ChatArea.tsx：改造 handleSend — 系统忙时入队，空闲时立即发送
- [x] ChatArea.tsx：chat 模式回复完成后调用 processQueue
- [x] ChatArea.tsx：brainstorm 模式回复完成后调用 processQueue
- [x] ChatArea.tsx：输入框上方显示队列提示
- [x] App.css：添加 .chatarea__queue-badge 样式
- [x] 验证：chat 模式发送 → 等待中再发 → 自动排队处理
- [x] 验证：brainstorm 模式同上
- [x] 合并 delta 到 specs
- [ ] 归档
