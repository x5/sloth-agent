# Sloth Agent Intro - Kraken Redesign Spec

> Date: 2026-04-16
> Status: In Progress
> Design Reference: Kraken (purple-accented dark UI, data-dense dashboards)
> Diagram Tool: architecture-diagram-generator (Cocoon-AI)

---

## Design System

### Colors
| Token | Value | Usage |
|-------|-------|-------|
| `--bg-deepest` | `#06080D` | Page top gradient start |
| `--bg-deep` | `#0B0F19` | Page background (Slate 950) |
| `--bg` | `#111827` | Card surface base (Slate 900) |
| `--bg-elevated` | `#151B2B` | Elevated cards, panels |
| `--bg-hover` | `#1A2235` | Hover state |
| `--surface` | `#1E293B` | Subtle surfaces (Slate 800) |
| `--ink` | `#F1F5F9` | Primary text (Slate 100) |
| `--ink-soft` | `#CBD5E1` | Secondary text (Slate 300) |
| `--muted` | `#94A3B8` | Tertiary text (Slate 400) |
| `--accent` | `#8B5CF6` | Primary purple (violet-500) |
| `--accent-soft` | `#A78BFA` | Light purple (violet-400) |
| `--accent-glow` | `rgba(139, 92, 246, 0.15)` | Purple glow effects |
| `--accent-2` | `#06B6D4` | Cyan secondary (cyan-500) |
| `--accent-2-soft` | `rgba(6, 182, 212, 0.08)` | Cyan soft backgrounds |
| `--line` | `rgba(255, 255, 255, 0.06)` | Subtle borders |
| `--line-strong` | `rgba(139, 92, 246, 0.25)` | Accent borders |
| `--success` | `#22c55e` | Pass/good states |
| `--warning` | `#F59E0B` | Warning states |
| `--danger` | `#ef4444` | Error states |

### Typography
| Element | Font | Size | Weight |
|---------|------|------|--------|
| Hero H1 | JetBrains Mono | clamp(2.8rem, 5vw, 4.5rem) | 700 |
| Section H2 | JetBrains Mono | clamp(1.6rem, 3vw, 2.4rem) | 600 |
| Card H3 | Inter + Noto Sans SC | 1.15rem | 600 |
| Body | Inter + Noto Sans SC | 0.95rem | 400 |
| Code | JetBrains Mono | 0.8125rem | 400 |
| Label/Caption | JetBrains Mono | 0.6875rem | 500, uppercase |

### Spacing
- Section gap: 64px
- Card gap: 20px
- Card padding: 24px
- Panel padding: 32px
- Content max-width: 1200px

### Effects
- Card shadow: `0 4px 24px rgba(0, 0, 0, 0.3)`
- Card hover shadow: `0 8px 40px rgba(139, 92, 246, 0.12)`
- Card hover border: `1px solid rgba(139, 92, 246, 0.3)`
- Card hover lift: `translateY(-3px)`
- Radius: `16px` (cards), `24px` (panels)
- Glow filter: `feGaussianBlur stdDeviation="3"` for diagram nodes

### Layout Structure
1. **Top Bar** — Fixed, translucent, with progress indicator
2. **Hero** — Centered, large monospace title + subtitle + tag pills
3. **System Architecture** — Full-width SVG diagram (generated)
4. **Why Sloth Agent** — 3-column problem cards
5. **Execution Harness** — Terminal code block + 4-step flow cards
6. **Infrastructure** — 3×2 icon card grid
7. **Control Surface** — Compact feature list with purple left borders
8. **Roadmap** — Horizontal timeline
9. **Footer** — Full-width dark panel with CTA buttons

### Diagram Style (architecture-diagram-generator inspired)
- Dark slate-950 background with subtle grid
- Semantic color coding: Cyan=Client, Emerald=Agent, Violet=Storage, Amber=Infra, Rose=Security
- Clean SVG arrows with arrowheads
- JetBrains Mono labels
- Auto-layout with clear visual hierarchy
