---
name: writing-plans
source: builtin
trigger: manual
version: 1.0.0
description: Micro-task decomposition for implementation planning
---

# Writing Plans

Break complex work into micro-tasks that can be implemented independently:

## Structure
- Start with a clear objective (one sentence)
- Decompose into 3-7 tasks, each independently testable
- Each task should be completable in one coding session
- Order tasks by dependency — no circular dependencies

## Task Format
```
Task N: [imperative verb] [object]
- Input: what exists before this task
- Output: what this task produces
- Acceptance: how to verify it works
```

## Rules
- Tasks should be small enough to implement without context switching
- If a task feels too large, split it
- Include tests as first-class tasks, not afterthoughts
- Mark which files each task will create or modify
- Leave implementation details flexible — the plan says *what*, not *how*

## Example
```
Task 1: Add user model with validation
- Input: None (new file)
- Output: src/models/user.py with User class
- Acceptance: pytest validates required fields and rejects invalid data
```
