---
name: systematic-debugging
source: builtin
trigger: manual
version: 1.0.0
description: Four-phase root cause analysis for bugs
---

# Systematic Debugging

Debug systematically in four phases:

## 1. Reproduce — Make It Happen Predictably
- Identify exact steps to reproduce
- Note environment, inputs, timing, state
- If intermittent, find the pattern — randomness is rarely truly random

## 2. Locate — Narrow Down the Source
- Use binary search: comment out halves, add logging, check assumptions
- Check the stack trace — the error location is rarely the root cause
- Look at what changed recently (git diff, recent commits)

## 3. Fix — Address the Root Cause
- Fix the cause, not the symptom
- If the fix is complex, add a regression test first
- Verify the fix with the original reproduction steps

## 4. Reflect — Prevent Recurrence
- Add the bug pattern to your mental model
- Consider: could a test have caught this earlier?
- Document unusual bugs for future reference

## Rules
- Never guess — verify each hypothesis with evidence
- One variable at a time
- If stuck for 30 minutes, ask for help or take a break
