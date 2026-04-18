---
name: plan-design-review
source: adapted from gstack (MIT License)
trigger: auto+manual
version: 1.0.0
description: "Design review of a development plan. Checks information architecture, interaction design, visual consistency, and accessibility. Use when asked to 'design review of the plan', 'review the UI plan', or 'is the design good'."
---

# plan-design-review: Design Plan Review

Review the design aspects of a development plan.

## Step 1: Information Architecture

1. **Navigation:** Is the structure intuitive? Can users find what they need?
2. **Content hierarchy:** Is the most important information prominent?
3. **Depth:** How many clicks to accomplish the primary task?

## Step 2: Interaction Design

1. **Key flows:** Walk through the primary user journey step by step
2. **Feedback:** Does the user know what's happening? Loading states, success/error messages
3. **Recovery:** Can users undo mistakes? Are destructive actions confirmed?

## Step 3: Visual Consistency

1. **Design system alignment:** Are existing components/patterns used?
2. **Typography:** Hierarchy clear? Consistent font sizes?
3. **Color:** Purpose-driven (not decorative)? Accessible contrast?
4. **Spacing:** Consistent rhythm? Not cramped or wasteful?

## Step 4: Accessibility

1. **Keyboard navigation:** All interactive elements reachable?
2. **Screen reader:** Semantic HTML? ARIA labels where needed?
3. **Color independence:** Information not conveyed by color alone?
4. **Focus management:** Visible focus indicators?

## Step 5: Responsive Design

1. **Mobile:** Does it work at 375px width?
2. **Tablet:** Does it adapt gracefully at 768px?
3. **Desktop:** Does it use the space well at 1280px+?

## Step 6: Output

```
DESIGN PLAN REVIEW
═══════════════════════════════
Plan: {title}

Information architecture: {score}/10 — {summary}
Interaction design:       {score}/10 — {summary}
Visual consistency:       {score}/10 — {summary}
Accessibility:            {score}/10 — {summary}
Responsive:               {score}/10 — {summary}

Top 3 design concerns:
1. {most critical design issue}
2. {second concern}
3. {third concern}

Recommendations:
1. {highest priority fix}
2. {second priority}
```

---

## Important Rules

- **User flows first.** A beautiful design that doesn't work is a failed design.
- **Accessibility is mandatory.** Not optional, not "nice to have."
- **Consistency over creativity.** Existing patterns should be reused unless there's a strong reason.
- **Mobile is not an afterthought.** Design for the smallest screen first.

---

## Completion Status

- **DONE** — Design review complete
- **DONE_WITH_CONCERNS** — Review completed but significant design gaps found
