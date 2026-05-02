#!/usr/bin/env bash
# check-test-coverage.sh — Verify that every frontend component and backend router
# has a corresponding test file. Exits 1 if any are missing.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MISSING=0

# ── Frontend component tests ──────────────────────────────────────────
COMPONENTS_DIR="$REPO_ROOT/frontend/src/components"
TEST_DIRS=("$COMPONENTS_DIR" "$REPO_ROOT/frontend/src/test")

for comp in "$COMPONENTS_DIR"/*.tsx; do
  name="$(basename "$comp")"
  # Skip test files, index files, and non-component files
  [[ "$name" == *.test.tsx ]] && continue
  [[ "$name" == "index.ts" || "$name" == "index.tsx" ]] && continue

  base="${name%.tsx}"
  found=false
  for dir in "${TEST_DIRS[@]}"; do
    [[ -f "$dir/${base}.test.tsx" ]] && found=true && break
  done

  if ! $found; then
    echo "MISSING frontend test: $name  (expected ${base}.test.tsx)"
    MISSING=$((MISSING + 1))
  fi
done

# ── Backend router integration tests ─────────────────────────────────
ROUTERS_DIR="$REPO_ROOT/backend/app/routers"
INTEGRATION_DIR="$REPO_ROOT/backend/tests/integration"

for router in "$ROUTERS_DIR"/*.py; do
  name="$(basename "$router")"
  [[ "$name" == "__init__.py" ]] && continue

  base="${name%.py}"
  if [[ ! -f "$INTEGRATION_DIR/test_${base}.py" ]]; then
    echo "MISSING backend integration test: $name  (expected test_${base}.py)"
    MISSING=$((MISSING + 1))
  fi
done

# ── Summary ───────────────────────────────────────────────────────────
if [[ $MISSING -gt 0 ]]; then
  echo ""
  echo "FAIL: $MISSING test file(s) missing. See above for details."
  exit 1
fi

echo "OK: All components and routers have corresponding test files."
exit 0
