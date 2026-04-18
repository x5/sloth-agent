---
name: guard
source: adapted from gstack (MIT License)
trigger: auto+manual
version: 1.0.0
description: "Full safety mode: destructive command warnings + directory-scoped edits. Combines /careful and /freeze. Use for maximum safety when touching prod or debugging live systems. Use when asked to 'guard mode', 'full safety', 'lock it down', 'maximum safety', 'protect everything', 'safe + restricted edits', or 'don't break anything and only touch this folder'."
---

# guard: Full Safety Mode

Activates both destructive command warnings and directory-scoped edit restrictions. This is the combination of `/careful` + `/freeze` in a single command.

## Setup

Ask the user which directory to restrict edits to:

> Guard mode: which directory should edits be restricted to? Destructive command warnings are always on. Files outside the chosen path will be blocked from editing.

Once the user provides a directory path, set the freeze boundary.

## What's active

1. **Destructive command warnings** — `rm -rf`, `DROP TABLE`, `force-push`, etc. will warn before executing (you can override)
2. **Edit boundary** — file edits restricted to `<path>/`. Edits outside this directory are blocked.

Protected command patterns:
- `rm -rf`, `DROP TABLE`, `TRUNCATE`, `git push --force`, `git reset --hard`, `kubectl delete`, `docker rm -f`

Safe exceptions (no warning needed):
- `rm -rf node_modules` / `.next` / `dist` / `__pycache__` / `.cache` / `build`

To remove the edit boundary, run `/unfreeze`. To deactivate everything, end the session.
