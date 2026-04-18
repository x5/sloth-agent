---
name: design-review
source: adapted from gstack (MIT License)
trigger: auto+manual
version: 1.0.0
description: "Visual design review of implemented UI. Compares implementation against design intent, checks visual consistency, accessibility, and responsive behavior. Use when asked to 'design review', 'visual review', 'audit the UI', 'does this look right', 'check the design', 'visual audit', 'review the UI', 'accessibility check', 'responsive design check', 'does this match the design', or 'UI consistency review'."
---

# design-review: Visual UI Review

Review implemented UI against design intent. Check visual consistency, accessibility, and responsive behavior.

## Phase 1: Design Intent Check

1. Read DESIGN.md or design specs (if they exist)
2. Compare the implementation against the intended design
3. Note any deviations: intentional vs accidental

## Phase 2: Visual Consistency

1. **Typography:**
   - Consistent font families?
   - Proper hierarchy (h1 > h2 > h3 > body)?
   - Readable line lengths (45-75 characters)?

2. **Color:**
   - Consistent palette?
   - Sufficient contrast (WCAG AA: 4.5:1 for normal text)?
   - Color used purposefully, not decoratively?

3. **Spacing:**
   - Consistent spacing scale (4px, 8px, 16px, 24px, 32px)?
   - Adequate whitespace between sections?
   - Not cramped or wasteful?

4. **Alignment:**
   - Elements aligned to a grid?
   - Consistent margins and padding?
   - No visual "orphan" elements?

## Phase 3: Responsive Check

Test at three breakpoints:
- **Mobile (375px):** Everything usable? No horizontal scroll?
- **Tablet (768px):** Layout adapts gracefully?
- **Desktop (1280px):** Space used effectively?

## Phase 4: Accessibility Check

1. Keyboard navigation: Tab through all interactive elements
2. Focus indicators: Visible and clear?
3. Alt text: Images have meaningful descriptions?
4. Form labels: All inputs have associated labels?
5. ARIA: Used correctly where needed?

## Phase 5: Output

```
DESIGN REVIEW
═══════════════════════════════
Page: {page/component}

Visual consistency: {score}/10
Responsive behavior: {score}/10
Accessibility: {score}/10
Design fidelity:  {score}/10

Deviations from design:
- {deviation 1}: {intentional/accidental}
- {deviation 2}: {intentional/accidental}

Top fixes:
1. {highest priority visual issue}
2. {second priority}
3. {third priority}
```

---

## Important Rules

- **Design intent is the baseline.** Compare against specs, not personal taste.
- **Accessibility is non-negotiable.** Every UI must work with keyboard and screen reader.
- **Consistency over creativity.** A consistent mediocre design is better than an inconsistent great one.
- **Mobile first.** If it doesn't work at 375px, it doesn't work.

---

## Completion Status

- **DONE** — Design review complete
- **DONE_WITH_CONCERNS** — Review completed but significant visual issues found
