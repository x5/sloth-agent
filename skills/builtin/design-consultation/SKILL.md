---
name: design-consultation
source: adapted from gstack (MIT License)
trigger: auto+manual
version: 1.0.0
description: "Design consultation and UI proposal. Researches design patterns, creates a complete design proposal with alternatives, and generates DESIGN.md. Use when asked to 'design consultation', 'design this', 'what should this look like', 'propose a design', 'UI design', 'design review', 'make this look good', 'suggest a layout', 'design proposal', 'how should this page look', or 'design ideas'."
---

# design-consultation: UI Design Proposal

Research design patterns, propose UI designs with alternatives, and generate DESIGN.md.

## Phase 0: Pre-checks

1. Read CLAUDE.md for any existing design system references
2. Check if DESIGN.md already exists
3. Understand what the user wants to design (feature, page, component)

## Phase 1: Requirements

Ask the user:
1. What are you designing? (feature/page/component)
2. Who is the user? (persona, role)
3. What's the goal? (what should the user accomplish)
4. Any constraints? (brand guidelines, existing design system, accessibility requirements)

## Phase 2: Research

Research comparable designs and patterns:
- What are industry leaders doing for similar features?
- What design patterns are standard for this type of interface?
- What accessibility requirements apply?

## Phase 3: Design Proposal

Create a complete design proposal:

```markdown
# Design: {Title}

## Problem
{What are we solving? For whom?}

## User Flow
{Step-by-step: what the user does}

## Layout
{Wireframe description: header, sidebar, main content, footer}

## Components
{List of components needed and their purpose}

## Interactions
{Key interactions: clicks, hovers, transitions, feedback}

## States
{Default, loading, empty, error, success}

## Accessibility
{Keyboard navigation, screen reader, color contrast}

## Responsive
{Mobile, tablet, desktop behavior}
```

## Phase 4: Alternatives

Present 2-3 design alternatives:
1. **Minimal** — Simplest possible design
2. **Standard** — Industry-standard approach
3. **Innovative** — Something differentiated

For each: pros, cons, effort estimate.

## Phase 5: Design System Alignment

If the project has an existing design system:
- Reference existing components where possible
- Note any new components needed
- Ensure consistency with established patterns

If no design system exists:
- Suggest a foundational set (colors, typography, spacing, components)
- Recommend tools (Tailwind, CSS variables, component library)

## Phase 6: Write DESIGN.md

Save the approved design to `DESIGN.md` or the project's design docs directory.

---

## Important Rules

- **User-first.** Design for the user's goal, not for aesthetics.
- **Alternatives always.** Never present one design.
- **Accessibility is non-negotiable.** Every design must work for keyboard and screen reader.
- **Reference real patterns.** Don't invent interactions that nobody uses.

---

## Completion Status

- **DONE** — Design proposal created, DESIGN.md written
- **DONE_WITH_CONCERNS** — Proposal created but some requirements unclear
