---
name: code-review
source: builtin
trigger: manual
version: 1.0.0
description: Code review checklist and best practices
---

# Code Review

Review code systematically using this checklist:

## Correctness
- Does the code do what it claims?
- Are edge cases handled? (empty input, null, boundary values, concurrent access)
- Are there race conditions or threading issues?
- Does error handling cover failure modes?

## Security
- Is user input validated/sanitized?
- Are secrets hardcoded?
- Is there SQL injection, XSS, or command injection risk?
- Are permissions and auth checks in place?

## Maintainability
- Are names clear and specific?
- Is the function short enough to understand at a glance?
- Is there unnecessary complexity? (over-engineering, premature optimization)
- Are there duplicated code blocks?

## Testing
- Are there tests for the happy path?
- Are edge cases tested?
- Do tests mock appropriately (not too much, not too little)?

## Performance
- Any N+1 queries or O(n²) loops?
- Are there memory leaks or unbounded caches?
- Is caching appropriate here?

## Review Process
- Review with the diff, not the full file — focus on what changed
- If the change is large, ask for it to be split
- Suggest improvements, don't demand — "Consider..." not "You must..."
- Approve when concerns are addressed, not when the code is perfect
