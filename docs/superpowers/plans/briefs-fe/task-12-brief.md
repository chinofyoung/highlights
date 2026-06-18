# Task 12 (modern-frontend)

## Global Constraints

- **Backend Python floor:** 3.10+ (interpreter is 3.10.8). Activate `.venv` before any pytest.
- **No new backend dependencies** — background work uses stdlib `threading`.
- **Backward-compatible analyzer/exporter signatures:** new `progress_callback` params MUST default to `None` so existing callers/tests keep working.
- **Existing backend suite (24 tests) must stay green** except the two `/api/detect` & `/api/export` tests in `tests/test_api.py`, which are intentionally updated in Task 4 to the new job flow.
- **Git is disabled** (not a git repo; user policy forbids state-changing git). Wherever a step says "Commit", instead run the task's tests (and build, where relevant) and confirm green. Never run a state-changing git command.
- **Node 22 / npm 10** are installed. Frontend commands run from `frontend/`.
- **Sensitivity semantics:** higher slider = more sensitive = more rallies; the client sends `threshold = 1 - sliderValue`.
- **Job record shape (canonical, used across backend + frontend):** `{ "status": "running"|"done"|"error", "progress": float 0.0–1.0, "result": object|null, "error": string|null }`.
- **Detect job result shape:** `{ "rallies": [{start, end, confidence}] }`. **Export job result shape:** `{ "clips": [string], "stitched": string|null }`.
- **If a pinned npm version fails to resolve,** install the latest compatible version and note it in the task report.



---

## Task 12: README update

**Files:**
- Modify: `README.md`

**Interfaces:** none (documentation).

- [ ] **Step 1: Add a "Frontend development" section to `README.md`**

Insert after the existing Run section:

````markdown
## Frontend (Vite + React)

The UI lives in `frontend/` (Vite + React + TypeScript + Tailwind) and builds to
`frontend/dist/`, which the FastAPI server serves automatically.

### One-time build (required before running normally)
```bash
cd frontend
npm install
npm run build
```
Then run the app as usual from the repo root: `uvicorn app.main:app` and open
http://localhost:8000.

### Frontend development (hot reload)
Run the backend and the Vite dev server in two terminals:
```bash
# terminal 1 (repo root)
source .venv/bin/activate && uvicorn app.main:app

# terminal 2
cd frontend && npm run dev
```
Open http://localhost:5173 — Vite proxies `/api/*` to the backend on :8000.

### Frontend tests
```bash
cd frontend && npm run test
```
````

- [ ] **Step 2: Update the top-level Run instructions** to note the frontend build is required the first time (the `dist/` must exist for the server to serve the UI).

- [ ] **Step 3: Checkpoint** — confirm README commands match reality: `frontend/package.json` scripts (`dev`, `build`, `test`) exist; `npm run build` produces `frontend/dist/index.html`.

---

