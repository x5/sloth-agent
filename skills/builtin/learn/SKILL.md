---
name: learn
source: adapted from gstack (MIT License)
trigger: auto+manual
version: 1.0.0
description: "Project learnings knowledge base. Search, view, prune, and export patterns, pitfalls, preferences, and architecture insights discovered during development. Use when asked to 'show learnings', 'search learnings', 'what have we learned', 'export learnings', 'what patterns do we know', 'search past solutions', 'what pitfalls should I avoid', 'project knowledge', 'show me past insights', or 'what went wrong before'."
---

# learn: Project Learnings Knowledge Base

Manage a project's accumulated knowledge — patterns, pitfalls, preferences, and architecture insights.

## Storage

Learnings are stored in `memory/learnings.jsonl` (one JSON object per line):

```json
{"ts":"2026-04-19T10:00:00Z","type":"pattern","key":"auth-middleware-order","insight":"Auth middleware must run before rate limiting to prevent unauthenticated abuse","confidence":8,"source":"observed","files":["src/middleware/auth.py"]}
```

Types:
- `pattern` — Reusable approach
- `pitfall` — What NOT to do
- `preference` — User-stated preference
- `architecture` — Structural decision
- `tool` — Library/framework insight
- `operational` — Project environment/workflow knowledge

## Commands

### Show recent (default: `/learn`)

Show the most recent 20 learnings, grouped by type:

```bash
if [ -f memory/learnings.jsonl ]; then
  tail -20 memory/learnings.jsonl
else
  echo "No learnings recorded yet."
fi
```

### Search (`/learn search <query>`)

Search learnings by keyword:

```bash
if [ -f memory/learnings.jsonl ]; then
  grep -i "query" memory/learnings.jsonl | tail -20
else
  echo "No learnings to search."
fi
```

### Prune (`/learn prune`)

Check for stale or contradictory learnings:

1. **File existence check:** If a learning references files that no longer exist, flag as stale
2. **Contradiction check:** Look for learnings with the same key but opposite insights
3. Present flagged entries and ask whether to remove, keep, or update

### Export (`/learn export`)

Export learnings as markdown for CLAUDE.md or project docs:

```markdown
## Project Learnings

### Patterns
- **auth-middleware-order**: Auth middleware must run before rate limiting (confidence: 8/10)

### Pitfalls
- **missing-null-guard**: User.profile can be null in the onboarding flow (confidence: 9/10)

### Architecture
- **event-driven-audit**: Audit log uses async events to avoid blocking the main request path (confidence: 8/10)
```

### Stats (`/learn stats`)

Show summary statistics:

```
LEARNINGS STATS
═══════════════════════
Total entries: N
Unique (deduped): M
By type:
  pattern:    X
  pitfall:    Y
  preference: Z
  architecture: W
Average confidence: N.N/10
```

### Manual add (`/learn add`)

Manually add a learning. Gather via AskUserQuestion:
1. Type (pattern / pitfall / preference / architecture / tool / operational)
2. Short key (2-5 words, kebab-case)
3. Insight (one sentence)
4. Confidence (1-10)
5. Related files (optional)

Append to `memory/learnings.jsonl`.

---

## Auto-capture

During review, ship, and investigate sessions, automatically capture non-obvious patterns:

```bash
echo '{"ts":"'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'","type":"TYPE","key":"KEY","insight":"INSIGHT","confidence":N,"source":"SOURCE","files":["FILE"]}' >> memory/learnings.jsonl
```

Only capture genuine discoveries — not obvious things the user already knows.

---

## Important Rules

- **Append-only.** Never delete learnings without user approval.
- **Latest wins.** If two learnings have the same key, the most recent one is authoritative.
- **Quality over quantity.** Only capture insights that would save time in a future session.
- **Project-scoped.** Learnings are specific to the current project.

---

## Completion Status

- **DONE** — Learnings displayed, searched, pruned, exported, or added
