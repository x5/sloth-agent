# Sloth Agent Intro Article - Terminal Noir Redesign Spec

> Date: 2026-04-16
> Status: Approved
> Target: docs/articles/20260416-introducing-sloth-agent.html

---

## Design Direction: Terminal Noir

Dark engineering aesthetic with amber accent. Full visual overhaul from warm editorial to dark tech terminal style.

## Visual System

| Dimension | Value |
|-----------|-------|
| **Background** | `#111111` base, `#1a1a1a` card surfaces, subtle `#F59E0B` radial glow at top |
| **Text** | Body `#e8e0d8` (warm white), muted `#8a8078`, headings `#ffffff` |
| **Primary** | `#F59E0B` (amber), gradient to `#F97316` (orange-red) for progress bar and emphasis |
| **Accent** | `#22c55e` (green, pass state), `#ef4444` (red, fail/alert) |
| **Border** | 1px `#2a2a2a` card borders, hover → `#F59E0B` semi-transparent |
| **Fonts** | English headings: `Space Grotesk` (Google Fonts), Chinese: `Noto Sans SC` (Google Fonts), Code: `JetBrains Mono` (Google Fonts) |
| **Icons** | All inline SVG, linear style (2px stroke, amber color), one per capability card |

## Page Structure

1. **Top bar**: 3px amber gradient progress bar + nav (left: `● SLOTH AGENT`, right: date)
2. **Hero (2-col)**: Left - huge "Sloth Agent" heading + CN subtitle. Right - SVG system architecture diagram (Builder → Reviewer → Deployer → Runner with connections) + 3 metric cards
3. **Problem section (full-width)**: Heading + 3-card grid with SVG linear icons (broken link, scattered blocks, unchecked shield)
4. **Execution loop (core diagram)**: Top - text flowchart in terminal code-block style. Bottom - SVG horizontal flow diagram with 4 stage nodes connected by gradient lines
5. **Quote section**: Dark panel, large amber `"` quote mark
6. **Infrastructure section (3×2 grid)**: 6 cards with SVG icons (Tools, Skills, Memory, Context, Checkpoints, Guard)
7. **Control surface section (3×2 grid)**: 6 text-only cards with amber left border
8. **Roadmap (4-col grid)**: Version cards with status badges
9. **Closing (full-width dark)**: Heading + summary + CTA buttons + "Execution Loop" badge panel

## Interactions

- Card hover: `translateY(-4px)` + border → amber semi-transparent
- Button hover: `translateY(-2px)`
- Scroll progress: top 3px amber gradient, fills on scroll
- No entrance animations, keep it restrained

## Content

All existing Chinese content preserved, only visual system replaced.
