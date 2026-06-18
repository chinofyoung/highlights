#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Preflight checks ──────────────────────────────────────────────────────────

if [[ ! -x "$ROOT/.venv/bin/uvicorn" ]]; then
  echo ""
  echo "ERROR: .venv not found or uvicorn missing."
  echo "Set up the virtual environment first:"
  echo ""
  echo "  python3 -m venv .venv"
  echo "  source .venv/bin/activate"
  echo "  pip install -e '.[dev]'"
  echo ""
  exit 1
fi

if [[ ! -d "$ROOT/frontend/node_modules" ]]; then
  echo "NOTE: frontend/node_modules not found — running npm install..."
  (cd "$ROOT/frontend" && npm install)
  echo "npm install complete."
fi

# ── Cleanup / teardown ────────────────────────────────────────────────────────

_cleanup() {
  # Clear the trap first so we don't re-enter
  trap - INT TERM EXIT

  echo ""
  echo "Shutting down all dev servers..."

  # Kill the entire process group (catches vite, esbuild, uvicorn worker processes)
  # 'kill 0' sends to every process in the current process group
  kill 0 2>/dev/null || true

  # Belt-and-suspenders: also kill known lingering processes by name.
  # Scoped to this repo's absolute paths so unrelated projects are never touched.
  pkill -f "$ROOT/.venv/bin/uvicorn"        2>/dev/null || true
  pkill -f "$ROOT/frontend/node_modules"    2>/dev/null || true

  echo "Done."
}

trap _cleanup INT TERM EXIT

# ── Start servers ─────────────────────────────────────────────────────────────

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║         Highlights Dev Environment           ║"
echo "╠══════════════════════════════════════════════╣"
echo "║  Backend API:       http://localhost:8000     ║"
echo "║  Dev UI (open):     http://localhost:5173     ║"
echo "╠══════════════════════════════════════════════╣"
echo "║  Press Ctrl-C to stop both servers           ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# Backend — run from repo root so app.main resolves
(cd "$ROOT" && "$ROOT/.venv/bin/uvicorn" app.main:app --port 8000 --reload) &
BACKEND_PID=$!

# Frontend — run from frontend/ dir
(cd "$ROOT/frontend" && npm run dev) &
FRONTEND_PID=$!

echo "Backend PID:  $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo ""

# Stay alive until interrupted
wait
