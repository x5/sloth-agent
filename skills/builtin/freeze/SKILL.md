---
name: freeze
source: adapted from gstack (MIT License)
trigger: auto+manual
version: 1.0.0
description: "Restrict file edits to a specific directory for the session. Use when debugging to prevent accidentally 'fixing' unrelated code, or when you want to scope changes to one module. Use when asked to 'freeze', 'restrict edits', 'only edit this folder', 'lock down edits', 'don't touch other files', 'scope edits to this directory', 'only change files in this folder', or 'limit changes to this path'."
---

# freeze: Restrict Edits to a Directory

Lock file edits to a specific directory. Any Edit or Write operation targeting a file outside the allowed path will be **blocked**.

## Setup

Ask the user which directory to restrict edits to:

> Which directory should I restrict edits to? Files outside this path will be blocked from editing.

Once the user provides a directory path:

1. Resolve it to an absolute path
2. Save the freeze boundary to session state

Tell the user: "Edits are now restricted to `<path>/`. Any Edit or Write outside this directory will be blocked. To change the boundary, run `/freeze` again. To remove it, run `/unfreeze` or end the session."

## How it works

- The freeze boundary persists for the session.
- Freeze applies to Edit and Write tools only — Read, Bash, Glob, Grep are unaffected.
- This prevents accidental edits, not a security boundary — Bash commands like `sed` can still modify files outside the boundary.
- The trailing `/` on the freeze directory prevents `/src` from matching `/src-old`.

## Notes

- To deactivate, run `/unfreeze` or end the conversation.
