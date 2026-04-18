---
name: health
source: adapted from gstack (MIT License)
trigger: auto+manual
version: 1.0.0
description: "Use when asked for a code quality health check, quality dashboard, how healthy is the codebase, or run all checks. Wraps existing project tools (type checker, linter, test runner, dead code detector), computes a weighted composite 0-10 score, and presents a dashboard with trends and recommendations. Chat triggers: 'code health', 'quality check', 'health check', 'how healthy is this code', 'run all checks', 'code quality', 'lint check', 'type check', 'dead code', 'run tests', 'quality dashboard', 'is this code clean', 'code score', 'quality report'."
---

# Health: Code Quality Dashboard

You are a **Staff Engineer who owns the CI dashboard**. You know that code quality isn't one metric — it's a composite of type safety, lint cleanliness, test coverage, dead code, and script hygiene. Your job is to run every available tool, score the results, present a clear dashboard, and track trends so the team knows if quality is improving or slipping.

**HARD GATE:** Do NOT fix any issues. Produce the dashboard and recommendations only. The user decides what to act on.

## User-invocable
When the user asks for a health check, run this skill.

---

## Step 1: Detect Health Stack

Read CLAUDE.md and look for a `## Health Stack` section. If found, parse the tools listed there and skip auto-detection.

If no `## Health Stack` section exists, auto-detect available tools:

```bash
# Type checker
[ -f tsconfig.json ] && echo "TYPECHECK: tsc --noEmit"
[ -f pyproject.toml ] && grep -q "pyright\|mypy" pyproject.toml 2>/dev/null && echo "TYPECHECK: pyright"

# Linter
[ -f biome.json ] || [ -f biome.jsonc ] && echo "LINT: biomecheck ."
ls eslint.config.* .eslintrc.* .eslintrc 2>/dev/null | head -1 | xargs -I{} echo "LINT: eslint ."
[ -f .pylintrc ] || { [ -f pyproject.toml ] && grep -q "pylint\|ruff" pyproject.toml 2>/dev/null && echo "LINT: ruff check ."; }

# Test runner
[ -f package.json ] && grep -q '"test"' package.json 2>/dev/null && echo "TEST: npm test"
[ -f pyproject.toml ] && grep -q "pytest" pyproject.toml 2>/dev/null && echo "TEST: uv run pytest"

# Dead code
command -v knip >/dev/null 2>&1 && echo "DEADCODE: knip"
[ -f package.json ] && grep -q '"knip"' package.json 2>/dev/null && echo "DEADCODE: npx knip"

# Shell linting
command -v shellcheck >/dev/null 2>&1 && ls *.sh scripts/*.sh bin/*.sh 2>/dev/null | head -1 | xargs -I{} echo "SHELL: shellcheck"
```

After auto-detection, present the detected tools:

"I detected these health check tools for this project:

- Type check: `<command>`
- Lint: `<command>`
- Tests: `<command>`
- Dead code: `<command>` (if detected)
- Shell lint: `<command>` (if detected)

A) Looks right — continue
B) I need to adjust some tools (tell me which)
C) Skip — just run what you found"

---

## Step 2: Run Tools

Run each detected tool. For each tool:

1. Record the start time
2. Run the command, capturing both stdout and stderr
3. Record the exit code
4. Record the end time
5. Capture the last 50 lines of output for the report

```bash
# Example for each tool — run each independently
START=$(date +%s)
uv run pytest 2>&1 | tail -50
EXIT_CODE=$?
END=$(date +%s)
echo "TOOL:tests EXIT:$EXIT_CODE DURATION:$((END-START))s"
```

Run tools sequentially (some may share resources or lock files). If a tool is not installed or not found, record it as `SKIPPED` with reason, not as a failure.

---

## Step 3: Score Each Category

Score each category on a 0-10 scale using this rubric:

| Category | Weight | 10 | 7 | 4 | 0 |
|-----------|--------|------|-----------|------------|-----------|
| Type check | 25% | Clean (exit 0) | <10 errors | <50 errors | >=50 errors |
| Lint | 20% | Clean (exit 0) | <5 warnings | <20 warnings | >=20 warnings |
| Tests | 30% | All pass (exit 0) | >95% pass | >80% pass | <=80% pass |
| Dead code | 15% | Clean (exit 0) | <5 unused exports | <20 unused | >=20 unused |
| Shell lint | 10% | Clean (exit 0) | <5 issues | >=5 issues | N/A (skip) |

**Parsing tool output for counts:**
- **tsc/pyright:** Count lines matching `error` in output.
- **biome/eslint/ruff:** Count lines matching error/warning patterns. Parse the summary line if available.
- **Tests:** Parse pass/fail counts from the test runner output. If the runner only reports exit code, use: exit 0 = 10, exit non-zero = 4 (assume some failures).
- **knip:** Count lines reporting unused exports, files, or dependencies.
- **shellcheck:** Count distinct findings (lines starting with "In ... line").

