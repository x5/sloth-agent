---
name: test-driven-development
source: builtin
trigger: manual
version: 1.0.0
description: RED-GREEN-REFACTOR cycle for test-driven development
---

# Test-Driven Development

Follow the RED-GREEN-REFACTOR cycle:

## 1. RED — Write a Failing Test
- Write the smallest test that describes the next behavior
- Run it and confirm it fails (compilation error or assertion failure)

## 2. GREEN — Make It Pass
- Write the minimum code to make the test pass
- Do not over-engineer; obvious implementation is fine
- If tempted to write complex logic, write another test first

## 3. REFACTOR — Clean Up
- With green tests, improve code quality
- Extract methods, rename variables, remove duplication
- Tests should still pass after each refactoring step

## Rules
- Never write production code without a failing test
- Do not write more production code than needed to pass the current test
- Refactor only when all tests are green
- Keep tests fast (< 1s each), isolated, and deterministic
