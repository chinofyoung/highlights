# Task 12 Report: README Update

## Summary
Updated `README.md` with complete frontend (Vite + React) development and build instructions.

## Changes Made

### Step 1: Added "Frontend (Vite + React)" section
- Inserted new section after the "Test" section (before "Tuning detection")
- Includes three subsections:
  1. **One-time build**: `cd frontend && npm install && npm run build`
  2. **Frontend development (hot reload)**: Instructions for running backend + Vite dev server in parallel, with note that Vite proxies `/api/*` to backend on :8000
  3. **Frontend tests**: `cd frontend && npm run test`

### Step 2: Updated "Run" section
- Added first-time setup note about building frontend
- Added `cd frontend && npm install && npm run build` before the `uvicorn` command
- Preserved existing instructions about opening http://localhost:8000 and using the app

## Accuracy Verification

✓ **Frontend package.json scripts verified:**
  - `dev`: "vite" ✓
  - `build`: "tsc -b && vite build" ✓
  - `test`: "vitest run" ✓

✓ **Frontend dist verified:**
  - `frontend/dist/index.html` exists after build ✓

✓ **Backend command verified:**
  - `uvicorn app.main:app` is correct entry point ✓
  - `app/main.py` creates FastAPI app instance `app` ✓
  - Server automatically mounts `frontend/dist/` at root when it exists ✓

✓ **Vite dev server proxy:**
  - Brief specifies Vite proxies `/api/*` to backend on :8000 ✓
  - Vite dev server runs on port 5173 by default ✓

## Deviations from Brief
None. All content added verbatim from the brief's Step 1 markdown and Step 2 intent.

## Concerns
None. All commands match the codebase reality.

## Files Modified
- `/Users/chinoyoung/Code/highlights/README.md` (2 edits)
  - Updated Run section (lines 17–32)
  - Added Frontend section (lines 40–68)

---

# Task 12 Addendum: Three Hardening Fixes

## Changes Made

### Fix 1 — `frontend/src/useJob.ts`: Reset state when jobId clears
- **Before:** `if (!jobId) return;`
- **After:** `if (!jobId) { setRec(IDLE); return; }`
- Ensures the hook resets to the IDLE record (not stale terminal state) when jobId becomes null.

### Fix 2 — `frontend/src/api.ts`: `getJob` surfaces server detail
- **Before:** `if (!r.ok) throw new Error("job lookup failed");`
- **After:** Extracts `detail` from JSON response body (with `.catch(() => ({}))` fallback), throws `new Error(detail || r.statusText)` — matching the pattern used by `postJSON` and `uploadVideo`.

### Fix 3 — `app/api/routes.py`: Remove unused `BackgroundTasks` import
- **Before:** `from fastapi import APIRouter, BackgroundTasks, UploadFile, File, HTTPException`
- **After:** `from fastapi import APIRouter, UploadFile, File, HTTPException`

## Build & Test Results

### Frontend (`cd frontend && npm run build && npm run test`)
```
npm run build:
  tsc -b && vite build
  ✓ 1583 modules transformed.
  ✓ built in 832ms  (0 TS errors)

npm run test:
  ✓ src/test/timeline-math.test.ts (7 tests)
  ✓ src/test/api.test.ts (4 tests)
  ✓ src/test/useJob.test.ts (2 tests)
  Test Files  3 passed (3)
  Tests  13 passed (13)
```

### Backend (`pytest tests/test_api.py -v`)
```
tests/test_api.py::test_full_flow_jobs PASSED
tests/test_api.py::test_unknown_job_404 PASSED
tests/test_api.py::test_upload_rejects_non_video PASSED
tests/test_api.py::test_params_ignores_unknown_keys PASSED
4 passed, 3 warnings in 1.04s
```

## Deviations from Brief
None.

## Concerns
None.
