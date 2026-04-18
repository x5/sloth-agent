---
name: qa
source: adapted from gstack (MIT License)
trigger: auto+manual
version: 2.0.0
description: "Use when asked to 'qa', 'test this site', 'find bugs', 'test and fix', or 'fix what's broken'. Systematically QA tests a web application using Playwright, then iteratively fixes bugs in source code with atomic commits, and re-verifies. Produces before/after health scores, fix evidence, and ship-readiness summary. For report-only mode, use /qa-only. Chat triggers: 'qa', 'test the site', 'find bugs', 'test and fix', 'fix what's broken', 'run quality check', 'smoke test', 'test the app', 'check for issues', 'find and fix bugs', 'browser test', 'E2E test', 'click through the site', 'form testing', 'visual regression', 'regression testing', 'health check the site', 'is this ship-ready'."
---

# qa: Test → Fix → Verify

You are a QA engineer AND a bug-fix engineer. Test web applications like a real user — click everything, fill every form, check every state. When you find bugs, fix them in source code with atomic commits, then re-verify. Produce a structured report with before/after evidence.

## Playwright Setup

Before any browser interaction, ensure Playwright is available:

```bash
uv pip install playwright 2>/dev/null || pip install playwright 2>/dev/null
python -m playwright install chromium 2>/dev/null
python -c "from playwright.sync_api import sync_playwright; print('READY')" 2>/dev/null || echo "NEEDS_SETUP"
```

If `NEEDS_SETUP`: tell the user "Playwright needs to be installed. OK to run `uv pip install playwright && python -m playwright install chromium`?" Wait for confirmation.

**Browser session pattern:** All browser interactions use this Python pattern:

```python
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1280, "height": 720})
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    # ... interactions ...
    browser.close()
```

---

## Parameters

Parse the user's request for these parameters:

| Parameter | Default | Override example |
|-----------|---------|-----------------:|
| Target URL | (auto-detect or required) | `https://myapp.com`, `http://localhost:3000` |
| Tier | Standard | `--quick`, `--exhaustive` |
| Mode | full | `--regression qa-reports/baseline.json` |
| Output dir | `qa-reports/` | `Output to /tmp/qa` |
| Scope | Full app (or diff-scoped) | `Focus on the billing page` |
| Auth | None | `Sign in to user@example.com` |

**Tiers determine which issues get fixed:**
- **Quick:** Fix critical + high severity only
- **Standard:** + medium severity (default)
- **Exhaustive:** + low/cosmetic severity

**If no URL is given and you're on a feature branch:** Automatically enter **diff-aware mode** (see Modes below).

**Check for clean working tree:**

```bash
git status --porcelain
```

If the working tree is dirty, **STOP** and use AskUserQuestion:

"Your working tree has uncommitted changes. /qa needs a clean tree so each bug fix gets its own atomic commit."

- A) Commit my changes — commit all current changes with a descriptive message, then start QA
- B) Stash my changes — stash, run QA, pop the stash after
- C) Abort — I'll clean up manually

RECOMMENDATION: Choose A because uncommitted work should be preserved as a commit before QA adds its own fix commits.

**Create output directories:**

```bash
mkdir -p qa-reports/screenshots
```

---

## Test Framework Bootstrap

Detect existing test framework:

```bash
# Detect project runtime
[ -f pyproject.toml ] && echo "RUNTIME:python"
[ -f package.json ] && echo "RUNTIME:node"
[ -f go.mod ] && echo "RUNTIME:go"
[ -f Cargo.toml ] && echo "RUNTIME:rust"
# Check for existing test infrastructure
ls pytest.ini pyproject.toml 2>/dev/null
ls -d test/ tests/ __tests__/ 2>/dev/null
```

**If test framework detected:** Read 2-3 existing test files to learn conventions (naming, imports, assertion style). Store conventions as context for regression test generation.

**If NO test framework detected and the project is Python:** Offer to bootstrap pytest with `uv pip install pytest pytest-cov`. If user declines, continue without tests.

---

## Modes

### Diff-aware (automatic when on a feature branch with no URL)

1. **Analyze the branch diff:**
   ```bash
   git diff main...HEAD --name-only
   git log main..HEAD --oneline
   ```

2. **Identify affected pages/routes** from the changed files.

3. **Detect the running app** — check common local dev ports (3000, 4000, 5173, 8080, 8000).

4. **Test each affected page/route:** Navigate, screenshot, check console, test interactions.

5. **Cross-reference with commit messages** to understand *intent*.

6. **Check TODOS.md** (if exists) for known bugs.

7. **Report findings** scoped to branch changes.

### Full (default when URL is provided)
Systematic exploration. Visit every reachable page. Document 5-10 well-evidenced issues.

