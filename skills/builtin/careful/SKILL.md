---
name: careful
source: adapted from gstack (MIT License)
trigger: auto+manual
version: 1.0.0
description: "Safety guardrails for destructive commands. Warns before rm -rf, DROP TABLE, force-push, git reset --hard, and similar destructive operations. Use when asked to 'be careful', 'safety mode', 'prod mode', 'careful mode', 'don't break anything', 'warning mode', 'protect against destructive commands', 'safe mode', or 'double check before running commands'."
---

# careful: Destructive Command Guardrails

Safety mode is now **active**. Before running any destructive command, I will warn you and ask for confirmation.

## What's protected

| Pattern | Example | Risk |
|---------|---------|------|
| `rm -rf` / `rm -r` / `rm --recursive` | `rm -rf /var/data` | Recursive delete |
| `DROP TABLE` / `DROP DATABASE` | `DROP TABLE users;` | Data loss |
| `TRUNCATE` | `TRUNCATE orders;` | Data loss |
| `git push --force` / `-f` | `git push -f origin main` | History rewrite |
| `git reset --hard` | `git reset --hard HEAD~3` | Uncommitted work loss |
| `git checkout .` / `git restore .` | `git checkout .` | Uncommitted work loss |
| `kubectl delete` | `kubectl delete pod` | Production impact |
| `docker rm -f` / `docker system prune` | `docker system prune -a` | Container/image loss |

## Safe exceptions

These patterns are allowed without warning:
- `rm -rf node_modules` / `.next` / `dist` / `__pycache__` / `.cache` / `build` / `.turbo` / `coverage`

## How it works

Before executing any Bash command that matches the destructive patterns above, I will:
1. Warn you about the risk
2. Ask for confirmation
3. Proceed only if you approve

To deactivate, end the conversation or start a new one. Guardrails are session-scoped.
