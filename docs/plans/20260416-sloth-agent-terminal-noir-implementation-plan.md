# Terminal Noir Article Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Completely redesign the Sloth Agent introduction article HTML from warm editorial style to dark "Terminal Noir" aesthetic with amber accents, SVG icons, flow diagrams, and refined layout — preserving all existing Chinese content.

**Architecture:** Single self-contained HTML file. Full CSS rewrite (inline), new SVG icons for all cards, updated SVG hero illustration, terminal-style code blocks, dark color system. No JS changes beyond existing progress bar.

**Tech Stack:** HTML5, CSS3 (inline), inline SVG, vanilla JS (existing progress bar only), Google Fonts (Space Grotesk, Noto Sans SC, JetBrains Mono)

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `docs/articles/20260416-introducing-sloth-agent.html` | Modify | Entire visual redesign — CSS variables, typography, all sections, SVG icons/diagrams |

Only one file is involved. Each task touches a different logical section of the HTML to keep changes self-contained and reviewable.

---

## Priority Rules

All tasks are P0 — the page needs every section redesigned to ship coherently. Execute in order so each section builds on the previous CSS system.

### Task 1: Dark CSS Variable System + Base Styles

**Files:**
- Modify: `docs/articles/20260416-introducing-sloth-agent.html` (lines 8-787, the `<style>` block)

- [ ] **Step 1: Replace the CSS variable system**

Replace the entire `:root` block (lines 9-29) with the Terminal Noir variables:

```css
:root {
  --bg: #111111;
  --bg-soft: #1a1a1a;
  --paper: rgba(26, 26, 26, 0.85);
  --paper-solid: #1a1a1a;
  --ink: #ffffff;
  --ink-soft: #e8e0d8;
  --muted: #8a8078;
  --line: rgba(255, 255, 255, 0.08);
  --line-strong: rgba(245, 158, 11, 0.3);
  --accent: #F59E0B;
  --accent-2: #F97316;
  --accent-soft: rgba(245, 158, 11, 0.12);
  --success: #22c55e;
  --danger: #ef4444;
  --shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
  --radius-xl: 32px;
  --radius-lg: 24px;
  --radius-md: 18px;
  --radius-sm: 12px;
  --content: min(1120px, calc(100vw - 32px));
  --font-display: "Space Grotesk", "Noto Sans SC", sans-serif;
  --font-body: "Noto Sans SC", "Segoe UI Variable", sans-serif;
  --font-mono: "JetBrains Mono", "Cascadia Code", Consolas, monospace;
}
```

- [ ] **Step 2: Replace the `body` and global background styles**

Replace the `body` rule (lines 39-51) and `body::before` (lines 53-64) with:

```css
body {
  margin: 0;
  color: var(--ink-soft);
  background:
    radial-gradient(circle at 30% 0%, rgba(245, 158, 11, 0.06), transparent 40%),
    radial-gradient(circle at 80% 10%, rgba(249, 115, 22, 0.04), transparent 30%),
    linear-gradient(180deg, #161616 0%, #111111 8%, #111111 100%);
  font-family: var(--font-body);
  line-height: 1.6;
  letter-spacing: 0.01em;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}

body::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.018) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.018) 1px, transparent 1px);
  background-size: 32px 32px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.6), transparent 90%);
  opacity: 0.5;
}
```

- [ ] **Step 3: Update the Google Fonts import**

Add a `<link>` tag at the very top inside `<head>` (right after `<meta name="viewport" ... />`):

```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&family=Noto+Sans+SC:wght@300;400;500;700&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet" />
```

- [ ] **Step 4: Update the progress bar**

Replace the `.progress` rule gradient to use amber:

```css
.progress {
  position: fixed;
  inset: 0 0 auto;
  height: 3px;
  background: linear-gradient(90deg, var(--accent), var(--accent-2));
  transform-origin: left center;
  transform: scaleX(0);
  z-index: 50;
}
```

- [ ] **Step 5: Update typography, heading, and link styles**

Replace `h1, h2, h3` rules and add link defaults:

