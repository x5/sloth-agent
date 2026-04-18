---
name: land-and-deploy
source: adapted from gstack (MIT License)
trigger: auto+manual
version: 1.0.0
description: "Land a merged PR and verify the deploy. Merges PR, monitors CI/CD deploy workflows, runs canary health checks on production. Use when asked to 'land', 'deploy', 'merge and deploy', 'go live', 'push to production', 'release this', 'merge and release', 'deploy to prod', 'ship to production', or 'verify the deploy'."
---

# land-and-deploy: Merge and Deploy Verification

Merge the PR, monitor the deployment, and verify production health.

## Step 0: Detect platform and base branch

Detect the git hosting platform:

```bash
git remote get-url origin 2>/dev/null
```

- URL contains "github.com" → **GitHub**
- URL contains "gitlab" → **GitLab**
- `gh auth status` → GitHub, `glab auth status` → GitLab
- Neither → **unknown**

Determine base branch (same as review/ship: gh pr view → gh repo view → main → master).

---

## Step 1: Pre-flight

1. Check GitHub CLI auth: `gh auth status`. If not authenticated, stop: "Need GitHub CLI access. Run `gh auth login`."

2. Find the PR:
   ```bash
   gh pr view --json number,state,title,url,mergeStateStatus,mergeable,baseRefName,headRefName
   ```

3. Validate PR state:
   - No PR → stop: "No PR found. Run `/ship` first."
   - Already MERGED → "PR already merged. Skip to deploy verification."
   - CLOSED → "PR was closed without merging."
   - OPEN → continue.

---

## Step 2: Pre-merge checks

1. Check PR mergeability:
   ```bash
   gh pr view --json mergeable,mergeStateStatus
   ```

2. If not mergeable: show the blocking reason (failing checks, conflicts, etc.)

3. Check if CI checks are passing:
   ```bash
   gh pr checks --json name,state | grep -v "SUCCESS"
   ```

4. If checks are failing: warn the user but don't block (they may want to merge anyway).

---

## Step 3: Wait for CI (if pending)

If CI checks are still in progress:

```bash
gh pr checks --watch 2>/dev/null || {
  while true; do
    gh pr view --json state,statusChecks -q '.statusChecks[].state' | sort -u
    sleep 30
  done
}
```

Wait until all checks complete (success, neutral, or skipped). Timeout after 30 minutes.

---

## Step 4: Merge the PR

Try merge (respects repo merge settings):

```bash
gh pr merge --squash --delete-branch
```

If merge fails with permission error: stop: "Don't have permission to merge. Check branch protection rules."

If merge queue is active: poll every 30 seconds until merged. Show progress every 2 minutes.

After merge: capture the merge commit SHA.

---

## Step 5: Deploy strategy detection

Detect how this project deploys:

```bash
# Check CLAUDE.md for deploy config
grep -A 20 "## Deploy Configuration" CLAUDE.md 2>/dev/null

# Auto-detect platform
[ -f fly.toml ] && echo "PLATFORM:fly"
[ -f render.yaml ] && echo "PLATFORM:render"
[ -f vercel.json ] && echo "PLATFORM:vercel"
[ -f netlify.toml ] && echo "PLATFORM:netlify"
[ -f Procfile ] && echo "PLATFORM:heroku"
[ -f railway.json ] && echo "PLATFORM:railway"

# Detect deploy workflows
ls .github/workflows/ 2>/dev/null | grep -iE 'deploy|release|cd'
```

Check for deploy workflow runs triggered by the merge:

```bash
gh run list --branch <base> --limit 5 --json name,status,conclusion,workflowName
```

**Decision tree:**
1. If deploy workflow found → monitor it (Step 6)
2. If docs-only changes → "Nothing to deploy. You're all set."
3. If no deploy workflow and no URL provided → ask user: "Is this a web app that needs deploying, or a library/CLI?"
4. If auto-deploy platform (Vercel, Netlify) → wait 60 seconds, then verify

---

## Step 6: Wait for deploy

### GitHub Actions
Find the run triggered by the merge commit and poll:

```bash
gh run view <run-id> --json status,conclusion
```

Poll every 30 seconds. Show progress every 2 minutes.

### Platform CLI
- **Fly.io:** `fly status --app {app}`
- **Render:** Poll production URL until it responds
- **Heroku:** `heroku releases --app {app} -n 1`

### Auto-deploy (Vercel, Netlify)
Wait 60 seconds for propagation, then proceed to canary.

---

## Step 7: Canary verification

After deploy succeeds, verify production health:

1. **HTTP check:**
   ```bash
   curl -sf {production-url} -o /dev/null -w "%{http_code}"
   ```

2. **Page load:** Visit the production URL, take a screenshot, check for errors

3. **Console check:** Look for JS errors on the production page

4. **Key flows:** Test 2-3 critical user flows (login, main feature, checkout)

If everything passes: "Production health verified. Deploy successful."
If issues found: Flag them with severity. Ask: "Deploy finished but I found N issues. Want to investigate or revert?"

---

## Step 8: Deploy report

```
DEPLOY REPORT
═══════════════════════════════════
PR:         #{number} — {title}
Merged at:  {timestamp}
Merge SHA:  {sha}
Deploy:     {platform/workflow}
Duration:   {deploy duration}
Verdict:    {HEALTHY / ISSUES FOUND}

Canary checks:
  HTTP status: {200/other}
  Page load:   {OK/errors}
  Console:     {N errors}
  Key flows:   {passed/failed}
```

---

## Important Rules

- **Verify before merging.** Check CI, conflicts, and mergeability.
- **Deploy is not instant.** Poll with progress updates, don't silently wait.
- **Canary is mandatory.** Never declare a deploy successful without verifying production.
- **Docs-only = no deploy needed.** Skip the whole sequence for documentation changes.

---

## Completion Status

- **DONE** — PR merged, deploy verified, production healthy
- **DONE_WITH_CONCERNS** — Deployed but canary found issues
- **BLOCKED** — Cannot merge (permissions, conflicts, failing CI)
