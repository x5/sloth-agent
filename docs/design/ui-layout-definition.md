# UI Layout Definition — Sloth Agent

Last updated: 2026-04-25

---

## Layout Overview

```
┌────────┬──────────────────┬──────────────────────────────┬──────────────┐
│  Col1  │       Col2       │            Col3              │     Col4     │
│  64px  │  280px ⇔ ~48px   │         flex: 1 ⇔           │  320px ⇔ 0   │
│ Tools  │   List Panel     │   Main Interaction Area      │  Detail      │
│ Menu   │   (collapsible)  │   (adapts when Col4 opens)   │  (dismissable)│
└────────┴──────────────────┴──────────────────────────────┴──────────────┘
```

| Column  | Width               | Role                              | Visibility      |
|---------|---------------------|-----------------------------------|-----------------|
| Col1    | 64px fixed          | Tool menu bar                     | Always visible   |
| Col2    | 280px ⇔ ~48px       | List panel (content-switchable)   | Collapsible      |
| Col3    | flex: 1 (adaptive)  | Main interaction + content area   | Always visible   |
| Col4    | 320px ⇔ 0           | Detail / context panel            | Dismissable      |

---

## Col1 — Tool Menu Bar (64px)

**Purpose:** Global navigation and agent status. All buttons here drive content in Col2 and Col3.

### Structure (top → bottom)

| Element            | Behavior                                                       |
|--------------------|----------------------------------------------------------------|
| Logo               | Global agent status indicator (idle / working / error). Purely indicative. |
| Nav button 1       | Inspiration — switches Col2 to Inspiration list                |
| Nav button 2       | Agents — switches Col2 to Agents list                          |
| Nav button 3       | Settings — switches Col2 to Settings panel                     |
| Spacer             | Pushes avatar to bottom                                        |
| User avatar        | Placeholder button. Future: user profile / preferences.        |

### Rules
- Only one nav button active at a time
- Active button → Col2 content switches accordingly
- Col2 collapse/expand does NOT affect Col1

---

## Col2 — List Panel (280px ⇔ ~48px)

**Purpose:** Displays the list or panel corresponding to the active Col1 nav item. Content is dynamic and Col1-driven.

### Content by Col1 selection

| Col1 active       | Col2 content              |
|-------------------|---------------------------|
| Inspiration       | Inspiration list + CRUD   |
| Agents            | Agents list               |
| Settings          | Settings panel            |

### Collapse behavior
- **Expand (280px):** full list view, all content visible
- **Collapse (~48px):** narrow vertical strip, icon-only, no text labels
- **Toggle button:** placed at the top-right (or bottom-right) of Col2
- When collapsed, Col3 gains the freed width

### Rules
- Col2 remembers its collapsed/expanded state per Col1 selection (TBD)
- Hovering a collapsed Col2 could show a temporary tooltip or mini-preview (TBD)

---

## Col3 — Main Interaction & Content Area (flex: 1, adaptive)

**Purpose:** Primary workspace. Content depends on the current task context (Inspiration chat, Agent workflow, etc.).

### Topbar

| Element            | Behavior                                                       |
|--------------------|----------------------------------------------------------------|
| Project name       | Shows current project/context name                             |
| Status tag         | Shows current agent status (e.g. "RUNNING")                    |
| Team button        | Opens Col4 with team/member details                            |
| Status button      | Opens Col4 with latest status feed / activity                  |
| More button        | Placeholder — future overflow menu                             |

### Main canvas
- For Inspiration: chat-style interaction, conversation flow
- For Agents: TBD
- For Settings: TBD

### Input area (bottom)
- Currently placeholder, disabled
- Future: prompt input + send button

### Width adaptation
- Col4 closed → Col3 stretches to right edge
- Col4 open (320px) → Col3 width = viewport - C1 - C2 - C4

### Rules
- Team and Status buttons open Col4; if Col4 is already showing a different panel, it switches
- If the same button is clicked while Col4 is showing its content, Col4 closes (toggle behavior)
- Col4 can also be dismissed with a close button inside Col4 itself

---

## Col4 — Detail / Context Panel (320px ⇔ 0)

**Purpose:** Shows contextual details summoned from Col3's Topbar. Dismissable.

### Content by trigger

| Trigger            | Col4 content                      |
|--------------------|-----------------------------------|
| Team button (C3)   | Team members, roles, status       |
| Status button (C3) | Activity feed, system status log  |
| (future) Item click in Col2 | Item detail / properties  |

### Dismiss behavior
- Close button (X) inside Col4 header
- Clicking the active Topbar button again (toggle)
- Width transitions to 0, then display: none

### Rules
- Only one content type shown at a time
- Col4 remembers its last content type per context (TBD)

---

## Cross-Module Interaction Summary

