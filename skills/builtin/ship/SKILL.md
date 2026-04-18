---
name: ship
source: adapted from gstack (MIT License)
trigger: auto+manual
version: 1.0.0
description: "Ship a feature branch: merge base, run tests, commit in logical chunks, push, create PR/MR with comprehensive body, auto-update docs. Use when asked to 'ship', 'deploy', 'push', 'create PR', 'open a pull request', 'merge and push', 'get this ready to merge', 'submit for review', or 'push my changes'."
---

# ship: Ship a Feature Branch

Merge the base branch, run tests, commit changes in logical chunks, push, and create a PR/MR with a comprehensive body. Documentation is auto-updated.

## Parameters

Parse the user's request:

| Parameter | Default | Override |
|-----------|---------|----------|
| Base branch | (auto-detect) | `--base main` |
| Skip tests | false | `--skip-tests` |
| PR title | (inferred) | `--title "..."` |

---

## Step 0: Detect platform and base branch

First, detect the git hosting platform from the remote URL:

```bash
git remote get-url origin 2>/dev/null
```

- If the URL contains "github.com" → platform is **GitHub**
- If the URL contains "gitlab" → platform is **GitLab**
- Otherwise, check CLI availability:
  - `gh auth status 2>/dev/null` succeeds → platform is **GitHub**
  - `glab auth status 2>/dev/null` succeeds → platform is **GitLab**
  - Neither → **unknown** (use git-native commands only)

Determine which branch this PR/MR targets, or the repo's default branch if no PR/MR exists:

**If GitHub:**
1. `gh pr view --json baseRefName -q .baseRefName` — if succeeds, use it
2. `gh repo view --json defaultBranchRef -q .defaultBranchRef.name` — if succeeds, use it

**If GitLab:**
1. `glab mr view -F json 2>/dev/null` and extract the `target_branch` field
2. `glab repo view -F json 2>/dev/null` and extract the `default_branch` field

**Git-native fallback:**
1. `git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's|refs/remotes/origin/||'`
2. If that fails: `git rev-parse --verify origin/main 2>/dev/null` → use `main`
3. If that fails: `git rev-parse --verify origin/master 2>/dev/null` → use `master`

If all fail, fall back to `main`.

---

## Step 1: Pre-flight

1. Check the current branch. If on the base branch, **abort**: "You're on the base branch. Ship from a feature branch."

2. Run `git status` (never use `-uall`). Uncommitted changes are always included.

3. Run `git diff <base>...HEAD --stat` and `git log <base>..HEAD --oneline` to understand what's being shipped.

4. If diff is large (>200 lines), note: "Large diff — consider reviewing before shipping."

---

## Step 1.5: Distribution Pipeline Check

If the diff introduces a new standalone artifact (CLI binary, library package, tool):

1. Check for new entry points:
   ```bash
   git diff origin/<base> --name-only | grep -E '(cmd/.*/main\.go|bin/|Cargo\.toml|setup\.py|package\.json)' | head -5
   ```

2. If new artifact detected, check for a release workflow:
   ```bash
   ls .github/workflows/ 2>/dev/null | grep -iE 'release|publish|dist'
   ```

3. **If no release pipeline exists:** Warn the user: "This PR adds a new binary/tool but there's no CI/CD pipeline to build and publish it." Suggest adding one or deferring to TODOS.md.

---

## Step 2: Merge the base branch

Fetch and merge the base branch so tests run against the merged state:

```bash
git fetch origin <base> && git merge origin/<base> --no-edit
```

**If there are merge conflicts:** Try to auto-resolve simple conflicts. If conflicts are complex, **STOP** and show them to the user.

**If already up to date:** Continue silently.

---

## Step 3: Run tests

Detect and run the project's test suite:

```bash
# Detect test framework
[ -f package.json ] && grep -q '"test"' package.json 2>/dev/null && echo "TEST:npm"
[ -f pyproject.toml ] && grep -q "pytest" pyproject.toml 2>/dev/null && echo "TEST:pytest"
[ -f Cargo.toml ] && echo "TEST:cargo"
[ -f go.mod ] && echo "TEST:go"
```

Run the appropriate test command, capturing output and exit code.

**If tests fail:** Show the failures. Ask the user:
- A) Fix failures and re-run tests
- B) Push anyway (not recommended)
- C) Abort

If A: Fix the failing tests, re-run. If they still fail after reasonable effort, return to B or C.

**If tests pass:** Continue.

---

## Step 3.5: Pre-Landing Review

Run a quick review of the diff for obvious issues:

