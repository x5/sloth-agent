---
name: autoplan
source: adapted from gstack (MIT License)
trigger: auto+manual
version: 1.0.0
description: "Automated plan review. Reads the active plan file and runs strategy, engineering, and design reviews automatically. Challenges assumptions, detects scope creep, suggests alternatives. Use when asked to 'review the plan', 'check my plan', 'is this plan good', 'validate the plan', 'review before implementing', 'plan review', 'technical plan review', 'architecture review of the plan', or 'does this plan make sense'."
---

# autoplan: Automated Plan Review

Read the active plan file and run multiple review passes automatically. Challenge assumptions, detect scope creep, suggest alternatives.

## Phase 0: Intake

### Step 1: Read context

1. Read `CLAUDE.md`, `TODOS.md` (if they exist)
2. Run `git log --oneline -30` and `git diff origin/main --stat` for recent context
3. Find the active plan file (in `.claude/plans/` or referenced in conversation)

### Step 2: Detect scope

- **UI scope:** Does the plan mention components, screens, forms, buttons, layouts, dashboards? (2+ matches)
- **DX scope:** Does the plan mention APIs, endpoints, CLIs, SDKs, developer tools, agents? (2+ matches)
- **Backend scope:** Database, models, services, auth, migrations

Output: "Here's the plan. UI scope: yes/no. DX scope: yes/no. Backend scope: yes/no."

---

## Phase 1: Strategy Review

Challenge the strategic foundations:

1. **Premise check:** Are the assumptions valid or just assumed? Which could be wrong?
2. **Right problem:** Is this the right problem to solve? Could a reframing yield 10x impact?
3. **Existing leverage:** What code already exists that solves sub-problems?
4. **Alternatives:** What approaches were dismissed without sufficient analysis?
5. **Scope calibration:** Is the scope appropriate for the goal? Any creep?
6. **6-month test:** What will look foolish in 6 months?

**Dream state diagram:**
```
CURRENT STATE → THIS PLAN → 12-MONTH IDEAL
```

**Implementation alternatives table:**
| Approach | Effort | Risk | Pros | Cons |
|----------|--------|------|------|------|

---

## Phase 2: Engineering Review (if backend or DX scope)

1. **Architecture:** Are the component boundaries right? Any tight coupling?
2. **Data model:** Are the tables/schemas normalized? Missing indexes?
3. **API design:** RESTful? Consistent naming? Error handling?
4. **Performance:** Any N+1 queries, missing caching, large payloads?
5. **Security:** Auth checks, input validation, rate limiting?
6. **Testing strategy:** What needs tests? Are edge cases covered?
7. **Error handling:** What happens when things fail?

---

## Phase 3: Design Review (if UI scope)

1. **Information architecture:** Navigation structure, content hierarchy
2. **Interaction design:** Key user flows, feedback patterns
3. **Responsive design:** Mobile considerations, breakpoints
4. **Accessibility:** Keyboard navigation, screen reader support
5. **Consistency:** Design system alignment, component reuse

---

## Phase 4: Scope Drift Check

Compare the plan against the stated goal:

1. **Must-have:** Items directly required to solve the problem
2. **Nice-to-have:** Items that improve the solution but aren't essential
3. **Out of scope:** Items unrelated to the stated goal

Flag any items in category 3 as scope creep.

---

## Phase 5: Error & Rescue Registry

For each major component, identify what could go wrong:

| Component | Failure Mode | Detection | Recovery |
|-----------|-------------|-----------|----------|

---

## Phase 6: Consolidated Report

```
PLAN REVIEW REPORT
═══════════════════════════════════
Plan: {title}
Branch: {branch}

## Strategy Findings
{premises, alternatives, dream state}

## Engineering Findings
{architecture, data model, security, performance}

## Design Findings (if applicable)
{information architecture, interactions, accessibility}

## Scope Analysis
Must-have: N items
Nice-to-have: M items
Out of scope: K items

## Error & Rescue Registry
{table of failure modes and recovery plans}

## Recommendations
1. {highest priority recommendation}
2. {second priority}
3. {third priority}

## Deferred Items
{items suggested but not essential for V1}
```

---

## Important Rules

- **Challenge, don't praise.** The value is in finding problems, not confirming goodness.
- **Auto-decide where safe.** Don't ask about trivial choices — pick the better option and explain why.
- **Human judgment for big decisions.** Strategy pivots, scope expansions, and taste decisions need the user's call.
- **Always generate alternatives.** Never accept the plan as the only way.

---

## Completion Status

- **DONE** — Plan reviewed, report generated
- **DONE_WITH_CONCERNS** — Review completed but major unresolved concerns remain
