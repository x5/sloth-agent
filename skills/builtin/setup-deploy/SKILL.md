---
name: setup-deploy
source: adapted from gstack (MIT License)
trigger: auto+manual
version: 1.0.0
description: "Configure deploy settings for the project. Detects platform, gathers production URL, health checks, and deploy workflow info. Saves to CLAUDE.md for /land-and-deploy to use. Use when asked to 'setup deploy', 'configure deployment', 'set production URL', 'configure the deploy target', 'set up CI/CD', 'which platform do we deploy to', 'add deploy config', 'set health check URL', or 'configure the production URL'."
---

# setup-deploy: Configure Deploy Settings

Detect the project's deploy infrastructure, gather configuration, and save it to CLAUDE.md.

## Step 1: Check existing configuration

```bash
grep -A 20 "## Deploy Configuration" CLAUDE.md 2>/dev/null || echo "NO_CONFIG"
```

If config exists: show it and ask whether to reconfigure, edit specific fields, or keep as-is.

## Step 2: Detect platform

```bash
[ -f fly.toml ] && echo "PLATFORM:fly"
[ -f render.yaml ] && echo "PLATFORM:render"
[ -f vercel.json ] || [ -d .vercel ] && echo "PLATFORM:vercel"
[ -f netlify.toml ] && echo "PLATFORM:netlify"
[ -f Procfile ] && echo "PLATFORM:heroku"
[ -f railway.json ] || [ -f railway.toml ] && echo "PLATFORM:railway"
[ -f Dockerfile ] && echo "PLATFORM:docker"

ls .github/workflows/ 2>/dev/null | grep -iE 'deploy|release|cd'
```

## Step 3: Gather configuration

Based on detection, gather deploy settings:

### Auto-detected platform
- Read the config file (fly.toml, render.yaml, etc.)
- Extract app name, regions, build commands
- Infer production URL

### No platform detected
Ask the user:

1. **How are deploys triggered?**
   - Auto on push to main
   - GitHub Actions workflow
   - Deploy script/CLI
   - Manual (dashboard, SSH)
   - Doesn't deploy (library, CLI)

2. **What's the production URL?**

3. **How to check deploy success?**
   - HTTP health check URL
   - CLI command
   - GitHub Actions status
   - No automated way

4. **Pre-merge or post-merge hooks?**

## Step 4: Write configuration

Add or update the `## Deploy Configuration` section in CLAUDE.md:

```markdown
## Deploy Configuration (configured by /setup-deploy)
- Platform: {fly/render/vercel/netlify/heroku/railway/docker/custom}
- Production URL: {url}
- Deploy workflow: {workflow file or "auto-deploy on push"}
- Deploy status command: {command or "HTTP health check"}
- Merge method: {squash/merge/rebase}
- Project type: {web app / API / CLI / library}
- Post-deploy health check: {URL or command}

### Custom deploy hooks
- Pre-merge: {command or "none"}
- Deploy trigger: {command or "automatic"}
- Deploy status: {command or "poll URL"}
- Health check: {URL or command}
```

## Step 5: Verify

1. Test health check URL: `curl -sf "{url}" -o /dev/null -w "%{http_code}"`
2. Test deploy status command (if configured)

Report results. If anything fails, note it but don't block.

## Step 6: Summary

```
DEPLOY CONFIGURATION — COMPLETE
════════════════════════════════
Platform:      {platform}
URL:           {url}
Health check:  {health check}
Status cmd:    {status command}

Saved to CLAUDE.md. /land-and-deploy will use these automatically.
```

---

## Important Rules

- **Don't expose secrets.** Never log full API keys or tokens.
- **Infer before asking.** Detect as much as possible from config files before prompting.
- **Verify before saving.** Test URLs and commands to catch typos early.
- **CLAUDE.md is the source of truth.** All deploy config lives there.

---

## Completion Status

- **DONE** — Deploy configuration saved to CLAUDE.md
- **DONE_WITH_CONCERNS** — Config saved but verification failed for some checks