1. **SQL/Data safety** — Any raw SQL? Migrations safe?
2. **Security** — Auth checks, input validation, injection risks
3. **Type safety** — Type errors, missing type annotations
4. **Test coverage** — New code covered by tests?
5. **Error handling** — New error paths handled?

If issues found, show them to the user with severity labels (P0/P1/P2). For P0/P1 issues, recommend fixing before shipping.

---

## Step 4: Version bump

**If VERSION file exists:**

1. Read the current version.
2. Determine the bump type from the changes:
   - New features → MINOR (X.Y+1.0)
   - Bug fixes only → PATCH (X.Y.Z+1)
   - Breaking changes → MAJOR (X+1.0.0)
3. Update VERSION with the new version.
4. Do NOT bump without asking if uncertain — show the user the current version and proposed bump.

**If VERSION does not exist:** Skip.

---

## Step 5.5: TODOS.md Update

Cross-reference the project's TODOS.md against the changes being shipped.

1. **If TODOS.md exists:**
   - For each TODO item, check if the diff completes it
   - Mark completed items: move to `## Completed` section with version and date
   - Be conservative — only mark if clear evidence in the diff

2. **If TODOS.md does not exist:** Skip.

3. Output summary: "TODOS.md: N items marked complete." or "TODOS.md: No items completed."

---

## Step 6: Commit (bisectable chunks)

Create small, logical commits:

1. **Order** (earliest first):
   - Infrastructure: migrations, config, route additions
   - Models & services (with tests)
   - Controllers & views (with tests)
   - VERSION + CHANGELOG + TODOS.md (final commit)

2. **Rules:**
   - A model and its tests go in the same commit
   - Each commit must be independently valid
   - If diff is small (<50 lines, <4 files), a single commit is fine

3. **Commit message format:**
   - First line: `<type>: <summary>` (feat/fix/chore/refactor/docs)
   - Only the final commit gets the co-author trailer:

```bash
git commit -m "$(cat <<'EOF'
chore: bump version and changelog (vX.Y.Z)

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Step 6.5: Verification Gate

Before pushing, re-verify if code changed during Steps 4-6:

1. **Test verification:** If any code changed after Step 3's test run, re-run tests.
2. **Build verification:** If the project has a build step, run it.

**If tests fail:** STOP. Do not push. Fix and return to Step 3.

---

## Step 7: Push

Check if the branch is already pushed:

```bash
git fetch origin <branch-name> 2>/dev/null
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/<branch-name> 2>/dev/null || echo "none")
[ "$LOCAL" = "$REMOTE" ] && echo "ALREADY_PUSHED" || echo "PUSH_NEEDED"
```

If push needed:

```bash
git push -u origin <branch-name>
```

---

## Step 8: Create PR/MR

Check if a PR/MR already exists:

**If GitHub:**
```bash
gh pr view --json url,number,state -q 'if .state == "OPEN" then "PR #\(.number): \(.url)" else "NO_PR" end' 2>/dev/null || echo "NO_PR"
```

If an open PR exists: **update** the body with fresh results.
If no PR exists: create one.

The PR/MR body should contain:

```
## Summary
<Summarize all changes. Group commits into logical sections.>

## Test Coverage
<Test results, or "All new code paths have test coverage.">

## Pre-Landing Review
<Review findings, or "No issues found.">

## TODOS
<Completed items, or "No TODO items completed in this PR.">

## Test plan
- [x] Tests pass

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

**If GitHub:**
```bash
gh pr create --base <base> --title "<type>: <summary>" --body "<PR body>"
```

**If neither CLI is available:** Print the branch name and instruct the user to create the PR/MR manually.

---

## Step 8.5: Auto-invoke /document-release

After the PR is created, sync project documentation:

1. Read the `document-release/SKILL.md` skill and execute its workflow
2. If any docs were updated, commit and push:
   ```bash
   git add -A && git commit -m "docs: sync documentation with shipped changes" && git push
   ```
3. If no docs needed: "Documentation is current — no updates needed."

This step is automatic. No user confirmation needed.

---

## Important Rules

- **One logical change per commit.** Never bundle unrelated changes.
- **Tests must pass before push.** No exceptions.
- **Merge base before testing.** Always test against merged state.
- **VERSION + CHANGELOG in final commit.** Keep metadata together.
- **Auto-update docs.** Never ship code changes without updating documentation.
- **Never skip verification.** If code changed after tests, re-run.

---

## Completion Status

- **DONE** — Code pushed, PR created, docs updated
- **DONE_WITH_CONCERNS** — Code pushed but tests failed or review found issues
- **BLOCKED** — Merge conflicts, auth failure, or tests failing with no fix