```css
h1, h2, h3 {
  margin: 0;
  font-family: var(--font-display);
  font-weight: 700;
  line-height: 1.08;
  letter-spacing: -0.02em;
  color: var(--ink);
}

a {
  color: var(--accent);
  text-decoration: none;
}

a:hover {
  color: var(--accent-2);
}

pre {
  margin: 0;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  padding: 22px;
  border-radius: var(--radius-lg);
  background: #0a0a0a;
  color: #e8e0d8;
  border: 1px solid var(--line);
  font: 500 13px/1.65 var(--font-mono);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
}
```

- [ ] **Step 6: Update all card, panel, and component styles**

Replace `.hero-card, .panel, .quote, .roadmap, .footer-card` rules:

```css
.hero-card, .panel, .quote, .roadmap, .footer-card {
  backdrop-filter: blur(18px);
  background: var(--paper);
  border: 1px solid var(--line);
  box-shadow: var(--shadow);
}

.hero-card {
  padding: 34px;
  border-radius: var(--radius-xl);
  position: relative;
  overflow: hidden;
  align-self: start;
  height: fit-content;
  min-height: 0;
}

.hero-card::after {
  content: "";
  position: absolute;
  inset: auto -80px -70px auto;
  width: 220px;
  height: 220px;
  background: radial-gradient(circle, rgba(245, 158, 11, 0.1), transparent 66%);
  pointer-events: none;
}
```

Replace `.card` styles:

```css
.card {
  padding: 22px;
  border-radius: var(--radius-lg);
  background: rgba(26, 26, 26, 0.7);
  border: 1px solid var(--line);
  min-height: 196px;
  transition: transform 180ms ease, border-color 180ms ease, background 180ms ease;
}

.card:hover {
  transform: translateY(-4px);
  border-color: var(--line-strong);
  background: rgba(30, 30, 30, 0.85);
}
```

Replace `.card-icon` styles:

```css
.card-icon {
  width: 40px;
  height: 40px;
  border-radius: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--accent-soft);
  border: 1px solid var(--line);
  flex: 0 0 auto;
}

.card-icon svg {
  width: 20px;
  height: 20px;
  stroke: var(--accent);
  stroke-width: 1.8;
  fill: none;
  stroke-linecap: round;
  stroke-linejoin: round;
}
```

Replace `.metric` styles:

```css
.metric {
  padding: 22px;
  border-radius: var(--radius-lg);
  background: linear-gradient(180deg, rgba(26, 26, 26, 0.9), rgba(20, 20, 20, 0.85));
  border: 1px solid var(--line);
  min-height: 144px;
  display: grid;
  align-content: start;
  gap: 8px;
  box-shadow: 0 14px 36px rgba(0, 0, 0, 0.3);
}

.metric.featured {
  grid-column: 1 / -1;
  min-height: 168px;
  padding: 24px;
  background:
    radial-gradient(circle at top right, rgba(245, 158, 11, 0.08), transparent 36%),
    linear-gradient(180deg, rgba(30, 30, 30, 0.95), rgba(22, 22, 22, 0.9));
}

.metric .label {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  color: var(--muted);
  margin-bottom: 2px;
}

.metric .value {
  font-family: var(--font-display);
  font-size: clamp(1.55rem, 2.4vw, 2.35rem);
  line-height: 1.05;
  letter-spacing: -0.03em;
  color: var(--accent);
}

.metric.featured .value {
  font-size: clamp(2.4rem, 4vw, 3.5rem);
}

.metric .desc {
  color: var(--muted);
  font-size: 0.95rem;
}
```

- [ ] **Step 7: Update the remaining section styles**

Replace `.panel.alt`:

```css
.panel.alt {
  background: linear-gradient(180deg, rgba(26, 26, 26, 0.92), rgba(20, 20, 20, 0.88));
}

.kicker {
  display: inline-block;
  margin-bottom: 16px;
  color: var(--accent);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.18em;
  font-weight: 700;
}
```

Replace `.panel-head` paragraph colors:

```css
.panel-head p, .aside-note {
  color: var(--muted);
  font-size: 1rem;
}
```