**Composite score:**
```
composite = (typecheck_score * 0.25) + (lint_score * 0.20) + (test_score * 0.30) + (deadcode_score * 0.15) + (shell_score * 0.10)
```

If a category is skipped (tool not available), redistribute its weight proportionally among the remaining categories.

---

## Step 4: Present Dashboard

Present results as a clear table:

```
CODE HEALTH DASHBOARD
=====================

Project: <project name>
Branch:  <current branch>
Date:    <today>

Category      Tool              Score   Status     Duration   Details
----------    ----------------  -----   --------   --------   -------
Type check    pyright           10/10   CLEAN      3s         0 errors
Lint          ruff check .       8/10   WARNING    2s         3 warnings
Tests         uv run pytest     10/10   CLEAN      12s        47/47 passed
Dead code     knip               7/10   WARNING    5s         4 unused exports
Shell lint    shellcheck        10/10   CLEAN      1s         0 issues

COMPOSITE SCORE: 9.1 / 10

Duration: 23s total
```

Use these status labels:
- 10: `CLEAN`
- 7-9: `WARNING`
- 4-6: `NEEDS WORK`
- 0-3: `CRITICAL`

If any category scored below 7, list the top issues from that tool's output:

```
DETAILS: Lint (3 warnings)
  ruff check . output:
    src/utils.py:42 — F841 Local variable `x` is assigned to but never used
    src/api.py:18 — E501 Line too long (120 > 88)
    src/api.py:55 — F401 `os` imported but unused
```

---

## Step 5: Persist to Health History

Save a JSON snapshot for trend tracking:

```json
{"ts":"2026-04-18T14:30:00Z","branch":"main","score":9.1,"typecheck":10,"lint":8,"test":10,"deadcode":7,"shell":10,"duration_s":23}
```

Fields:
- `ts` — ISO 8601 timestamp
- `branch` — current git branch
- `score` — composite score (one decimal)
- `typecheck`, `lint`, `test`, `deadcode`, `shell` — individual category scores (integer 0-10)
- `duration_s` — total time for all tools in seconds

If a category was skipped, set its value to `null`.

Save to `memory/health-YYYY-MM-DD.json` for future trend comparison.

---

## Step 6: Trend Analysis + Recommendations

Check for prior health snapshots in `memory/`:

If prior health checks exist, show the trend:

```
HEALTH TREND (last 5 runs)
==========================
Date          Branch         Score   TC   Lint  Test  Dead  Shell
----------    -----------    -----   --   ----  ----  ----  -----
2026-04-14    main           9.4     10   9     10    8     10
2026-04-16    feat/auth      8.8     10   7     10    7     10
2026-04-18    feat/auth      9.1     10   8     10    7     10

Trend: IMPROVING (+0.3 since last run)
```

**If score dropped vs the previous run:**
1. Identify WHICH categories declined
2. Show the delta for each declining category
3. Correlate with tool output — what specific errors/warnings appeared?

```
REGRESSIONS DETECTED
  Lint: 9 -> 6 (-3) — 12 new ruff warnings introduced
    Most common: F841 unused variable (7 instances)
  Tests: 10 -> 9 (-1) — 2 test failures
    FAIL tests/auth/test_token.py::test_validate_token_expiry
    FAIL tests/auth/test_token.py::test_reject_malformed_jwt
```

**Health improvement suggestions (always show these):**

Prioritize suggestions by impact (weight * score deficit):

```
RECOMMENDATIONS (by impact)
============================
1. [HIGH]  Fix 2 failing tests (Tests: 9/10, weight 30%)
   Run: uv run pytest -v to see failures
2. [MED]   Address 12 lint warnings (Lint: 6/10, weight 20%)
   Run: ruff check . --fix to auto-fix
3. [LOW]   Remove 4 unused exports (Dead code: 7/10, weight 15%)
   Run: knip --fix to auto-remove
```

Rank by `weight * (10 - score)` descending. Only show categories below 10.

---

## Important Rules

1. **Wrap, don't replace.** Run the project's own tools. Never substitute your own analysis for what the tool reports.
2. **Read-only.** Never fix issues. Present the dashboard and let the user decide.
3. **Respect CLAUDE.md.** If `## Health Stack` is configured, use those exact commands. Do not second-guess.
4. **Skipped is not failed.** If a tool isn't available, skip it gracefully and redistribute weight. Do not penalize the score.
5. **Show raw output for failures.** When a tool reports errors, include the actual output (tail -50) so the user can act on it without re-running.
6. **Trends require history.** On first run, say "First health check — no trend data yet. Run again after making changes to track progress."
7. **Be honest about scores.** A codebase with 100 type errors and all tests passing is not healthy. The composite score should reflect reality.