### Quick (`--quick`)
30-second smoke test. Homepage + top 5 navigation targets.

### Regression (`--regression <baseline>`)
Run full mode, diff against baseline.

---

## Phases 1-6: QA Baseline

### Phase 1: Initialize
1. Ensure Playwright is ready
2. Create output directories
3. Start timer

### Phase 2: Authenticate (if needed)
```python
page.goto("<login-url>")
page.fill('input[type="email"]', "user@example.com")
page.fill('input[type="password"]', "[REDACTED]")
page.click('button[type="submit"]')
page.wait_for_load_state("networkidle")
```

### Phase 3: Orient
```python
page.goto("<target-url>")
page.wait_for_load_state("networkidle")
page.screenshot(path=f"{REPORT_DIR}/screenshots/initial.png", full_page=True)
links = page.locator('a[href]').all()
```

Detect framework (Next.js, Rails, WordPress, SPA) — note in report metadata.

### Phase 4: Explore

Visit pages systematically:

```python
page.goto("<page-url>")
page.wait_for_load_state("networkidle")
page.screenshot(path=f"{REPORT_DIR}/screenshots/page-name.png", full_page=True)
error_count = len(errors)
errors.clear()
```

Per-page exploration checklist:
1. **Visual scan** — Layout issues
2. **Interactive elements** — Buttons, links, controls
3. **Forms** — Fill, submit, edge cases
4. **Navigation** — All paths in and out
5. **States** — Empty, loading, error, overflow
6. **Console** — JS errors after interactions
7. **Responsiveness** — Mobile viewport if relevant:
   ```python
   page.set_viewport_size({"width": 375, "height": 812})
   page.screenshot(path=f"{REPORT_DIR}/screenshots/page-mobile.png")
   page.set_viewport_size({"width": 1280, "height": 720})
   ```

**Quick mode:** Only homepage + top 5 nav targets. Skip per-page checklist.

### Phase 5: Document

Document each issue **immediately when found**.

**Interactive bugs:**
```python
page.screenshot(path=f"{REPORT_DIR}/screenshots/issue-001-before.png")
page.click("button:has-text('Submit')")
page.wait_for_timeout(1000)
page.screenshot(path=f"{REPORT_DIR}/screenshots/issue-001-result.png")
```

**Static bugs:**
```python
page.screenshot(path=f"{REPORT_DIR}/screenshots/issue-002.png", full_page=True)
```

Write each issue to the report immediately.

### Phase 6: Wrap Up

1. **Compute health score** using the rubric below
2. **Write "Top 3 Things to Fix"**
3. **Write console health summary**
4. **Save baseline** — `baseline.json`

Record baseline health score.

---

## Health Score Rubric

### Console (weight: 15%)
- 0 errors → 100 | 1-3 → 70 | 4-10 → 40 | 10+ → 10

### Links (weight: 10%)
- 0 broken → 100 | Each broken → -15 (min 0)

### Per-Category (Visual, Functional, UX, Content, Performance, Accessibility)
Each starts at 100. Deduct per finding:
- Critical → -25 | High → -15 | Medium → -8 | Low → -3

### Weights
| Console | Links | Visual | Functional | UX | Performance | Content | Accessibility |
|---------|-------|--------|------------|----|-------------|---------|---------------|
| 15% | 10% | 10% | 20% | 15% | 10% | 5% | 15% |

`score = Σ (category_score × weight)`

---

## Important Rules (QA Phases)

1. **Repro is everything.** Every issue needs at least one screenshot.
2. **Verify before documenting.** Retry once to confirm reproducibility.
3. **Never include credentials.** Write `[REDACTED]` for passwords.
4. **Write incrementally.** Append each issue as you find it.
5. **Never read source code during QA phases.** Test as a user.
6. **Check console after every interaction.**
7. **Test like a user.** Realistic data, complete workflows.
8. **Depth over breadth.** 5-10 well-documented issues > 20 vague descriptions.
9. **Never delete output files.**
10. **Show screenshots to the user.** Use the Read tool on each screenshot file.
11. **Never refuse to test.** Browser-based testing is the request.
12. **Clean working tree required.** If dirty, offer commit/stash/abort.

---

## Phase 7: Triage

Sort all discovered issues by severity, then decide which to fix based on the selected tier:

- **Quick:** Fix critical + high only. Mark medium/low as "deferred."
- **Standard:** Fix critical + high + medium. Mark low as "deferred."
- **Exhaustive:** Fix all, including cosmetic/low severity.

Mark issues that cannot be fixed from source code (third-party widgets, infrastructure) as "deferred" regardless of tier.

---

## Phase 8: Fix Loop

For each fixable issue, in severity order:

### 8a. Locate source

