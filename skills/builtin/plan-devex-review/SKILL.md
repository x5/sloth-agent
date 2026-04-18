---
name: plan-devex-review
source: adapted from gstack (MIT License)
trigger: auto+manual
version: 1.0.0
description: "Developer experience review of a development plan. Checks API ergonomics, onboarding path, error handling strategy, and extensibility. Use when asked to 'DX review of the plan' or 'is this developer-friendly'."
---

# plan-devex-review: Developer Experience Plan Review

Review the developer experience aspects of a plan.

## DX Evaluation Areas

1. **API Ergonomics:**
   - Are function/method names intuitive?
   - Are parameters ordered logically?
   - Are there sensible defaults?

2. **Onboarding Path:**
   - Can a new developer get started in <5 minutes?
   - Is setup documented?
   - Is there a "hello world" example?

3. **Error Strategy:**
   - Do errors explain what's wrong?
   - Do errors suggest how to fix it?
   - Are error codes documented?

4. **Extensibility:**
   - Can developers add features without modifying core code?
   - Are there hooks, plugins, or extension points?
   - Is the extension API documented?

5. **Testing Support:**
   - Is the plan testable?
   - Are test utilities included?
   - Is mocking supported?

6. **Debugging Support:**
   - Are there logging points?
   - Can developers inspect state?
   - Are there diagnostic endpoints?

## Output

```
DX PLAN REVIEW
═══════════════════════════════
Plan: {title}

API ergonomics:  {score}/10
Onboarding:      {score}/10
Error strategy:  {score}/10
Extensibility:   {score}/10
Testing:         {score}/10
Debugging:       {score}/10

Top DX concerns:
1. {most critical DX gap}
2. {second concern}
3. {third concern}
```

---

## Important Rules

- **Judge from a new developer's perspective.** You already know this code — they don't.
- **Errors are the #1 DX feature.** Good errors save hours of debugging.
- **Defaults matter more than options.** Most developers never change defaults.

---

## Completion Status

- **DONE** — DX plan review complete
