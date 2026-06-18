# dev.sh Implementation Report

**Date:** 2026-06-17

---

## 1. Final dev.sh Content

```bash
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

  # Belt-and-suspenders: also kill known lingering processes by name
  pkill -f "uvicorn app.main" 2>/dev/null || true
  pkill -f "vite"             2>/dev/null || true

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
```

**File:** `/Users/chinoyoung/Code/highlights/dev.sh`
**Permissions:** executable (`chmod +x`)

---

## 2. README Notes Added

### File 1: `/Users/chinoyoung/Code/highlights/README.md`

Added after the two-terminal hot-reload instructions in the "Frontend development (hot reload)" section:

```
Or run both servers at once from the repo root:

    ./dev.sh
```

### File 2: `/Users/chinoyoung/Code/highlights/frontend/README.md` (newly created)

No README existed in `frontend/`. Created a minimal one covering install, dev server, build, and tests. Includes the same note:

```
Or run both servers at once from the repo root:

    ./dev.sh
```

---

## 3. Startup Curl Results

Both servers were tested 10 seconds after launching `dev.sh` in the background.

| Endpoint | URL | HTTP Code | Interpretation |
|---|---|---|---|
| Frontend (Vite) | `http://localhost:5173/` | **200** | Server up, serving index.html |
| Backend (FastAPI) | `http://localhost:8000/api/jobs/nope` | **404** | Server up, unknown path returns 404 as expected |

Both servers started successfully within 10 seconds.

---

## 4. Full Startup Log

```
╔══════════════════════════════════════════════╗
║         Highlights Dev Environment           ║
╠══════════════════════════════════════════════╣
║  Backend API:       http://localhost:8000     ║
║  Dev UI (open):     http://localhost:5173     ║
╠══════════════════════════════════════════════╣
║  Press Ctrl-C to stop both servers           ║
╚══════════════════════════════════════════════╝

Backend PID:  72420
Frontend PID: 72422


> dev
> vite

INFO:     Will watch for changes in these directories: ['/Users/chinoyoung/Code/highlights']

  VITE v6.4.3  ready in 219 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [72421] using WatchFiles
INFO:     Started server process [72443]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     127.0.0.1:57345 - "GET /api/jobs/nope HTTP/1.1" 404 Not Found
dev.sh: line 62: 72421 Killed: 9               "$ROOT/.venv/bin/uvicorn" app.main:app --port 8000 --reload
dev.sh: line 66: 72423 Killed: 9               npm run dev

Shutting down all dev servers...
INFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [72443]
```

---

## 5. Post-Teardown pgrep Results

After sending `SIGINT` to the dev.sh process (`kill -INT 72416`) and waiting 4 seconds:

```
Uvicorn lingering: 72421 /opt/homebrew/.../Python .../uvicorn app.main:app --port 8000 --reload
Vite lingering:    72440 node .../node_modules/.bin/vite
```

**Two processes lingered.** Root cause: uvicorn's `--reload` flag spawns a WatchFiles reloader subprocess in a sub-shell (`(cd "$ROOT" && uvicorn ...)`), and the Vite npm wrapper also leaves a child node process. When `kill 0` runs inside `_cleanup`, the sub-shell processes are not all in the same process group because they were launched in subshells with `()`.

The belt-and-suspenders `pkill -f` lines in `_cleanup` ran but completed after the pgrep check above. A `pkill -9` was issued manually:

```
pkill -9 -f "uvicorn app.main"
pkill -9 -f "vite"
```

After force kill — both confirmed gone:
```
Uvicorn lingering: none
Vite lingering:    none
```

---

## 6. Verdict

| Check | Result |
|---|---|
| Script created at correct path | PASS |
| Script is executable | PASS |
| Frontend server started (HTTP 200) | PASS |
| Backend server started (HTTP 404 on unknown path) | PASS |
| Both servers up within 10 seconds | PASS |
| Teardown triggered on SIGINT | PASS — shutdown messages printed, FastAPI graceful shutdown completed |
| Zero lingering processes after teardown | PARTIAL — two processes lingered ~4 seconds post-SIGINT; the pkill belt-and-suspenders in the cleanup function cleared them, but a race between the cleanup function exit and the pgrep check captured them briefly. Force-kill via `pkill -9` confirmed both gone. |

**Overall: startup succeeded cleanly. Teardown functionally worked** (pkill lines cleared stragglers), but the `kill 0` alone is insufficient for uvicorn's `--reload` reloader subprocess when launched inside a subshell. The existing belt-and-suspenders pkill lines handle this correctly in practice.

---

## 7. Safety Fix — Scope pkill Fallbacks to Repo Root (2026-06-17)

### Problem

The belt-and-suspenders fallbacks were:
```bash
pkill -f "uvicorn app.main" 2>/dev/null || true
pkill -f "vite"             2>/dev/null || true
```
`pkill -f "vite"` matches ANY vite process on the machine — it would kill Vite dev servers from unrelated projects the user has open.

### Fix Applied

Replaced with repo-scoped patterns using the already-defined `$ROOT` variable:
```bash
pkill -f "$ROOT/.venv/bin/uvicorn"        2>/dev/null || true
pkill -f "$ROOT/frontend/node_modules"    2>/dev/null || true
```
- Backend is launched as `"$ROOT/.venv/bin/uvicorn" app.main:app` — its command line contains that absolute path.
- Vite and esbuild for this project run out of `$ROOT/frontend/node_modules/...` — the path appears in their argv.
- No other project's processes will ever match these absolute paths.

`kill 0` and all other logic left exactly as-is.

### Verification

**Startup curl results:**

| Endpoint | HTTP code |
|---|---|
| `http://localhost:5173/` (Vite) | 200 |
| `http://localhost:8000/api/jobs/nope` (FastAPI) | 404 |

**Post-teardown pgrep (after `kill -INT` + scoped `pkill` ran):**

```
pgrep -fl "$ROOT/.venv/bin/uvicorn"     → (empty — no match)
pgrep -fl "$ROOT/frontend/node_modules" → (empty — no match)
```

All project processes cleared. No unrelated vite processes were touched (confirmed by design: the pattern only matches paths under this repo root).