| Trigger                  | Target     | Action                          |
|--------------------------|------------|---------------------------------|
| Col1 nav button          | Col2       | Switch list content             |
| Col2 collapse toggle     | Col2       | Expand 280px ↔ Collapse ~48px  |
| Col3 Topbar Team button  | Col4       | Open/show team details          |
| Col3 Topbar Status button| Col4       | Open/show status feed           |
| Col3 Topbar More button  | —          | Placeholder (overflow menu)     |
| Col4 close button        | Col4       | Close panel, Col3 expands       |
| Col2 item click          | Col3/Col4  | Load item into main area / detail (TBD) |

---

## Visual Adjustments Queue (2026-04-25 review)

Items identified during UI walkthrough. To be fixed in batch.

### 1. Col3 background color mismatch

- **Problem:** `.chatarea` background is `bg-page` (#f9f9f9 gray); canvas and input area use `bg-surface` (#ffffff white). The gray bleeds through below the input box.
- **Fix:** Change `.chatarea` background to `var(--bg-surface)`.

### 2. Header height & title font too large

- **Problem:** Col2/Col3/Col4 headers are 64px tall with 20px/600 title text, nearly 2× the body text (14-16px). Looks heavy and wastes vertical space.
- **Fix:** Reduce header height from 64px to a smaller value (TBD). Reduce title font size from 20px/16px to ~15px/14px.

### 3. Divider lines — no engraved texture

- **Problem:** All borders use `1px solid #e2e2e2` (or `#e2e2e2`). Too thick, too dark, flat — no depth. Should look like a fine laser-etched groove in metal.
- **Affected:** Col1‒Col4 column borders, Col2 search divider, Col3 topbar bottom border, Col4 header bottom border.
- **Fix:** Replace with a two-layer approach — a thin dark line + adjacent light line to create an inset (engraved) effect. Use `rgba(0,0,0,0.06)` and `rgba(255,255,255,0.8)` or tokens.

### 4. All icons — unified redesign

- **Problem:** Inconsistent style across the app. Some use `fill`, some `stroke`. Stroke widths, sizes, and visual weight vary. Some icons lack clear meaning.
- **Scope (12 icon locations):**

| # | Location | Current | Issue |
|---|----------|---------|-------|
| 1 | C1 — Inspiration | Chat bubble | Replace with creative lightbulb |
| 2 | C1 — Agents | Starburst/sun | Replace with robot head |
| 3 | C1 — Settings | Gear | Too cliche — find a simpler, more modern metaphor |
| 4 | C1 — Avatar | User silhouette | Placeholder OK |
| 5 | C2 — Add button | Plus | OK |
| 6 | C3 — Team | Two-person silhouette | Acceptable |
| 7 | C3 — Status | ⓘ Circle-i | Meaning unclear for "status" — replace |
| 8 | C3 — More | Three vertical dots | OK |
| 9 | C3 — Attach file | Paperclip | OK |
| 10 | C3 — @Mention | User + circle | Acceptable |
| 11 | C3 — Send | Paper plane | OK |
| 12 | C3 — Empty state | Chat bubble | Redundant with C1 — remove or differentiate |

- **Fix:** Design a consistent icon set — uniform stroke width, same viewBox (24×24), same visual density. Replace icons #2, #7 with clearer metaphors. Consider a single icon library approach (e.g. Feather icons or custom SVG sprite).

### 5. Missing interactions (from layout definition)

- Col2 collapse/expand toggle button + animation
- Col3 Topbar buttons → Col4 open/close toggle + slide animation
- Col4 dismiss with X button
- Col3 adaptive width when Col4 show/hide
- Col4 default state: closed

### 6. Design system — standards not yet defined

- **Color tokens:** Only green + gray palette defined. Need full semantic token map (primary, success, warning, error, info, surface levels, text hierarchy).
- **Spacing scale:** No explicit spacing system. Current values (8px, 12px, 16px, 24px, 32px) are ad-hoc. Need a consistent 4px-grid scale.
- **Type scale:** Font sizes scattered (10px to 20px). No hierarchy — what's H1/H2/body/caption/label? Need defined scale with line-heights and weights.
- **Component states:** Buttons, inputs, list items — hover / active / focus / disabled / loading states not consistently defined.
- **Animation tokens:** Logo uses custom @keyframes values (4.5s, 1.2s, 8s). No shared easing curves, duration tokens, or transition presets for the rest of the UI.
- **Responsive breakpoints:** Window min-width, Col2 collapse threshold, Col4 overlay vs push behavior at narrow widths — not defined.
- **Accessibility:** No contrast audit, no focus-ring design, no keyboard navigation spec, no screen-reader labels defined.
- **Dark mode:** No plan yet.

- Col2 collapse/expand toggle button + animation
- Col3 Topbar buttons → Col4 open/close toggle + slide animation
- Col4 dismiss with X button
- Col3 adaptive width when Col4 show/hide
- Col4 default state: closed
