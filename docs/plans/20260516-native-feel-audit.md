# Sloth Agent 桌面版 — native-feel 审计与改进计划

> 来源: native-feel-skill (`yetone/native-feel-skill`)，Raycast 2.0 架构实践
> 日期: 2026-05-16
> 状态: DRAFT

---

## 背景

用 native-feel-skill 的决策树、八大原则、WebView 生存指南、IPC 契约设计、原生交互惯例五份参考文件，对 Sloth Agent 当前桌面架构做了系统性审计。

---

## 决策树结论：Sloth 严格来说"不该用这套架构"

| 问题 | Sloth 现状 | 判定 |
|------|-----------|------|
| Q1: 几个 OS？ | 当前只发 Windows（MVP），macOS/Linux 在 Phase 2 | **不使用此架构** |
| Q2: 原生感是硬需求？ | 目标用户是 PM，核心诉求是功能可用，不是"跟原生 App 一样" | **不使用此架构** |
| Q3: 插件生态？ | 没有 | 可跳过 Layer 3 |
| Q4: 冷启动预算？ | 无硬约束 | 通过 |
| Q5: 内存预算？ | 宽松（AI App） | 通过 |
| Q6: 团队经验？ | React/TS 强，无原生开发经验 | 谨慎推进 |
| Q7: 开发周期？ | 12+ 月到 v1 | 通过 |

按决策树，Sloth 当前满足 2 个"Don't use this architecture"条件。但 **skill 中的具体知识（WebView 坑、IPC 设计、CSS 惯例）在 Tauri 栈内仍然直接可用**，不需要重构成四层架构也能获得大部分收益。

---

## 八大原则对照

### T1 — 把接缝画在渲染面上 ✅/⚠️

> 渲染面之下必须原生；渲染面之上应该共享。

Sloth 将渲染面之下的 native shell 完全交给了 Tauri。Tauri Rust 层只做 `invoke → reqwest → FastAPI` 的薄代理，没有做窗口管理、热键、材料、系统托盘。对 Sloth 的定位（PM 工具，不需要 Raycast 级原生感）来说 **可以接受**。如果未来需要系统托盘/全局热键/原生通知，Tauri plugin 大概率能满足。

### T2 — 一套 schema，多种语言 🔴 高优先级

> 手写跨语言序列化是禁止的。一端声明，多端生成。

**Sloth 当前最大架构债务。** 现状：

```
前端 TypeScript    → 手写类型（Zustand store 接口）
Tauri Rust 命令    → 手写 serde struct（invoke 参数/返回值）
FastAPI Pydantic   → 手写 model（API 请求/响应）
```

三处独立维护，零编译时一致性保证。迭代中已出现重复实现问题（Iter-4 LLM Provider 在 backend 重写了 httpx 调用）。

**改进方案（见下方 tasks）：** 建立 `schema/` 单一源文件 + codegen。

### T3 — 接纳平台，不要与平台竞争 ⚠️ 可改进

> 平台的模糊比你快。平台的滚动条比你正确。平台的暗色模式比你正确。

Sloth 用 Tauri WebView，窗口层面没有大问题。但在 CSS 层面需要按 `06-native-conventions.md` 的 70+ 审计项检查：
- `cursor: pointer` 在列表行上？
- 文本默认可选？
- 硬编码品牌色而非跟随系统 accent color？
- 用 JS smooth-scroll 替代原生滚动？

这些是只改 CSS 就能提升"不像网页"感觉的廉价修复。

### T4 — 性能是感知的属性 ⚠️ 可改进

> 先定义感知目标，再测量。不要用 VM size 替代用户体验。

Sloth 的性能目标全是后端指标（"简单原型 < 5 分钟"），零 UI 感知目标：
- 按键到窗口可见？未定义
- 输入到结果更新？未定义
- 视图切换是否闪屏？未定义

### T5 — 短迭代循环就是产品 ✅

> React HMR 200ms vs Xcode 重建 30s。150 倍差距决定 UI 能否打磨完。

Sloth 的 React + Vite + HMR 是正确配置。需警惕：如果未来把更多逻辑迁入 Tauri Rust 层，每次 `cargo tauri dev` 重建会破坏这个循环。

### T6 — 有意识地跨越边界 🔴 高优先级

> 每次 IPC 调用都是一个设计决策。追踪每次调用的频率和负载。

当前边界跨越链：

```
React ──invoke──> Tauri Rust ──reqwest──> FastAPI ──SQLAlchemy──> SQLite
```

前端一次点击触发 3 个进程边界往返，无批处理，无 tracing。是 `04-ipc-contract.md` 描述的典型反模式。

### T7 — 身份是肌肉记忆

不适用（不是对现有 App 的重写）。

### T8 — 分离基准成本和边际成本 ⚠️

> 基准成本来自平台，不可削减。边际成本来自你的代码，这才是优化目标。

Sloth 没有做这个分类。当前内存占用：
- **基准（不可削减）：** Tauri WebView ~50MB、Python 解释器 ~30MB
- **边际（可优化）：** React bundle 大小、FastAPI connection pool、SQLite cache、Python import 模块数

---

## WebView 生存指南 — Sloth 风险矩阵

