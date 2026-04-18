---
name: plan-eng-review
source: adapted from gstack (MIT License)
trigger: auto+manual
version: 1.0.0
description: "Engineering review of a development plan. Checks architecture, data model, API design, testing strategy, and implementation feasibility. Use when asked to 'review the engineering plan', 'technical review of the plan', or 'is this plan technically sound'."
---

# plan-eng-review: Engineering Plan Review

Review a development plan from an engineering perspective.

## Step 0: Load the Plan

Read the active plan file (from `.claude/plans/` or conversation context).

## Step 1: Architecture Review

1. **Component boundaries:** Are responsibilities well-separated? Any tight coupling?
2. **Data flow:** Is the data flow clear? Any circular dependencies?
3. **Scalability:** Will this approach work at 10x the current load?
4. **Technology choices:** Are the framework/library choices appropriate?

## Step 2: Data Model Review

1. **Schema design:** Normalized? Missing indexes? Appropriate data types?
2. **Migrations:** Safe to run on production? Backwards compatible?
3. **Data integrity:** Foreign keys, constraints, cascading deletes?

## Step 3: API Design Review

1. **Consistency:** Naming, versioning, error responses
2. **Security:** Auth requirements, rate limiting, input validation
3. **Documentation:** Are endpoints documented? Examples provided?

## Step 4: Implementation Feasibility

1. **Complexity:** Is the plan over-engineered? Under-engineered?
2. **Dependencies:** Are there external dependencies that could block?
3. **Risk areas:** What's the hardest part to implement correctly?

## Step 5: Testing Strategy

1. **Coverage:** What needs tests? Unit, integration, E2E?
2. **Edge cases:** Are error paths and boundary conditions covered?
3. **Test data:** Is there a strategy for fixtures and test data?

## Step 6: Output

```
ENGINEERING PLAN REVIEW
═══════════════════════════════
Plan: {title}

Architecture: {score}/10 — {summary}
Data model:   {score}/10 — {summary}
API design:   {score}/10 — {summary}
Feasibility:  {score}/10 — {summary}
Testing:      {score}/10 — {summary}

Critical gaps:
1. {most critical missing consideration}
2. {second critical gap}

Recommendations:
1. {highest priority suggestion}
2. {second priority}
```

---

## Important Rules

- **Be specific about problems.** "The data model might have issues" is not helpful. "The users table has no unique constraint on email, allowing duplicate accounts" is.
- **Don't redesign.** Review the plan, don't rewrite it. Suggest improvements, don't dictate architecture.
- **Check feasibility, not perfection.** A plan doesn't need to be optimal — it needs to work.

---

## Completion Status

- **DONE** — Engineering review complete
- **DONE_WITH_CONCERNS** — Review completed but major concerns remain