Replace `.flow-visual` styles (the 4-step flow section):

```css
.flow-visual {
  margin-top: 20px;
  padding: 24px 22px 20px;
  border-radius: var(--radius-xl);
  background:
    radial-gradient(circle at top right, rgba(245, 158, 11, 0.05), transparent 24%),
    linear-gradient(180deg, rgba(22, 22, 22, 0.8), rgba(18, 18, 18, 0.75));
  border: 1px solid var(--line);
  position: relative;
  overflow: hidden;
}

.flow-visual::before {
  content: "";
  position: absolute;
  left: 36px;
  right: 36px;
  top: 58px;
  height: 2px;
  background: linear-gradient(90deg, var(--accent), var(--accent-2), var(--accent));
  opacity: 0.7;
}

.flow-panel {
  min-height: 128px;
  padding: 16px;
  border-radius: 18px;
  background: rgba(20, 20, 20, 0.8);
  border: 1px solid var(--line);
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.2);
  display: grid;
  gap: 8px;
  align-content: start;
}

.flow-dot {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: 2px solid var(--line);
  background: var(--accent-soft);
  box-shadow: 0 0 0 6px rgba(26, 26, 26, 0.55);
}

.flow-step {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: var(--accent);
  font-weight: 700;
}

.flow-title {
  font-family: var(--font-display);
  font-size: 1.15rem;
  line-height: 1.1;
  color: var(--ink);
}

.flow-copy {
  color: var(--muted);
  font-size: 0.9rem;
  line-height: 1.45;
}
```

Replace `.inline-item`:

```css
.inline-item {
  padding: 18px 20px;
  border-left: 3px solid var(--accent);
  background: rgba(26, 26, 26, 0.5);
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
  color: var(--muted);
}
```

Replace `.roadmap-step`:

```css
.roadmap-step {
  padding: 22px;
  border-radius: var(--radius-lg);
  background: rgba(26, 26, 26, 0.6);
  border: 1px solid var(--line);
  display: grid;
  gap: 12px;
}

.roadmap-step .state {
  display: inline-block;
  width: fit-content;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  background: var(--accent-soft);
  color: var(--accent);
  border: 1px solid rgba(245, 158, 11, 0.2);
}
```

Replace `.footer-card` styles:

```css
.footer-card {
  border-radius: var(--radius-xl);
  padding: 34px;
  display: grid;
  grid-template-columns: 1fr;
  gap: 24px;
  align-items: stretch;
  margin-top: 4px;
  color: #f8efe6;
  background:
    radial-gradient(circle at top right, rgba(245, 158, 11, 0.08), transparent 26%),
    radial-gradient(circle at bottom left, rgba(249, 115, 22, 0.06), transparent 30%),
    linear-gradient(135deg, #0f0f0f 0%, #151515 52%, #1a1510 100%);
  border: 1px solid rgba(255, 255, 255, 0.06);
  box-shadow: 0 26px 80px rgba(0, 0, 0, 0.5);
}

.footer-card .kicker { color: var(--accent); }
```

Replace `.footer-badge`:

```css
.footer-badge {
  display: grid;
  gap: 14px;
  align-content: start;
  min-height: 100%;
  padding: 22px;
  border-radius: var(--radius-lg);
  border: 1px solid rgba(255, 255, 255, 0.08);
  background:
    linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02)),
    radial-gradient(circle at top right, rgba(245, 158, 11, 0.1), transparent 45%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.footer-badge-label {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  color: var(--accent);
}

.footer-badge-title {
  font-family: var(--font-display);
  font-size: 1.5rem;
  line-height: 1.15;
  color: #ffffff;
}

.footer-badge-copy {
  color: rgba(248, 239, 230, 0.6);
  font-size: 0.95rem;
  line-height: 1.55;
}
```

Replace `.footer-action` styles:

