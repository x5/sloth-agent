---
name: plan-ceo-review
source: adapted from gstack (MIT License)
trigger: auto+manual
version: 1.0.0
description: "Strategic review of a development plan from a product/business perspective. Challenges premises, validates market fit, checks scope decisions. Use when asked to 'strategic review', 'is this the right thing to build', or 'ceo review of the plan'."
---

# plan-ceo-review: Strategic Plan Review

Review a development plan from a product/business strategy perspective.

## Phase 1: Premise Challenge

Question every assumption in the plan:

1. **What premises are stated?** List them explicitly.
2. **Which are verified vs assumed?** How do we know they're true?
3. **What if a premise is wrong?** What's the fallback?

## Phase 2: Right Problem Check

1. **Is this the right problem?** Could a reframing yield 10x impact?
2. **Who actually has this pain?** Can you name a specific person?
3. **What are they doing now?** What's the current workaround?
4. **Will they pay/change?** What evidence supports this?

## Phase 3: Scope Calibration

1. **Is the scope right for the goal?** Too big? Too small?
2. **What's the wedge?** The smallest thing someone would pay for this week?
3. **What's out of scope?** What was deferred and why?
4. **Will this look foolish in 6 months?** What competitive/market risks are ignored?

## Phase 4: Alternatives

Generate 3 alternatives:
1. **Simpler** — What's the 80/20 version?
2. **Different** — What approach wasn't considered?
3. **Bigger** — If resources were unlimited, what would you build?

## Phase 5: Output

```
STRATEGIC PLAN REVIEW
═══════════════════════════════
Plan: {title}

## Premises
- {premise 1}: {verified/assumed} — {evidence}
- {premise 2}: {verified/assumed} — {evidence}

## Problem Fit
- Right problem? {yes/no/partially}
- Evidence: {what supports this}
- Risk: {what could be wrong}

## Scope
- Appropriate? {yes/too-big/too-small}
- Wedge: {smallest valuable thing}
- Deferred: {what was left out}

## Alternatives
1. Simpler: {description}
2. Different: {description}
3. Bigger: {description}

## Verdict
{BUILD / PIVOT / REFRAME} — {one-line rationale}
```

---

## Important Rules

- **Challenge, don't validate.** The value is in finding flaws in reasoning.
- **Demand evidence.** "I think users want this" is not evidence. "3 users paid $50" is.
- **No sycophancy.** Take positions on every answer.
- **End with a verdict.** Build, pivot, or reframe — pick one.

---

## Completion Status

- **DONE** — Strategic review complete
- **DONE_WITH_CONCERNS** — Review completed but major unresolved strategic questions
