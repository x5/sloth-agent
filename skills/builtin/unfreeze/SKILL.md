---
name: unfreeze
source: adapted from gstack (MIT License)
trigger: auto+manual
version: 1.0.0
description: "Remove the freeze boundary set by /freeze or /guard. Re-enables file edits across the entire project. Use when asked to 'unfreeze', 'remove edit restriction', 'unlock edits', 'allow all edits again', 'remove the freeze', 'stop restricting edits', or 'I need to edit files outside the frozen directory'."
---

# unfreeze: Remove Edit Restrictions

Remove the freeze boundary and re-enable file edits across the entire project.

## How it works

Delete the freeze state file to remove the edit boundary:

```bash
rm -f memory/freeze-dir.txt 2>/dev/null || echo "No freeze boundary set."
echo "Freeze boundary removed. Edits are unrestricted."
```

Tell the user: "Edit restrictions removed. You can now edit any file in the project."

## Notes

- If no freeze boundary was set, this is a no-op.
- This also deactivates guard mode (which includes freeze).
- Destructive command warnings from `/careful` are session-scoped and end with the conversation.