```css
.footer-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 46px;
  padding: 0 18px;
  border-radius: 999px;
  text-decoration: none;
  font-size: 0.95rem;
  font-weight: 700;
  transition: transform 180ms ease, background 180ms ease, border-color 180ms ease;
}

.footer-action:hover {
  transform: translateY(-2px);
}

.footer-action.primary {
  background: linear-gradient(135deg, var(--accent), var(--accent-2));
  color: #111;
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.footer-action.secondary {
  background: rgba(255, 255, 255, 0.03);
  color: var(--ink-soft);
  border: 1px solid var(--line);
}
```

Replace `.muted` and `.source-note`:

```css
.muted { color: var(--muted); }

.source-note {
  margin-top: 18px;
  font-size: 0.92rem;
  color: var(--muted);
}

.footer-card .muted,
.footer-card .source-note {
  color: rgba(248, 239, 230, 0.55);
}
```

- [ ] **Step 8: Update the `.hero-visual` SVG styling**

Replace `.hero-visual` to use dark gradient:

```css
.hero-visual {
  padding: 18px;
  border-radius: var(--radius-xl);
  background:
    radial-gradient(circle at top right, rgba(245, 158, 11, 0.1), transparent 34%),
    linear-gradient(180deg, rgba(26, 26, 26, 0.95), rgba(20, 20, 20, 0.9));
  border: 1px solid var(--line);
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.3);
  overflow: hidden;
}

.hero-visual svg {
  width: 100%;
  height: auto;
  display: block;
}

.hero-visual-copy {
  margin-top: 12px;
  color: var(--muted);
  font-size: 0.93rem;
}
```

- [ ] **Step 9: Verify media queries still reference correct classes**

Keep the existing `@media` rules (lines 726-786) unchanged — they already reference the right class names. Just verify they compile correctly after all the style changes.

### Task 2: Hero Section — Dark Theme + New SVG Diagram

**Files:**
- Modify: `docs/articles/20260416-introducing-sloth-agent.html` (lines 790-866, the `<body>` content through the hero section)

- [ ] **Step 1: Replace the topbar / nav**

Replace lines 792-795 with:

```html
<header class="topbar">
  <div class="brand">
    <span class="brand-mark"></span>
    <span style="font-family:var(--font-display); letter-spacing:0.12em;">SLOTH AGENT</span>
  </div>
  <div>Architecture Preview &bull; April 16, 2026 &bull; Product</div>
</header>
```

Update `.brand-mark` CSS to use amber dot:

```css
.brand-mark {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 0 4px rgba(245, 158, 11, 0.15);
}
```

- [ ] **Step 2: Replace the hero card content**

Keep the exact same Chinese text content. Update the eyebrow badge to dark:

```html
<article class="hero-card">
  <div class="eyebrow">Introducing a Product-Grade Agent System</div>
  <h1>Sloth Agent</h1>
  <p class="subtitle">
    一个面向中国开发者生态设计的 AI 开发执行系统。它的目标不是再做一个更会聊天的 coding assistant，
    而是把 <strong>Plan → 开发 → 审查 → 部署</strong> 变成一条可控、可恢复、可审计的执行闭环。
  </p>

  <div class="lede">
    <p>
      今天的大多数 AI 编码体验，在"生成一段代码"时已经足够惊艳；但一旦任务跨越文件、命令、测试、审查与部署，
      系统往往开始失去结构。Sloth Agent 的出发点很简单：<strong>不要把 agent 当作一次性回答器，而要把它当作持续执行的软件系统。</strong>
    </p>
    <p>
      这也是为什么 Sloth Agent 把运行时内核、工具调用、技能注入、状态持久化、安全默认和质量门控视为同一问题的不同侧面。
      真正可用的 agent，不只是"会做"，更要"做得稳、做得清楚、出了问题还能接着做"。
    </p>
  </div>
</article>
```

- [ ] **Step 3: Replace the `.eyebrow` CSS for dark theme**

```css
.eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border: 1px solid var(--line);
  border-radius: 999px;
  color: var(--muted);
  font-size: 12px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  margin-bottom: 22px;
  background: rgba(255, 255, 255, 0.03);
}
```

- [ ] **Step 4: Replace the hero SVG with a new Terminal Noir diagram**

Replace the entire `<svg>` block (lines 820-840) inside `.hero-visual` with a new 4-node system diagram with amber gradient strokes and dark fills:

