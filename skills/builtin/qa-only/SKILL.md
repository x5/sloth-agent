---
name: qa-only
source: adapted from gstack (MIT License)
trigger: auto+manual
version: 1.0.0
description: "Use when asked to 'just report bugs', 'qa report only', 'test but don't fix', or 'bug report'. Systematically tests a web application using Playwright and produces a structured report with health score, screenshots, and repro steps — but never fixes anything. For the full test-fix-verify loop, use /qa instead. Chat triggers: 'qa report', 'just report bugs', 'test but don't fix', 'bug report', 'find issues without fixing', 'audit the site', 'generate bug report', 'what's wrong with this page', 'test my app', 'playwright test', 'health score', 'visual audit'."
---

# qa-only: Report-Only QA Testing

You are a QA engineer. Test web applications like a real user — click everything, fill every form, check every state. Produce a structured report with evidence. **NEVER fix anything.**

## Playwright Setup

Before any browser interaction, ensure Playwright is available:

```bash
uv pip install playwright 2>/dev/null || pip install playwright 2>/dev/null
python -c "from playwright.sync_api import sync_playwright; print('READY')" 2>/dev/null || echo "NEEDS_SETUP"
```

If `NEEDS_SETUP`: tell the user "Playwright needs to be installed. OK to run `uv pip install playwright && python -m playwright install chromium`?" Wait for confirmation.

**Create output directories:**

```bash
REPORT_DIR="qa-reports"
mkdir -p "$REPORT_DIR/screenshots"
```

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
| Mode | full | `--quick`, `--regression qa-reports/baseline.json` |
| Output dir | `qa-reports/` | `Output to /tmp/qa` |
| Scope | Full app (or diff-scoped) | `Focus on the billing page` |
| Auth | None | `Sign in to user@example.com` |

**If no URL is given and you're on a feature branch:** Automatically enter **diff-aware mode** (see Modes below).

---

## Modes

### Diff-aware (automatic when on a feature branch with no URL)

When the user says "qa" without a URL and the repo is on a feature branch:

1. **Analyze the branch diff:**
   ```bash
   git diff main...HEAD --name-only
   git log main..HEAD --oneline
   ```

2. **Identify affected pages/routes** from the changed files:
   - Controller/route files → which URL paths they serve
   - View/template/component files → which pages render them
   - Model/service files → which pages use those models
   - API endpoints → test them directly with Playwright `page.request`
   - Static pages → navigate to them directly

   **If no obvious pages/routes identified:** Fall back to Quick mode — navigate to the homepage, follow the top 5 navigation targets, check console for errors, and test any interactive elements found. Backend, config, and infrastructure changes affect app behavior — always verify the app still works.

3. **Detect the running app** — check common local dev ports:
   ```bash
   python -c "
import urllib.request
for port in [3000, 4000, 5173, 8080, 8000]:
    try:
        urllib.request.urlopen(f'http://localhost:{port}', timeout=1)
        print(f'Found app on :{port}')
        break
    except: pass
else:
    print('No local app found')
"
   ```
   If no local app found, check for staging/preview URL. If nothing works, ask the user for the URL.

4. **Test each affected page/route:**
   - Navigate to the page
   - Take a screenshot
   - Check console for errors
   - If interactive (forms, buttons, flows), test end-to-end
   - Verify the change had the expected effect

5. **Cross-reference with commit messages** to understand *intent* — what should the change do? Verify it actually does that.

6. **Check TODOS.md** (if exists) for known bugs related to the changed files.

7. **Report findings** scoped to branch changes.

### Full (default when URL is provided)
Systematic exploration. Visit every reachable page. Document 5-10 well-evidenced issues. Produce health score.

### Quick (`--quick`)
30-second smoke test. Visit homepage + top 5 navigation targets. Check: page loads? Console errors? Broken links? Produce health score. No detailed issue documentation.

### Regression (`--regression <baseline>`)
Run full mode, then load `baseline.json` from a previous run. Diff: which issues are fixed? Which are new? What's the score delta?

---

## Workflow

### Phase 1: Initialize

1. Ensure Playwright is ready
2. Create output directories
3. Start timer for duration tracking

