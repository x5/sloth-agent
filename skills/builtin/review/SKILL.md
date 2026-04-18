---
name: review
source: adapted from gstack (MIT License)
trigger: auto+manual
version: 1.0.0
description: "Pre-landing PR review. Analyzes diff against the base branch for SQL safety, trust boundary violations, conditional side effects, and other structural issues. Use when asked to 'review this PR', 'code review', 'check my diff', 'review my changes', 'pre-merge review', 'review before merge', 'look at my changes', or 'is this code safe to merge'."
---

# review: Pre-Landing Code Review

Analyze the current branch's diff against the base branch for structural issues that tests don't catch.

## Step 0: Detect platform and base branch

Detect the git hosting platform and target branch:

```bash
git remote get-url origin 2>/dev/null
```

- If URL contains "github.com" → **GitHub**
- If URL contains "gitlab" → **GitLab**
- Check CLI: `gh auth status` → GitHub, `glab auth status` → GitLab
- Neither → **unknown** (use git-native commands)

Determine base branch:
- GitHub: `gh pr view --json baseRefName -q .baseRefName` or `gh repo view --json defaultBranchRef -q .defaultBranchRef.name`
- GitLab: `glab mr view -F json` target_branch or `glab repo view -F json` default_branch
- Fallback: `git symbolic-ref refs/remotes/origin/HEAD` → `main` → `master`

---

## Step 1: Check branch

1. Run `git branch --show-current`.
2. If on the base branch, output: **"Nothing to review — you're on the base branch."** and stop.
3. Run `git fetch origin <base> --quiet && git diff origin/<base> --stat`. If no diff, stop.

---

## Step 1.5: Scope Drift Detection

Before reviewing code quality, check: **did they build what was requested?**

1. Read `TODOS.md` (if it exists). Read commit messages (`git log origin/<base>..HEAD --oneline`).
2. Identify the **stated intent** — what was this branch supposed to accomplish?
3. Compare files changed against stated intent.

**SCOPE CREEP detection:**
- Files unrelated to stated intent
- New features or refactors not mentioned
- "While I was in there..." changes

**MISSING REQUIREMENTS detection:**
- Requirements from TODOS.md not addressed
- Test coverage gaps for stated requirements
- Partial implementations

Output:
```
Scope Check: [CLEAN / DRIFT DETECTED / REQUIREMENTS MISSING]
Intent: <1-line summary>
Delivered: <1-line summary>
[If drift: list each out-of-scope change]
[If missing: list each unaddressed requirement]
```

This is **INFORMATIONAL** — does not block the review.

---

## Step 2: Get the diff

Fetch latest base branch:

```bash
git fetch origin <base> --quiet
```

Run `git diff origin/<base>` to get the full diff (committed and uncommitted changes).

---

## Step 3: Critical pass

Review the diff for these categories:

### CRITICAL Categories

1. **SQL & Data Safety:**
   - Raw SQL with string interpolation
   - Migrations that lock tables or drop columns
   - N+1 queries
   - Missing indexes on new queries

2. **Race Conditions & Concurrency:**
   - Check-then-act patterns without locks
   - Non-atomic read-modify-write
   - Missing transaction boundaries

3. **Trust Boundary Violations:**
   - User input passed directly to shell commands
   - Unvalidated input in database queries
   - Missing auth checks on sensitive endpoints
   - LLM output used without validation

4. **Shell Injection:**
   - String interpolation in subprocess calls
   - Unsanitized file paths
   - Command injection via user-controlled arguments

5. **Enum & Value Completeness:**
   - New enum values not handled in all switch/match statements
   - Missing status/tier handling in existing code
   - **Requires reading code OUTSIDE the diff** — grep for sibling values

### INFORMATIONAL Categories

6. **Type Coercion** — Implicit conversions that could lose precision
7. **Time Window Safety** — Timezone handling, DST transitions
8. **Error Handling** — Swallowed exceptions, missing error paths
9. **Completeness Gaps** — Added feature but missing tests, docs, or config

### Finding format:

```
[SEVERITY] (confidence: N/10) file:line — description
```

Severity levels:
- **P0** — Security vulnerability, data loss, production outage risk
- **P1** — Logic bug, incorrect behavior, broken user flow
- **P2** — Code smell, maintainability issue, potential performance problem
- **P3** — Style, naming, minor improvement

Confidence levels:
- **9-10:** Verified by reading specific code. Concrete bug.
- **7-8:** High confidence pattern match.
- **5-6:** Moderate. Show with caveat: "Verify this is actually an issue."
- **3-4:** Low confidence. Include in appendix only.
- **1-2:** Speculation. Only report if P0 severity.

---

## Step 4: Enum & Value Completeness (deep check)

When the diff introduces a new enum value, status, tier, or type constant:

1. Grep for all files that reference sibling values
2. Read those files to check if the new value is handled
3. Flag any missing handlers

Example:
```bash
# If diff adds a new status "PENDING_REVIEW"
grep -rn "COMPLETED\|CANCELLED\|PENDING" --include="*.py" --include="*.ts" --include="*.rb"
```

---

## Step 5: Fix-First Review

For findings in this review:

### AUTO-FIX (apply directly):
- Missing type annotations
- Unused imports/variables
- Simple SQL injection (use parameterized queries)
- Missing null checks

### ASK (require user approval):
- Architectural changes
- Logic rewrites
- Anything changing behavior

**Never commit, push, or create PRs** — that's the ship workflow's job.

---

## Step 5.5: TODOS cross-reference

Check if any issues found in the review match existing items in TODOS.md:

1. If TODOS.md exists, search for items related to the files/categories with findings
2. If a finding matches a known TODO, note: "Known issue: [TODO reference]"
3. If a finding is NOT in TODOS.md and should be, suggest adding it

---

## Step 5.6: Documentation staleness check

Cross-reference the diff against documentation files (README.md, ARCHITECTURE.md, etc.):

1. Check if code changes affect features described in docs
2. If docs were NOT updated but code changed, flag: "Documentation may be stale: [file]. Consider running `/document-release`."

This is informational only.

---

## Step 6: Output Summary

Present the full review:

```
REVIEW SUMMARY
═══════════════════════════════════════
Branch: {branch}
Base:   {base}
Diff:   +N / -M lines across K files

Scope Check: {result}

Critical findings:
{list P0/P1 findings with file:line}

Informational findings:
{list P2/P3 findings}

Total: N findings (P0: X, P1: Y, P2: Z, P3: W)

Top 3 things to fix:
1. ...
2. ...
3. ...
```

---

## Important Rules

- **Read the FULL diff before commenting.** Do not flag issues already addressed.
- **Fix-first where safe.** Auto-fix trivial issues, ask for the rest.
- **Be terse.** One line problem, one line fix suggestion. No preamble.
- **Only flag real problems.** Skip anything that's fine.
- **Never commit or push.** Review only — shipping is a separate workflow.

---

## Completion Status

- **DONE** — Review complete, findings reported
- **DONE_WITH_CONCERNS** — Review completed but some areas could not be fully analyzed
- **BLOCKED** — Cannot get diff or review cannot proceed
