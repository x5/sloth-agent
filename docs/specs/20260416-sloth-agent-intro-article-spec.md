# Sloth Agent 介绍文章 HTML 规格

> 日期: 20260416
> 状态: 已起草
> 参考风格: OpenAI《The next evolution of the Agents SDK》的写作思路与节奏，不复用其原文、版式或专有表达

---

## 1. 目标

基于 [docs/specs/00000000-architecture-overview.md](c:/Users/TUF/Workspace/agent-evolve/docs/specs/00000000-architecture-overview.md) 输出一篇面对开发者与技术决策者的 Sloth Agent 介绍文章，并交付为可直接打开的精美静态 HTML。

文章目标不是逐段复述架构文档，而是用更适合传播的方式解释：
- Sloth Agent 为什么存在
- 它解决了什么现实问题
- 它的运行时内核、工具、技能、记忆、安全机制如何协同
- v1.0 与 v2.0 的边界和路线图是什么

---

## 2. 读者与传播场景

### 2.1 目标读者

- 希望把 AI 编码从“对话助手”提升到“可执行系统”的开发者
- 对 agent runtime、tool use、memory、安全、生产可用性有要求的技术团队
- 关注中国模型生态、多模型路由、本地可控性的技术负责人

### 2.2 使用场景

- 项目官网或内部门户中的产品介绍页
- 对外展示 Sloth Agent 设计理念的长文页面
- 给潜在贡献者、测试者、合作者的架构说明入口

---

## 3. 内容要求

### 3.1 文章结构

文章需采用“问题提出 -> 核心能力 -> 系统设计 -> 安全与控制 -> 路线图”的推进方式，参考 OpenAI 文章的叙事节奏，但内容必须完全原创。

建议结构：

1. Hero 区
   - 标题、副标题、发布时间、定位标签
   - 一段短摘要，说明 Sloth Agent 是什么

2. 为什么现在需要 Sloth Agent
   - 解释现有 AI coding workflow 的典型断层：能生成代码，但难以稳定执行、审查、恢复、部署
   - 引出 Sloth Agent 的产品定位

3. 一个更可靠的 agent execution harness
   - 强调单一 `Runner` 内核
   - 说明 Builder / Reviewer / Deployer 串行流水线与自动门控
   - 用简洁图示或代码样式块解释运行模式

4. 让 agent 真正可落地的基础设施
   - Tools、Skills、Memory、Checkpoints、Context Window Manager、HallucinationGuard
   - 说明这些能力不是零散功能，而是同一个执行系统的一部分

5. 为生产环境而设计的控制面
   - 安全默认、文件系统即真相、可审计、可恢复、多模型路由、成本控制
   - 突出“可控性”而不只是“能力更强”

6. 路线图
   - 说明 v1.0 的范围边界
   - 说明 v1.1 / v2.0 的演进方向

7. 收尾
   - 用一段简洁结语强调 Sloth Agent 的独特定位

### 3.2 语气与表达

- 中文写作
- 面向开发者，但不写成纯规格说明
- 节奏应克制、清晰、偏产品发布文风
- 允许适量技术术语，但必须能让非作者读者快速抓住主线
- 避免营销空话，尽量把论点落到架构事实

### 3.3 必须体现的事实

- v1.0 核心是 Plan -> Builder -> Reviewer -> Deployer
- `Runner` 是唯一运行时内核，`Product Orchestrator` 不是第二套真相源
- Sloth Agent 是工具优先、技能注入、文件系统状态持久化的系统
- 具备自动门控、自我纠错、安全默认、多模型路由、成本控制思路
- v2.0 才进入 8+1 Agent、事件系统、知识库、daemon 等完整扩展

---

## 4. 视觉与交互要求

### 4.1 交付形式

- 单文件 HTML，可直接在浏览器打开
- 优先内联 CSS；可包含少量原生 JS 做轻交互，但不得依赖打包工具

### 4.2 视觉方向

- 不是照搬 OpenAI 官网外观，而是借鉴其“发布级长文页面”的克制感、留白与层次
- 整体风格应偏 editorial / product announcement
- 需要比普通 Markdown 页面更精致：明确视觉层级、版式节奏、重点数据卡片、代码/架构块样式

### 4.3 设计要求

- 桌面端优先，同时兼容移动端
- 至少包含：Hero、摘要、分节长文、能力卡片、路线图、结尾 CTA/总结区
- 使用有个性的中英文字体搭配，避免通用默认风格
- 背景、边框、阴影、渐变、分隔线需要形成完整视觉语言
- 页面不能只由纯文字和普通卡片构成，至少应包含一组原创非文字视觉元素，例如：流程图、结构图、线性图标、抽象插画、系统节点图中的一种或多种
- 非文字元素必须服务于内容理解，不能只是装饰噪音；优先用于 Hero 区、执行内核区、能力卡片区

---

## 5. 文件与产物

- HTML 输出文件：`docs/articles/20260416-introducing-sloth-agent.html`
- 对应 implementation plan：`docs/plans/20260416-sloth-agent-intro-article-implementation-plan.md`
- `TODO.md` 需新增与该 plan 一一对应的高优先级任务

---

## 6. 验收标准

- HTML 可直接打开且排版完整
- 内容主线与 canonical architecture 一致，不混淆 v1.0 和 v2.0 边界
- 明显能看出参考了“产品发布长文”的写法节奏，但没有复用原文或近似改写
- 页面观感达到“可展示”的水平，而不是简单导出的文档页