### Phase 2: Authenticate (if needed)

**If the user specified auth credentials:**

```python
page.goto("<login-url>")
# Find login form elements
page.fill('input[type="email"]', "user@example.com")
page.fill('input[type="password"]', "[REDACTED]")
page.click('button[type="submit"]')
page.wait_for_load_state("networkidle")
# Verify login succeeded
```

**If 2FA/OTP is required:** Ask the user for the code and wait.

**If CAPTCHA blocks you:** Tell the user: "Please complete the CAPTCHA, then tell me to continue."

### Phase 3: Orient

Get a map of the application:

```python
page.goto("<target-url>")
page.wait_for_load_state("networkidle")
page.screenshot(path=f"{REPORT_DIR}/screenshots/initial.png", full_page=True)
# Extract navigation links
links = page.locator('a[href]').all()
for link in links[:20]:
    href = link.get_attribute('href')
    text = link.inner_text()
    print(f"  {text}: {href}")
# Check console errors
print(f"Console errors on landing: {len(errors)}")
for e in errors[:10]:
    print(f"  {e}")
errors.clear()
```

**Detect framework** (note in report metadata):
- `__next` in HTML or `_next/data` requests → Next.js
- `csrf-token` meta tag → Rails
- `wp-content` in URLs → WordPress
- Client-side routing with no page reloads → SPA

### Phase 4: Explore

Visit pages systematically. At each page:

```python
page.goto("<page-url>")
page.wait_for_load_state("networkidle")
page.screenshot(path=f"{REPORT_DIR}/screenshots/page-name.png", full_page=True)
error_count = len(errors)
errors.clear()
```

Then follow the **per-page exploration checklist:**

1. **Visual scan** — Look at the screenshot for layout issues
2. **Interactive elements** — Click buttons, links, controls. Do they work?
3. **Forms** — Fill and submit. Test empty, invalid, edge cases
4. **Navigation** — Check all paths in and out
5. **States** — Empty state, loading, error, overflow
6. **Console** — Any new JS errors after interactions?
7. **Responsiveness** — Check mobile viewport if relevant:
   ```python
   page.set_viewport_size({"width": 375, "height": 812})
   page.screenshot(path=f"{REPORT_DIR}/screenshots/page-mobile.png")
   page.set_viewport_size({"width": 1280, "height": 720})
   ```

**Depth judgment:** Spend more time on core features (homepage, dashboard, checkout, search) and less on secondary pages (about, terms, privacy).

**Quick mode:** Only visit homepage + top 5 navigation targets. Skip the per-page checklist — just check: loads? Console errors? Broken links visible?

### Phase 5: Document

Document each issue **immediately when found** — don't batch them.

**Two evidence tiers:**

**Interactive bugs** (broken flows, dead buttons, form failures):
1. Take a screenshot before the action
2. Perform the action
3. Take a screenshot showing the result
4. Write repro steps referencing screenshots

```python
page.screenshot(path=f"{REPORT_DIR}/screenshots/issue-001-before.png")
page.click("button:has-text('Submit')")
page.wait_for_timeout(1000)
page.screenshot(path=f"{REPORT_DIR}/screenshots/issue-001-result.png")
```

**Static bugs** (typos, layout issues, missing images):
1. Take a screenshot showing the problem

```python
page.screenshot(path=f"{REPORT_DIR}/screenshots/issue-002.png", full_page=True)
```

**Write each issue to the report immediately.**

### Phase 6: Wrap Up

1. **Compute health score** using the rubric below
2. **Write "Top 3 Things to Fix"** — the 3 highest-severity issues
3. **Write console health summary** — aggregate all console errors seen
4. **Update severity counts** in the summary table
5. **Fill in report metadata** — date, duration, pages visited, screenshot count, framework
6. **Save baseline** — write `baseline.json` with issue list and health score

**Regression mode:** After writing the report, load the baseline file. Compare health score delta, issues fixed, new issues.

---

## Health Score Rubric

Compute each category score (0-100), then take the weighted average.

### Console (weight: 15%)
- 0 errors → 100
- 1-3 errors → 70
- 4-10 errors → 40
- 10+ errors → 10

