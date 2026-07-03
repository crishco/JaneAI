#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PYTHON_BIN="$ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "[JaneAI] Python virtual environment not found at $PYTHON_BIN"
  echo "Create it with: python -m venv .venv"
  exit 1
fi

if [[ ! -d node_modules ]]; then
  echo "[JaneAI] Installing root Node dependencies..."
  npm install
fi

if [[ ! -d frontend/node_modules ]]; then
  echo "[JaneAI] Installing frontend dependencies..."
  npm --prefix frontend install
fi

export PYTHONUNBUFFERED=1

echo "[JaneAI] Starting backend, frontend, and Electron..."
npx concurrently -k -n backend,frontend,electron -c cyan,magenta,green \
  "cd backend && ../.venv/bin/python server.py" \
  "npm --prefix frontend run dev" \
  "cross-env NODE_ENV=development wait-on http://127.0.0.1:8765/health http://127.0.0.1:5173 && cross-env NODE_ENV=development electron ."