```html
<svg viewBox="0 0 380 220" role="img" aria-label="Sloth Agent system illustration">
  <defs>
    <linearGradient id="heroStroke" x1="0" x2="1">
      <stop offset="0%" stop-color="#F59E0B" />
      <stop offset="50%" stop-color="#F97316" />
      <stop offset="100%" stop-color="#F59E0B" />
    </linearGradient>
    <filter id="glow">
      <feGaussianBlur stdDeviation="2" result="blur" />
      <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
    </filter>
  </defs>
  <rect x="18" y="28" width="344" height="164" rx="28" fill="rgba(20,20,20,0.7)" stroke="rgba(255,255,255,0.06)"/>
  <!-- Builder node -->
  <circle cx="92" cy="108" r="38" fill="rgba(245,158,11,0.08)" stroke="url(#heroStroke)" stroke-width="2.5" filter="url(#glow)"/>
  <text x="92" y="105" text-anchor="middle" font-family="Space Grotesk, sans-serif" font-size="11" font-weight="600" fill="#F59E0B">Builder</text>
  <text x="92" y="120" text-anchor="middle" font-family="Noto Sans SC, sans-serif" font-size="9" fill="#8a8078">编码</text>
  <!-- Reviewer node -->
  <circle cx="190" cy="68" r="26" fill="rgba(245,158,11,0.06)" stroke="url(#heroStroke)" stroke-width="2" filter="url(#glow)"/>
  <text x="190" y="65" text-anchor="middle" font-family="Space Grotesk, sans-serif" font-size="10" font-weight="600" fill="#F59E0B">Reviewer</text>
  <text x="190" y="78" text-anchor="middle" font-family="Noto Sans SC, sans-serif" font-size="8" fill="#8a8078">审查</text>
  <!-- Deployer node -->
  <circle cx="278" cy="110" r="32" fill="rgba(249,115,22,0.08)" stroke="url(#heroStroke)" stroke-width="2.2" filter="url(#glow)"/>
  <text x="278" y="107" text-anchor="middle" font-family="Space Grotesk, sans-serif" font-size="11" font-weight="600" fill="#F97316">Deployer</text>
  <text x="278" y="120" text-anchor="middle" font-family="Noto Sans SC, sans-serif" font-size="9" fill="#8a8078">部署</text>
  <!-- Runner node -->
  <rect x="148" y="136" width="86" height="40" rx="18" fill="rgba(26,26,26,0.85)" stroke="url(#heroStroke)" stroke-width="2"/>
  <text x="191" y="160" text-anchor="middle" font-family="Space Grotesk, sans-serif" font-size="10" font-weight="600" fill="#e8e0d8">Runner</text>
  <!-- Connection lines -->
  <path d="M130 94 C145 82, 160 76, 170 72" stroke="url(#heroStroke)" stroke-width="2.2" fill="none" stroke-linecap="round" filter="url(#glow)"/>
  <path d="M216 79 C234 84, 247 91, 255 98" stroke="url(#heroStroke)" stroke-width="2.2" fill="none" stroke-linecap="round" filter="url(#glow)"/>
  <path d="M110 130 C128 140, 142 146, 158 150" stroke="url(#heroStroke)" stroke-width="2.2" fill="none" stroke-linecap="round" filter="url(#glow)"/>
  <path d="M234 150 C248 144, 260 136, 268 126" stroke="url(#heroStroke)" stroke-width="2.2" fill="none" stroke-linecap="round" filter="url(#glow)"/>
</svg>
```

- [ ] **Step 5: Replace the 3 metric cards in hero-side**

Keep the exact same metric content and labels. Update the metric grid to have 3 cards instead of 4 (the featured card + 2 regular):

