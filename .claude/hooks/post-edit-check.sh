#!/usr/bin/env bash
# post-edit-check.sh — PostToolUse hook: run type diagnostics after file edits
# Reads hook JSON from stdin, extracts file_path, dispatches to the right checker.
# Non-blocking: failures produce warnings (exit 0) so edits aren't blocked.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# Read hook JSON from stdin
INPUT=$(cat)

# Extract file_path from tool_input JSON
FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('tool_input', {}).get('file_path', ''))
" 2>/dev/null || true)

# Exit silently if no file path found
[[ -z "$FILE_PATH" ]] && exit 0

# Normalize to forward slashes (Windows compatibility)
FILE_PATH="${FILE_PATH//\\//}"

# Skip non-source paths
case "$FILE_PATH" in
  *node_modules*|*.venv*|*__pycache__*|*target/debug*|*target/release*|*dist/*) exit 0 ;;
esac

# Get relative path from repo root
REL_PATH="${FILE_PATH#"$REPO_ROOT/"}"

# Dispatch based on extension
case "$REL_PATH" in
  *.ts|*.tsx)
    # Skip test files for tsc (they have their own type checking)
    case "$REL_PATH" in
      *.test.ts|*.test.tsx) exit 0 ;;
    esac
    cd "$REPO_ROOT/frontend" && npx tsc --noEmit 2>&1 || true
    ;;
  *.py)
    # Only check project files, not generated/installed
    case "$REL_PATH" in
      .venv/*|*/.venv/*|*site-packages*|*gen/*) exit 0 ;;
    esac
    cd "$REPO_ROOT" && uv run mypy --config-file pyproject.toml "$REL_PATH" 2>&1 || true
    ;;
  *.rs)
    cd "$REPO_ROOT/src-tauri" && cargo check 2>&1 || true
    ;;
  *)
    # Not a recognized source file — skip silently
    exit 0
    ;;
esac
