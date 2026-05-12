#!/bin/bash
# Sloth Agent — one-command dev launcher
# Starts backend + Tauri desktop app (with Vite HMR)

set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
SRC_TAURI="$ROOT/src-tauri"

export SLOTH_BACKEND_URL="${SLOTH_BACKEND_URL:-http://127.0.0.1:8080}"
PORT=$(echo "$SLOTH_BACKEND_URL" | grep -oP ':\d+' | tr -d ':' || echo "8080")
PORT=${PORT:-8080}

cleanup() {
  echo ""
  echo "Shutting down..."
  [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null
  exit 0
}
trap cleanup INT TERM

echo "Starting backend on port $PORT (SLOTH_BACKEND_URL=$SLOTH_BACKEND_URL)..."
cd "$BACKEND"
uv run uvicorn app.main:app --reload --port "$PORT" &
BACKEND_PID=$!

echo "Waiting for backend..."
sleep 2

echo "Starting Tauri (Rust compile + Vite HMR)..."
cd "$SRC_TAURI"
cargo tauri dev

cleanup
