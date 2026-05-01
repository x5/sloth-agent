#!/bin/bash
# Sloth Agent — one-command dev launcher
# Starts backend + Tauri desktop app (with Vite HMR)

set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
SRC_TAURI="$ROOT/src-tauri"

cleanup() {
  echo ""
  echo "Shutting down..."
  [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null
  exit 0
}
trap cleanup INT TERM

echo "Starting backend..."
cd "$BACKEND"
uv run uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

echo "Waiting for backend..."
sleep 2

echo "Starting Tauri (Rust compile + Vite HMR)..."
cd "$SRC_TAURI"
cargo tauri dev

cleanup
