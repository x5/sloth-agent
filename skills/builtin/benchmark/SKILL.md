---
name: benchmark
source: adapted from gstack (MIT License)
trigger: auto+manual
version: 1.0.0
description: "Web performance benchmarking. Measures TTFB, FCP, LCP, bundle sizes, and resource loading. Compares against baselines to detect regressions. Use when asked to 'benchmark', 'performance audit', 'check page speed', 'how fast is this site', 'measure load time', 'performance regression', 'check bundle size', 'analyze page performance', 'why is this slow', 'measure web vitals', or 'LCP is too high'."
---

# benchmark: Performance Benchmarking

Measure web performance, compare against baselines, detect regressions.

## Playwright Setup

```bash
uv pip install playwright 2>/dev/null || pip install playwright 2>/dev/null
python -m playwright install chromium 2>/dev/null
```

## Parameters

| Parameter | Default | Override |
|-----------|---------|----------|
| URL | (required) | `https://myapp.com` |
| Mode | full | `--baseline`, `--quick`, `--diff`, `--trend` |
| Pages | auto-discover | `--pages /,/dashboard` |

---

## Phase 1: Setup

```bash
mkdir -p benchmark-reports/baselines
```

---

## Phase 2: Performance Data Collection

For each page, collect metrics:

```python
from playwright.sync_api import sync_playwright
import json

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1280, "height": 720})
    page = context.new_page()

    # Navigate and capture performance metrics
    page.goto("<page-url>")
    page.wait_for_load_state("networkidle")

    # Get navigation timing
    nav_timing = page.evaluate("""
        () => {
            const nav = performance.getEntriesByType('navigation')[0];
            return {
                ttfb: Math.round(nav.responseStart - nav.requestStart),
                dom_interactive: Math.round(nav.domInteractive - nav.startTime),
                dom_complete: Math.round(nav.domComplete - nav.startTime),
                full_load: Math.round(nav.loadEventEnd - nav.startTime)
            };
        }
    """)

    # Get paint timing (FCP, LCP)
    paint_metrics = page.evaluate("""
        () => {
            const paint = performance.getEntriesByType('paint');
            const fcp = paint.find(p => p.name === 'first-contentful-paint');
            return { fcp: fcp ? Math.round(fcp.startTime) : null };
        }
    """)

    # Get resource data
    resources = page.evaluate("""
        () => {
            const r = performance.getEntriesByType('resource');
            return {
                total_requests: r.length,
                total_transfer: r.reduce((s,e) => s + (e.transferSize||0), 0),
                scripts: r.filter(e => e.initiatorType === 'script')
                    .map(e => ({name: e.name.split('/').pop(), size: e.transferSize, duration: Math.round(e.duration)})),
                css: r.filter(e => e.initiatorType === 'css')
                    .map(e => ({name: e.name.split('/').pop(), size: e.transferSize})),
                slowest: r.sort((a,b) => b.duration - a.duration).slice(0, 10)
                    .map(e => ({name: e.name.split('/').pop(), type: e.initiatorType, size: e.transferSize, duration: Math.round(e.duration)}))
            };
        }
    """)

    browser.close()
```

---

## Phase 3: Baseline Capture (--baseline mode)

Save metrics to `benchmark-reports/baselines/baseline.json`:

```json
{
  "url": "<url>",
  "timestamp": "<ISO>",
  "pages": {
    "/": {
      "ttfb_ms": 120,
      "fcp_ms": 450,
      "dom_interactive_ms": 600,
      "dom_complete_ms": 1200,
      "full_load_ms": 1400,
      "total_requests": 42,
      "total_transfer_bytes": 1250000
    }
  }
}
```

---

## Phase 4: Comparison

If baseline exists, compare:

```
PERFORMANCE REPORT — [url]
══════════════════════════
Page: /
─────────────────────────────────────────────────────
Metric              Baseline    Current     Delta    Status
TTFB                120ms       135ms       +15ms    OK
FCP                 450ms       480ms       +30ms    OK
DOM Complete        1200ms      1350ms      +150ms   WARNING
Full Load           1400ms      2100ms      +700ms   REGRESSION
Total Requests      42          58          +16      WARNING
Transfer Size       1.2MB       1.8MB       +0.6MB   REGRESSION

Regression thresholds:
- Timing: >50% increase OR >500ms absolute = REGRESSION
- Timing: >20% increase = WARNING
- Requests: >30% increase = WARNING
```

---

## Phase 5: Slowest Resources

```
TOP 10 SLOWEST RESOURCES
═════════════════════════
#   Resource          Type      Size      Duration
1   vendor.js         script    320KB     480ms
2   main.js           script    250KB     320ms
3   hero.webp         img       180KB     280ms
```

---

## Phase 6: Performance Budget

```
PERFORMANCE BUDGET CHECK
════════════════════════
Metric              Budget      Actual      Status
FCP                 < 1.8s      0.48s       PASS
Total JS            < 500KB     720KB       FAIL
Total Transfer      < 2MB       1.8MB       WARNING
HTTP Requests       < 50        58          FAIL

Grade: B (4/6 passing)
```

---

## Phase 7: Save Report

Write to `benchmark-reports/benchmark-{date}.md` and `.json`.

---

## Important Rules

- **Baseline before changes.** Always capture baseline before making performance-affecting changes.
- **Compare against yourself.** Industry benchmarks are rough; your own baseline is precise.
- **Resource-level detail.** Don't just report totals — identify which specific resources are slow.
- **Trend over time.** Run benchmarks regularly to catch gradual degradation.

---

## Completion Status

- **DONE** — Benchmark complete, report generated
- **DONE_WITH_CONCERNS** — Benchmark completed but some metrics could not be collected
