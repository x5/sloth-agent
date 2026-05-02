# Tasks: Reply Thread 引用预览 UI

> 日期: 2026-05-02

## 实现任务

- [x] `ChatArea.tsx` — 移除外层 `borderLeft` style，改为气泡内渲染 `parentMsg` 引用块
- [x] `ChatArea.tsx` — 将 `threadLine` 变量改名为 `threadAccent`，查找 `parentMsg` by `parent_message_id`
- [x] `App.css` — 新增 `.chat-message__quote`、`.chat-message__quote-author`、`.chat-message__quote-text` 样式规则

## 验证

- [x] 前端测试: 36 passed (15 test files)
- [ ] 合并 delta 到 `docs/specs/brainstorm/spec.md`
- [ ] 归档变更目录到 `docs/archive/reply-thread-quote-ui/`