```html
<div class="metric-grid" style="grid-template-columns:1fr 1fr;">
  <div class="metric">
    <div class="label">Runtime Kernel</div>
    <div class="value">1 Runner</div>
    <p class="desc">唯一执行内核推进同一个 run，避免多套状态循环与恢复混乱。</p>
  </div>
  <div class="metric">
    <div class="label">System Posture</div>
    <div class="value">Tool First</div>
    <p class="desc">所有关键动作经由工具层执行并留下结构化记录，而不是隐式完成。</p>
  </div>
  <div class="metric featured">
    <div class="label">North Star</div>
    <div class="value">Plan → Ship</div>
    <p class="desc">输入一份 plan，输出通过测试、经过审查、可部署的结果。</p>
  </div>
</div>
```

### Task 3: Problem Section — New Icons + Dark Cards

**Files:**
- Modify: `docs/articles/20260416-introducing-sloth-agent.html` (lines 868-895, the "Why now" panel section)

- [ ] **Step 1: Update the "Why now" panel heading**

Keep the same Chinese heading and paragraph text. The `.panel.alt` styles are already updated in Task 1.

- [ ] **Step 2: Replace the 3 problem cards with new amber SVG icons**

Replace the `.cards` section (lines 881-894) with:

```html
<div class="cards">
  <div class="card">
    <div class="card-head">
      <span class="card-icon">
        <svg viewBox="0 0 24 24">
          <path d="M4.93 4.93l14.14 14.14"/>
          <path d="M12 3c4.97 0 9 4.03 9 9 0 1.34-.3 2.6-.82 3.74"/>
          <path d="M12 21c-4.97 0-9-4.03-9-9 0-1.34.3-2.6.82-3.74"/>
          <path d="M21 12c0 4.97-4.03 9-9 9"/>
        </svg>
      </span>
      <h3>能生成，不能稳定推进</h3>
    </div>
    <p>模型可以提出方案，却缺少一个可靠的执行内核来推进任务状态、处理中断、串联工具调用和质量门控。</p>
  </div>
  <div class="card">
    <div class="card-head">
      <span class="card-icon">
        <svg viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="2"/>
          <circle cx="19" cy="5" r="2"/>
          <circle cx="5" cy="19" r="2"/>
          <path d="M10.5 10.5L7.5 16"/>
          <path d="M13.5 13.5L16.5 7.5"/>
        </svg>
      </span>
      <h3>能调用工具，不能解释系统</h3>
    </div>
    <p>文件读写、命令运行、补丁编辑、测试验证常常是分散的能力，缺少统一的审计视图和恢复语义。</p>
  </div>
  <div class="card">
    <div class="card-head">
      <span class="card-icon">
        <svg viewBox="0 0 24 24">
          <path d="M12 3l7 4v5c0 4.2-2.4 6.9-7 9-4.6-2.1-7-4.8-7-9V7l7-4z"/>
          <path d="m15 9-6 6"/>
          <path d="m9 9 6 6"/>
        </svg>
      </span>
      <h3>能写代码，不能承担交付责任</h3>
    </div>
    <p>没有结构化交接、自动 gate 和回滚路径时，agent 仍然停留在"副驾驶"而非"执行系统"。</p>
  </div>
</div>
```

### Task 4: Execution Loop Section — Terminal Style + SVG Flow Diagram

**Files:**
- Modify: `docs/articles/20260416-introducing-sloth-agent.html` (lines 897-979, the "Execution Harness" section)

- [ ] **Step 1: Update the section heading and paragraph**

Keep the same Chinese content. The `.panel` styles are already updated in Task 1.

- [ ] **Step 2: Replace the two `<pre>` blocks with terminal-style code blocks**

Replace lines 910-927 with:

```html
<div class="diagram">
  <pre><span style="color:#F59E0B;">$</span> plan
  <span style="color:#8a8078;">→</span> Builder
  <span style="color:#8a8078;">→</span> Gate 1   <span style="color:#22c55e;"># lint / type / test</span>
  <span style="color:#8a8078;">→</span> Reviewer
  <span style="color:#8a8078;">→</span> Gate 2   <span style="color:#22c55e;"># blocking issues / coverage</span>
  <span style="color:#8a8078;">→</span> Deployer
  <span style="color:#8a8078;">→</span> Gate 3   <span style="color:#22c55e;"># smoke test / rollback</span>
  <span style="color:#8a8078;">→</span> <span style="color:#F59E0B;">Done ✓</span></pre>

  <pre><span style="color:#F59E0B;">$</span> runtime
  CLI / Daemon / Chat
  <span style="color:#8a8078;">→</span> Product Orchestrator
  <span style="color:#8a8078;">→</span> Runner
      <span style="color:#8a8078;">│</span> prepare()
      <span style="color:#8a8078;">│</span> think()
      <span style="color:#8a8078;">│</span> resolve()
      <span style="color:#8a8078;">│</span> persist()
      <span style="color:#8a8078;">└</span> observe()</pre>
</div>
```