| 问题 | 风险 | 优先级 |
|------|------|--------|
| A.2 启动白屏闪烁 — `NSWindow.orderFront()` 先于 WebView 首帧 | **高** — Tauri window 创建→WebView 加载→React 渲染之间有可见白屏 | P1 |
| A.8 视图切换闪烁 — unmount-before-mount / CSS 路由分包 / View Transitions API | **高** — 4 列布局切换、Brainstorm/Chat 模式切换 | P1 |
| B.1 WebView2 初始化白屏 — `CoreWebView2` async init 导致窗口先空白 | **高** — Windows 专属 | P1 |
| B.5 IME 组合输入 — 中文输入法 composition 事件问题 | **中** — 目标用户是国内 PM | P2 |
| C.1 `cursor: pointer` 在列表行 | **中** — 需检查前端代码 | P2 |
| C.2 文本默认可选 | **中** — 需检查 | P2 |
| A.1 隐藏窗口限流 | 低 — 无 prewarm 需求 | P3 |
| A.5 半透明/毛玻璃/Liquid Glass | 低 — 无透明窗口需求 | P3 |

---

## IPC 契约 — 当前最值得投入的改进

现状 vs 目标：

```
# 现状（三处独立维护，零编译时保证）
frontend/src/   → 手写 interface（store 里）
src-tauri/src/  → 手写 serde struct（invoke 参数）
backend/app/    → 手写 Pydantic model（API 请求/响应）

# 目标（单一源文件 + codegen）
frontend/src/shared/schema/   ← 单一 .ts 源文件
  ├── requests.ts              ← 所有请求/响应类型
  └── events.ts                ← SSE/WebSocket 事件类型

backend/app/shared/schema/
  ├── requests.py              ← datamodel-codegen 从 .ts 生成
  └── events.py

src-tauri/src/
  └── schema.rs                ← 手工维护，以 .ts 为源头
```

投入 1-2 天，收益是永远不会出现"前端发了字段名后端不认识"的运行时 bug。

---

## 改进任务

### P0 — 阻塞性（本周做）

- [ ] **建立统一 IPC schema 源文件 + codegen**
  - 创建 `frontend/src/shared/schema/` 目录，定义所有请求/响应和事件类型
  - 配置 `datamodel-codegen` 从 TS 生成 Pydantic model
  - 在 Tauri Rust 侧手工对齐 serde struct（以 .ts 为源头）
  - 投入: 1-2 天

- [ ] **IPC 调用加 tracing**
  - 开发环境为每个 IPC 调用记录 `{requestId, kind, durationMs}`
  - 发现慢 handler 和不必要的连锁跨越
  - 投入: 半天

### P1 — 高优先级（下周做）

- [ ] **修复 WebView 启动白屏**
  - Tauri 侧：设置窗口背景色为非白色 `DefaultBackgroundColor`
  - 或在 WebView `NavigationCompleted` 之前不显示窗口
  - 投入: 半天

- [ ] **消除视图切换闪屏**
  - 检查 A.8 三条根因（unmount-before-mount / CSS 分包 / View Transitions）
  - 确保旧视图在新视图首帧前不卸载
  - 禁用页面切换动画（原生 App 用 cut，不用 fade）
  - 投入: 1 天

### P2 — 中优先级（本月做）

- [ ] **按 06-native-conventions.md 审计前端 CSS**
  - 检查 `cursor: pointer`、`user-select`、scrollbar、accent color、字体
  - 每项只改 CSS，不动逻辑
  - 投入: 1 天

- [ ] **测试中文 IME 输入**
  - 在 Pinyin 下测试所有输入框的 composition 事件
  - 检查候选窗口位置是否在光标处
  - 投入: 半天

- [ ] **定义 UI 感知性能目标**
  - 窗口冷启动到可交互: < ? ms
  - 视图切换: < ? ms（无闪屏）
  - 输入到流式首字渲染: < ? ms
  - 投入: 1 小时

### P3 — 低优先级（本季度做）

- [ ] **区分基准/边际内存成本**
  - 记录到架构文档：哪些内存是 Tauri/Python/WebView 的基线，哪些是 Sloth 代码产生的
  - 避免在基准成本上浪费优化时间
  - 投入: 1 小时

- [ ] **文档化架构权衡**
  - 将决策树结论（为何选 Tauri 而不选四层架构）写入架构 spec
  - 记录"不做什么"和"做了的代价"
  - 投入: 1 小时

---

## 资源投入汇总

| 优先级 | 任务数 | 总投入 |
|--------|--------|--------|
| P0 | 2 | 1.5-2.5 天 |
| P1 | 2 | 1.5 天 |
| P2 | 3 | 1.5 天 |
| P3 | 2 | 2 小时 |
| **合计** | **9** | **约 1 周** |

---

## 不做的事

- **不重构成四层架构**（native shell + WebView + Node + Rust）— Sloth 不需要 Raycast 级的原生感，Tauri 够用
- **不引入 UniFFI** — Sloth 没有 Rust ↔ Swift/C# 的绑定需求，太重
- **不做原生壳重写** — 当前 Windows-only，没有跨平台壳的收益
- **不做 ProMotion 120Hz 适配** — 虽然 skill 提到了，但目标用户机器大概率 60Hz

---

*审计基于 [native-feel-skill](https://github.com/yetone/native-feel-skill)，MIT license*
