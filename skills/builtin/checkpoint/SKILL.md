---
name: checkpoint
source: adapted from gstack (MIT License)
trigger: auto+manual
version: 1.0.0
description: "Save and resume working state checkpoints. Captures git state, decisions made, and remaining work so you can pick up exactly where you left off — even across sessions. Use when asked to 'checkpoint', 'save progress', 'where was I', 'resume', 'what was I working on', 'pick up where I left off', 'save my work', 'save state', 'pause this', 'come back later', or 'what's left to do'."
---

# checkpoint: Save and Resume Working State

Capture git state, decisions made, and remaining work. Save checkpoints as markdown files so you can pick up exactly where you left off.

## Parameters

Parse the user's request:

| Parameter | Default | Override |
|-----------|---------|----------|
| Action | save | `list`, `resume` |
| Title | (inferred from work) | "auth-refactor" |
| Scope | current branch | `--all` for list |

---

## Save flow

### Step 1: Gather state

Collect the current working state:

```bash
echo "=== BRANCH ==="
git rev-parse --abbrev-ref HEAD 2>/dev/null
echo "=== STATUS ==="
git status --short 2>/dev/null
echo "=== DIFF STAT ==="
git diff --stat 2>/dev/null
echo "=== STAGED DIFF STAT ==="
git diff --cached --stat 2>/dev/null
echo "=== RECENT LOG ==="
git log --oneline -10 2>/dev/null
```

### Step 2: Summarize context

Using the gathered state plus conversation history, produce a summary covering:

1. **What's being worked on** — the high-level goal or feature
2. **Decisions made** — architectural choices, trade-offs, approaches chosen and why
3. **Remaining work** — concrete next steps, in priority order
4. **Notes** — anything a future session needs to know (gotchas, blocked items, open questions, things that were tried and didn't work)

If the user provided a title, use it. Otherwise, infer a concise title (3-6 words) from the work being done.

### Step 3: Write checkpoint file

```bash
CHECKPOINT_DIR="checkpoints"
mkdir -p "$CHECKPOINT_DIR"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
```

Write the checkpoint file to `checkpoints/{TIMESTAMP}-{title-slug}.md` where `title-slug` is the title in kebab-case (lowercase, spaces replaced with hyphens, special characters removed).

The file format:

```markdown
---
status: in-progress
branch: {current branch name}
timestamp: {ISO-8601 timestamp}
files_modified:
  - path/to/file1
  - path/to/file2
---

## Working on: {title}

### Summary

{1-3 sentences describing the high-level goal and current progress}

### Decisions Made

{Bulleted list of architectural choices, trade-offs, and reasoning}

### Remaining Work

{Numbered list of concrete next steps, in priority order}

### Notes

{Gotchas, blocked items, open questions, things tried that didn't work}
```

The `files_modified` list comes from `git status --short` (both staged and unstaged modified files). Use relative paths from the repo root.

After writing, confirm to the user:

```
CHECKPOINT SAVED
════════════════════════════════════════
Title:    {title}
Branch:   {branch}
File:     {path to checkpoint file}
Modified: {N} files
════════════════════════════════════════
```

---

## Resume flow

### Step 1: Find checkpoints

```bash
CHECKPOINT_DIR="checkpoints"
if [ -d "$CHECKPOINT_DIR" ]; then
  find "$CHECKPOINT_DIR" -maxdepth 1 -name "*.md" -type f 2>/dev/null | xargs ls -1t 2>/dev/null | head -20
else
  echo "NO_CHECKPOINTS"
fi
```

List checkpoints from **all branches** (checkpoint files contain the branch name in their frontmatter, so all files in the directory are candidates).

### Step 2: Load checkpoint

If the user specified a checkpoint (by number, title fragment, or date), find the matching file. Otherwise, load the **most recent** checkpoint.

Read the checkpoint file and present a summary:

```
RESUMING CHECKPOINT
════════════════════════════════════════
Title:       {title}
Branch:      {branch from checkpoint}
Saved:       {timestamp, human-readable}
Status:      {status}
════════════════════════════════════════

### Summary
{summary from checkpoint}

### Remaining Work
{remaining work items from checkpoint}

### Notes
{notes from checkpoint}
```

If the current branch differs from the checkpoint's branch, note this:
"This checkpoint was saved on branch `{branch}`. You are currently on `{current branch}`. You may want to switch branches before continuing."

### Step 3: Offer next steps

After presenting the checkpoint, ask the user what they'd like to do:

- A) Continue working on the remaining items
- B) Show the full checkpoint file
- C) Just needed the context, thanks

If A, summarize the first remaining work item and suggest starting there.

---

## List flow

### Step 1: Gather checkpoints

```bash
CHECKPOINT_DIR="checkpoints"
if [ -d "$CHECKPOINT_DIR" ]; then
  find "$CHECKPOINT_DIR" -maxdepth 1 -name "*.md" -type f 2>/dev/null | xargs ls -1t 2>/dev/null
else
  echo "NO_CHECKPOINTS"
fi
```

### Step 2: Display table

**Default behavior:** Show checkpoints for the **current branch** only.

If the user passes `--all`, show checkpoints from **all branches**.

Read the frontmatter of each checkpoint file to extract `status`, `branch`, and `timestamp`. Parse the title from the filename (the part after the timestamp).

Present as a table:

```
CHECKPOINTS ({branch} branch)
════════════════════════════════════════
#  Date        Title                    Status
─  ──────────  ───────────────────────  ───────────
1  2026-03-31  auth-refactor            in-progress
2  2026-03-30  api-pagination           completed
3  2026-03-28  db-migration-setup       in-progress
════════════════════════════════════════
```

If `--all` is used, add a Branch column:

```
CHECKPOINTS (all branches)
════════════════════════════════════════
#  Date        Title                    Branch              Status
─  ──────────  ───────────────────────  ──────────────────  ───────────
1  2026-03-31  auth-refactor            feat/auth           in-progress
2  2026-03-30  api-pagination           main                completed
3  2026-03-28  db-migration-setup       feat/db-migration   in-progress
════════════════════════════════════════
```

If there are no checkpoints, tell the user: "No checkpoints saved yet. Run `/checkpoint` to save your current working state."

---

## Important Rules

- **Checkpoints are local files.** Stored in `checkpoints/` directory at repo root.
- **Cross-branch handoff.** A checkpoint saved on one branch can be resumed from another.
- **Save proactively.** Suggest checkpoints when the user is switching context, ending a session, or before a long break.
- **No telemetry.** Do not log checkpoint operations to external services.
- **Never delete checkpoints.** They accumulate — that's intentional for history.

---

## Completion Status

- **DONE** — Checkpoint saved, resumed, or listed successfully
