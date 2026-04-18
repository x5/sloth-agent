---
name: canary
source: adapted from gstack (MIT License)
trigger: auto+manual
version: 1.0.0
description: "Post-deploy visual monitoring. Watches the live app after a deploy, takes screenshots, checks console errors, compares against baselines. Use when asked to 'canary', 'monitor production', 'check deploy health', 'verify the site after deploy', 'is the deploy working', 'check for regressions after deploy', 'monitor the release', 'visual health check', or 'did the deploy break anything'."
---

# canary: Post-Deploy Visual Monitor

Watch the live app after a deploy. Take screenshots, check console errors, compare against baselines. You are the safety net between "shipped" and "verified."

## Playwright Setup

```bash
uv pip install playwright 2>/dev/null || pip install playwright 2>/dev/null
python -m playwright install chromium 2>/dev/null
```

## Parameters

| Parameter | Default | Override |
|-----------|---------|----------|
| URL | (required) | `https://myapp.com` |
| Duration | 10 minutes | `--duration 5m` |
| Mode | continuous | `--baseline`, `--quick` |
| Pages | auto-discover | `--pages /,/dashboard` |

---

## Phase 1: Setup

```bash
mkdir -p canary-reports/baselines
mkdir -p canary-reports/screenshots
```

---

## Phase 2: Baseline Capture (--baseline mode)

Run BEFORE deploying to capture the current state.

For each page:

```python
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1280, "height": 720})
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

    page.goto("<page-url>")
    page.wait_for_load_state("networkidle")
    page.screenshot(path="canary-reports/baselines/<page-name>.png", full_page=True)
    console_errors = len(errors)
    browser.close()
```

Save baseline manifest to `canary-reports/baseline.json`:

```json
{
  "url": "<url>",
  "timestamp": "<ISO>",
  "pages": {
    "/": {
      "screenshot": "baselines/home.png",
      "console_errors": 0
    }
  }
}
```

Then STOP: "Baseline captured. Deploy your changes, then run `/canary <url>` to monitor."

---

## Phase 3: Page Discovery

If no `--pages` specified, auto-discover:

```python
page.goto("<url>")
page.wait_for_load_state("networkidle")
links = page.locator('a[href]').all()
for link in links[:10]:
    href = link.get_attribute('href')
    text = link.inner_text()
    print(f"  {text}: {href}")
```

Present discovered pages via AskUserQuestion:

- A) Monitor these pages: [list]
- B) Add more pages
- C) Homepage only

---

## Phase 4: Health Check

For each page to monitor:

```python
page.goto("<page-url>")
page.wait_for_load_state("networkidle")
page.screenshot(path="canary-reports/screenshots/<page-name>.png", full_page=True)
console_errors = len(errors)
errors.clear()
```

Compare against baseline (if exists):
1. **Page load failure** → CRITICAL
2. **New console errors** → HIGH
3. **Visual differences** → MEDIUM (compare screenshots)

---

## Phase 5: Monitoring Loop

Perform 3-5 checks over the monitoring period. After each check, compare against baseline:

**Alert logic:**
- CRITICAL: Page won't load → notify user immediately
- HIGH: New console error → notify user
- MEDIUM: New visual issue → note in report
- Only alert on patterns that persist across 2+ consecutive checks

---

## Phase 6: Health Report

```
CANARY REPORT — [url]
═════════════════════
Duration:     [X minutes]
Pages:        [N monitored]
Checks:       [N performed]
Status:       [HEALTHY / DEGRADED / BROKEN]

Per-Page Results:
  Page            Status      Errors
  /               HEALTHY     0
  /dashboard      DEGRADED    2 new
  /settings       HEALTHY     0

Alerts:  [N] (X critical, Y high, Z medium)

VERDICT: [DEPLOY IS HEALTHY / DEPLOY HAS ISSUES]
```

Save to `canary-reports/canary-report-{date}.md`.

---

## Important Rules

- **Alert on changes, not absolutes.** Compare against baseline.
- **Screenshots are evidence.** Every alert includes a screenshot.
- **Transient tolerance.** Only alert on persistent patterns (2+ checks).
- **Baseline is king.** Without a baseline, canary is a health check.
- **Read-only.** Observe and report. Don't modify code unless asked.

---

## Completion Status

- **DONE** — Monitoring complete, deploy healthy
- **DONE_WITH_CONCERNS** — Issues found, reported to user
- **BLOCKED** — Cannot access the target URL