- [ ] **Step 3: Update the 4-step flow visual**

Keep the same Chinese content for each step. Update the dot colors and step labels. The `.flow-visual` styles are already updated in Task 1. Change step text color to amber:

```html
<div class="flow-step" style="color:var(--accent);">01</div>
<div class="flow-step" style="color:var(--accent);">02</div>
<div class="flow-step" style="color:var(--accent);">03</div>
<div class="flow-step" style="color:var(--accent);">04</div>
```

- [ ] **Step 4: Update the inline-item list**

Keep the same Chinese content. The `.inline-item` styles are already updated in Task 1.

### Task 5: Quote + Infrastructure Sections

**Files:**
- Modify: `docs/articles/20260416-introducing-sloth-agent.html` (lines 981-1027)

- [ ] **Step 1: Update the quote section**

Keep the same Chinese quote content. Update the `.quote` styles — add dark background:

```css
.quote {
  padding: 28px 32px;
  border-radius: var(--radius-xl);
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 18px;
  align-items: start;
  background: var(--paper);
  border: 1px solid var(--line);
}

.quote-mark {
  font-family: var(--font-display);
  font-size: 4rem;
  line-height: 0.8;
  color: var(--accent);
}

.quote p:first-child {
  font-family: var(--font-display);
  font-size: 1.4rem;
  line-height: 1.35;
  margin-bottom: 10px;
  color: var(--ink);
}

.quote .meta {
  color: var(--muted);
  font-size: 0.94rem;
}
```

- [ ] **Step 2: Update the 6 infrastructure cards with new SVG icons**

Replace lines 1001-1026 with new icons:

```html
<div class="cards">
  <div class="card">
    <div class="card-head">
      <span class="card-icon">
        <svg viewBox="0 0 24 24">
          <path d="M14 6 8 12l6 6"/>
          <path d="M10 6l6 6-6 6"/>
        </svg>
      </span>
      <h3>Tools</h3>
    </div>
    <p>以读写文件、运行命令、补丁编辑、搜索为核心能力，通过工具层执行动作并保留结构化结果，确保系统可审计、可回放。</p>
  </div>
  <div class="card">
    <div class="card-head">
      <span class="card-icon">
        <svg viewBox="0 0 24 24">
          <path d="M6 5h12v14H6z"/>
          <path d="M9 9h6"/>
          <path d="M9 13h6"/>
        </svg>
      </span>
      <h3>Skills</h3>
    </div>
    <p>通过 `SKILL.md` 注入针对任务的高阶行为模板，让模型获得渐进式能力，而不是把所有规则一次性塞进主提示词。</p>
  </div>
  <div class="card">
    <div class="card-head">
      <span class="card-icon">
        <svg viewBox="0 0 24 24">
          <path d="M4 6h16v12H4z"/>
          <path d="M8 6V4h8v2"/>
          <path d="M4 12h16"/>
        </svg>
      </span>
      <h3>Memory</h3>
    </div>
    <p>以文件系统为第一真相源，优先保证简单、可读、可编辑，再向索引与语义层扩展，而不是一开始就把状态埋进黑盒服务。</p>
  </div>
  <div class="card">
    <div class="card-head">
      <span class="card-icon">
        <svg viewBox="0 0 24 24">
          <path d="M4 7h16"/>
          <path d="M4 12h10"/>
          <path d="M4 17h7"/>
        </svg>
      </span>
      <h3>Context Control</h3>
    </div>
    <p>Builder 负责最重的上下文负载，因此需要明确的窗口分区、规则压缩和输出预留，避免长任务在最关键时刻失焦。</p>
  </div>
  <div class="card">
    <div class="card-head">
      <span class="card-icon">
        <svg viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="8"/>
          <path d="M12 5v7l4 2"/>
        </svg>
      </span>
      <h3>Checkpoints</h3>
    </div>
    <p>状态持久化不是为了做日志归档，而是为了让 agent 在失败、中断、审批或环境变化后，仍然能够继续同一个 run。</p>
  </div>
  <div class="card">
    <div class="card-head">
      <span class="card-icon">
        <svg viewBox="0 0 24 24">
          <path d="M12 3l7 4v5c0 4.2-2.4 6.9-7 9-4.6-2.1-7-4.8-7-9V7l7-4z"/>
          <path d="m9.5 12 1.8 1.8 3.2-3.6"/>
        </svg>
      </span>
      <h3>Hallucination Guard</h3>
    </div>
    <p>路径白名单、命令黑名单、工具结果验证与运行时边界一起工作，把"模型猜测"尽可能限制在可见、可证、可拒绝的范围内。</p>
  </div>
</div>
```

