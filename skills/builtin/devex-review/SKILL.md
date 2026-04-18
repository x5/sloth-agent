---
name: devex-review
source: adapted from gstack (MIT License)
trigger: auto+manual
version: 1.0.0
description: "Developer Experience review. Evaluates how easy it is for developers to use this project — setup, docs, error messages, onboarding, API design. Use when asked to 'devex review', 'developer experience', 'is this easy to use', 'onboarding review', 'how hard is it to contribute', 'developer usability audit', 'setup experience', 'error message quality', 'is the documentation good enough', or 'DX audit'."
---

# devex-review: Developer Experience Audit

Evaluate how easy it is for developers to use, contribute to, and build on this project.

## DX First Principles

Great developer experience means:
1. **Fast time-to-first-success** — Can a new developer get something working in <5 minutes?
2. **Clear error messages** — When things break, does the error explain what's wrong?
3. **Good defaults** — Does it work out of the box without configuration?
4. **Composable** — Can developers use parts without needing the whole?
5. **Predictable** — Does behavior match expectations?
6. **Forgiving** — Can mistakes be undone?
7. **Documented** — Is there a clear path from "I want to do X" to "I did X"?

## The Seven DX Characteristics

Evaluate each:

1. **Onboarding:** Setup instructions, first-run experience, TTHW (Time to Hello World)
2. **Documentation:** README, API docs, examples, tutorials
3. **Error handling:** Quality of error messages, debugging tools, logging
4. **API design:** Consistency, naming, discoverability, type safety
5. **Extensibility:** Plugin system, hooks, configuration, customization
6. **Testing:** Test framework, fixtures, mock data, CI integration
7. **Community:** Contribution guide, issue templates, PR templates, CODE_OF_CONDUCT

## DX Scoring Rubric (0-10)

| Score | Meaning |
|-------|---------|
| 10 | Best-in-class reference project |
| 8-9 | Excellent — minor polish needed |
| 6-7 | Good — some friction points |
| 4-5 | Mediocre — significant gaps |
| 2-3 | Poor — hostile to new developers |
| 0-1 | Unusable — no docs, no setup path |

## Evaluation Steps

### Step 1: TTHW (Time to Hello World)

Walk through the setup instructions as a brand new developer:

1. Clone the repo
2. Install dependencies
3. Run the project
4. Make a small change and see it work

Time each step mentally. Note any friction:
- Missing dependencies?
- Unclear instructions?
- Broken setup steps?
- Environment variables needed but undocumented?

### Step 2: Documentation Audit

Check each doc file:
- **README.md:** Does it explain what, why, and how to start?
- **CONTRIBUTING.md:** Is there a clear path for contributors?
- **ARCHITECTURE.md:** Can a new dev understand the structure?
- **API docs:** Are endpoints, parameters, and responses documented?

### Step 3: Error Message Quality

Grep for error messages:
```bash
grep -rn "raise\|throw\|panic\|console.error\|logger.error" --include="*.py" --include="*.ts" --include="*.go" | head -20
```

Evaluate: Do errors tell the user what's wrong and how to fix it?

### Step 4: API Design Review

Check for:
- Consistent naming conventions
- Clear parameter types
- Sensible defaults
- No surprising side effects

### Step 5: Testing DX

Check for:
- Easy test execution (`make test`, `uv run pytest`)
- Test fixtures and helpers
- Meaningful test output
- CI integration

## Findings Report

```
DX REVIEW REPORT
═══════════════════════════
Overall Score: N/10

Category Scores:
  Onboarding:     N/10
  Documentation:  N/10
  Error handling: N/10
  API design:     N/10
  Extensibility:  N/10
  Testing:        N/10
  Community:      N/10

TTHW: ~N minutes (target: <5)

Top 3 improvements:
1. {highest impact DX fix}
2. {second priority}
3. {third priority}
```

---

## Important Rules

- **Walk the path yourself.** Don't read docs and assume they work — try the setup.
- **New developer perspective.** Judge from the viewpoint of someone who's never seen this code.
- **Error messages are UX.** Bad errors are the #1 reason developers abandon tools.
- **TTHW is the north star.** If it takes >5 minutes to get started, everything else is secondary.

---

## Completion Status

- **DONE** — DX review complete, findings reported
- **DONE_WITH_CONCERNS** — Review completed but some areas could not be tested
