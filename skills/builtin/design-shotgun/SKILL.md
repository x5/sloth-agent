---
name: design-shotgun
source: adapted from gstack (MIT License)
trigger: auto+manual
version: 1.0.0
description: "Rapid design exploration. Generates multiple design variants quickly, lets the user pick the best direction, then refines the winner. Use when asked to 'design shotgun', 'show me options', 'explore designs', 'give me 3 options', 'design alternatives', 'quick design options', 'show different layouts', 'design variants', 'explore visual directions', or 'I need design choices'."
---

# design-shotgun: Rapid Design Exploration

Generate multiple design variants quickly, pick the best, then refine.

## Step 1: Requirements

Gather design requirements:
1. What are we designing? (page, component, feature)
2. Who is the user?
3. What's the goal?
4. Any brand constraints? (colors, fonts, style guide)
5. Any reference designs they like?

## Step 2: Generate Variants

Create 3 distinct design variants:

1. **Variant A — Minimal:** Clean, sparse, maximum whitespace
2. **Variant B — Standard:** Industry-typical layout, familiar patterns
3. **Variant C — Bold:** Differentiated, unexpected, stands out

For each variant, describe:
- Layout structure
- Color palette
- Typography choices
- Key design decisions and rationale

## Step 3: Present Options

Show all three variants side by side. For each:
- What works well
- What could be improved
- When you'd choose this over the others

## Step 4: Selection

Ask the user to choose:
- A) Variant A (Minimal)
- B) Variant B (Standard)
- C) Variant C (Bold)
- D) Mix — elements from different variants

## Step 5: Refine

Based on the selection:
1. Apply the user's feedback
2. Iterate until they're satisfied
3. Save the final design

## Step 6: Save

Save the approved design:
- Screenshot/mockup to `designs/{screen-name}/approved.png`
- Design tokens to `DESIGN.md`
- Component specs to `DESIGN.md` or design doc

---

## Important Rules

- **Three distinct options.** Not three shades of the same design.
- **Speed over perfection.** The goal is direction-finding, not pixel perfection.
- **Real content.** Use realistic copy, not placeholders.
- **Reference patterns.** Ground designs in what users already know works.

---

## Completion Status

- **DONE** — Design variant selected and refined
- **DONE_WITH_CONCERNS** — Variant selected but significant refinements needed