### Task 6: Control Surface + Roadmap Sections

**Files:**
- Modify: `docs/articles/20260416-introducing-sloth-agent.html` (lines 1029-1115)

- [ ] **Step 1: Update the control surface section**

Keep the same Chinese content and card text. The `.card` styles for this section (no icon header) are already handled by the base `.card h3` and `.card p` rules updated in Task 1.

- [ ] **Step 2: Update the roadmap section**

Keep the same Chinese content and version text. The `.roadmap-step` and `.state` styles are already updated in Task 1. Update the roadmap grid to use `grid-template-columns: repeat(4, minmax(0, 1fr))` — already correct in existing CSS.

### Task 7: Closing Section + Final Polish

**Files:**
- Modify: `docs/articles/20260416-introducing-sloth-agent.html` (lines 1117-1161)

- [ ] **Step 1: Update the closing section**

Keep the same Chinese content. Update the footer card styles (already done in Task 1). Update the CTA button colors and the Execution Loop badge panel (already done in Task 1).

- [ ] **Step 2: Add scroll-triggered entrance animation for sections (optional, lightweight)**

Add a minimal JS observer at the bottom of the page, before the closing `</body>` tag, to add a subtle fade-in as sections scroll into view:

```html
<script>
  const progress = document.getElementById('progress');
  const updateProgress = () => {
    const scrollTop = window.scrollY;
    const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
    const ratio = maxScroll > 0 ? scrollTop / maxScroll : 0;
    progress.style.transform = `scaleX(${Math.min(1, Math.max(0, ratio))})`;
  };
  updateProgress();
  window.addEventListener('scroll', updateProgress, { passive: true });
  window.addEventListener('resize', updateProgress);

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.style.opacity = '1';
          entry.target.style.transform = 'translateY(0)';
        }
      });
    },
    { threshold: 0.1 }
  );

  document.querySelectorAll('.panel, .quote, .roadmap, .footer-card').forEach((el) => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
    observer.observe(el);
  });
</script>
```

- [ ] **Step 3: Open the HTML in browser to verify rendering**

Open `docs/articles/20260416-introducing-sloth-agent.html` in a browser and verify:
- Dark background renders correctly
- Amber accent colors are visible and contrast well
- SVG icons display properly with amber strokes
- All sections are readable on dark background
- Hover effects work on cards and buttons
- Responsive layout still works at mobile widths
- Google Fonts load correctly
- Scroll progress bar shows amber gradient

- [ ] **Step 4: Commit the redesign**

```bash
git add docs/articles/20260416-introducing-sloth-agent.html
git commit -m "design: Terminal Noir redesign of Sloth Agent intro article

- Dark color system (#111 background, amber #F59E0B accent)
- New SVG icons for all capability cards
- Updated hero diagram with amber gradient strokes
- Terminal-style code blocks with colored syntax
- Scroll-triggered fade-in animations
- Google Fonts: Space Grotesk, Noto Sans SC, JetBrains Mono"
```