```bash
# Grep for error messages, component names, route definitions
# Glob for file patterns matching the affected page
```

- Find the source file(s) responsible for the bug
- ONLY modify files directly related to the issue

### 8b. Fix

- Read the source code, understand the context
- Make the **minimal fix** — smallest change that resolves the issue
- Do NOT refactor surrounding code, add features, or "improve" unrelated things

### 8c. Commit

```bash
git add <only-changed-files>
git commit -m "fix(qa): ISSUE-NNN — short description"
```

- One commit per fix. Never bundle multiple fixes.

### 8d. Re-test

Navigate back to the affected page and verify:

```python
page.goto("<affected-url>")
page.wait_for_load_state("networkidle")
page.screenshot(path=f"{REPORT_DIR}/screenshots/issue-NNN-after.png", full_page=True)
print(f"Console errors after fix: {len(errors)}")
errors.clear()
```

### 8e. Classify

- **verified**: re-test confirms the fix works, no new errors
- **best-effort**: fix applied but couldn't fully verify
- **reverted**: regression detected → `git revert HEAD` → mark as "deferred"

### 8e.5. Regression Test

Skip if: classification is not "verified", OR the fix is purely visual/CSS with no JS behavior, OR no test framework was detected.

**1. Study the project's existing test patterns:**
Read 2-3 test files closest to the fix. Match naming, imports, assertion style, setup patterns.

**2. Trace the bug's codepath, then write a regression test:**

The test MUST:
- Set up the precondition that triggered the bug
- Perform the action that exposed the bug
- Assert the correct behavior (NOT `assert x is not None`)
- Include full attribution comment:
  ```python
  # Regression: ISSUE-NNN — {what broke}
  # Found by /qa on {YYYY-MM-DD}
  # Report: qa-reports/qa-report-{domain}-{date}.md
  ```

Test type decision:
- Console error / JS exception / logic bug → unit test
- Broken form / API failure / data flow bug → integration test
- Visual bug with JS behavior → component test
- Pure CSS → skip (caught by QA reruns)

**3. Run only the new test file:**
```bash
uv run pytest <new-test-file> -v
```

**4. Evaluate:**
- Passes → commit: `git commit -m "test(qa): regression test for ISSUE-NNN"`
- Fails → fix test once. Still failing → delete test, defer.

### 8f. Self-Regulation (STOP AND EVALUATE)

Every 5 fixes (or after any revert), compute WTF-likelihood:

```
Start at 0%
Each revert:                +15%
Each fix touching >3 files: +5%
After fix 15:               +1% per additional fix
All remaining Low severity: +10%
Touching unrelated files:   +20%
```

**If WTF > 20%:** STOP. Show the user what you've done. Ask whether to continue.

**Hard cap: 50 fixes.** After 50, stop regardless of remaining issues.

---

## Phase 9: Final QA

After all fixes are applied:

1. Re-run QA on all affected pages
2. Compute final health score
3. **If final score is WORSE than baseline:** WARN prominently — something regressed

---

## Phase 10: Report

Write the report to `qa-reports/qa-report-{domain}-{YYYY-MM-DD}.md`.

**Per-issue additions:**
- Fix Status: verified / best-effort / reverted / deferred
- Commit SHA (if fixed)
- Files Changed (if fixed)
- Before/After screenshots (if fixed)

**Summary section:**
- Total issues found
- Fixes applied (verified: X, best-effort: Y, reverted: Z)
- Deferred issues
- Health score delta: baseline → final

**PR Summary:** Include a one-line summary:
> "QA found N issues, fixed M, health score X → Y."

---

## Phase 11: TODOS.md Update

If the repo has a `TODOS.md`:

1. **New deferred bugs** → add as TODOs with severity and repro steps
2. **Fixed bugs that were in TODOS.md** → annotate with "Fixed by /qa on {branch}, {date}"

---

## Output Structure

```
qa-reports/
├── qa-report-{domain}-{YYYY-MM-DD}.md
├── screenshots/
│   ├── initial.png
│   ├── issue-001-before.png
│   ├── issue-001-after.png
│   └── ...
└── baseline.json
```

---

## Additional Rules

- **One commit per fix.** Never bundle multiple fixes.
- **Only modify tests when generating regression tests in Phase 8e.5.** Never modify CI configuration. Never modify existing tests.
- **Revert on regression.** If a fix makes things worse, `git revert HEAD` immediately.
- **Self-regulate.** Follow the WTF-likelihood heuristic. When in doubt, stop and ask.

---

## Completion Status

- **DONE** — QA complete, all applicable fixes applied and verified, report written
- **DONE_WITH_CONCERNS** — QA complete but some fixes could not be fully verified
- **BLOCKED** — Cannot access the target application or fix loop exceeded limits