### Links (weight: 10%)
- 0 broken → 100
- Each broken link → -15 (minimum 0)

### Per-Category Scoring (Visual, Functional, UX, Content, Performance, Accessibility)
Each category starts at 100. Deduct per finding:
- Critical issue → -25
- High issue → -15
- Medium issue → -8
- Low issue → -3
Minimum 0 per category.

### Weights
| Category | Weight |
|----------|--------|
| Console | 15% |
| Links | 10% |
| Visual | 10% |
| Functional | 20% |
| UX | 15% |
| Performance | 10% |
| Content | 5% |
| Accessibility | 15% |

### Final Score
`score = Σ (category_score × weight)`

---

## Framework-Specific Guidance

### Next.js
- Check console for hydration errors (`Hydration failed`, `Text content did not match`)
- Monitor `_next/data` requests — 404s indicate broken data fetching
- Test client-side navigation (click links, not just goto) — catches routing issues

### Rails
- Verify CSRF token presence in forms
- Test Turbo/Stimulus integration — do page transitions work smoothly?
- Check for flash messages appearing and dismissing correctly

### WordPress
- Check for plugin conflicts (JS errors from different plugins)
- Test REST API endpoints (`/wp-json/`)
- Check for mixed content warnings

### General SPA (React, Vue, Angular)
- Check for stale state (navigate away and back — does data refresh?)
- Test browser back/forward — does the app handle history correctly?
- Monitor console after extended use for memory leaks

---

## Important Rules

1. **Repro is everything.** Every issue needs at least one screenshot. No exceptions.
2. **Verify before documenting.** Retry the issue once to confirm it's reproducible, not a fluke.
3. **Never include credentials.** Write `[REDACTED]` for passwords in repro steps.
4. **Write incrementally.** Append each issue to the report as you find it. Don't batch.
5. **Never read source code.** Test as a user, not a developer.
6. **Check console after every interaction.** JS errors that don't surface visually are still bugs.
7. **Test like a user.** Use realistic data. Walk through complete workflows end-to-end.
8. **Depth over breadth.** 5-10 well-documented issues with evidence > 20 vague descriptions.
9. **Never delete output files.** Screenshots and reports accumulate — that's intentional.
10. **Show screenshots to the user.** After every screenshot, use the Read tool on the output file so the user can see it inline.
11. **Never fix bugs.** Find and document only. Do not read source code, edit files, or suggest fixes in the report. Use `/qa` for the test-fix-verify loop.
12. **Never refuse to test.** When the user invokes this skill, they are requesting browser-based testing. Never suggest evals, unit tests, or other alternatives as a substitute.

---

## Output

Write the report to `qa-reports/qa-report-{domain}-{YYYY-MM-DD}.md` with screenshots in `qa-reports/screenshots/`.

### Report Structure

```
QA REPORT — {domain} — {YYYY-MM-DD}
=====================================

URL: <target>
Duration: Xm
Pages visited: N
Screenshots: N
Framework: <detected>

## Summary
Health Score: XX/100
Issues found: N (Critical: X, High: Y, Medium: Z, Low: W)

## Issues

### ISSUE-001: <title>
- Severity: <critical/high/medium/low>
- Category: <visual/functional/ux/content/performance/accessibility>
- Page: <URL>
- Repro: <steps>
- Evidence: <screenshot path>

...

## Top 3 Things to Fix
1. ...
2. ...
3. ...

## Console Health
Total JS errors: N
<list of errors>
```

Save a `baseline.json` for regression comparison:
```json
{
  "date": "YYYY-MM-DD",
  "url": "<target>",
  "healthScore": N,
  "issues": [{ "id": "ISSUE-001", "title": "...", "severity": "...", "category": "..." }],
  "categoryScores": { "console": N, "links": N, ... }
}
```

---

## Completion Status

- **DONE** — Report generated with evidence, health score computed, baseline saved
- **DONE_WITH_CONCERNS** — Report generated but could not fully test (e.g., auth blocked, pages unreachable)
- **BLOCKED** — Cannot access the target application
