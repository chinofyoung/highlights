# Cancel + Play Implementation Report
Date: 2026-06-17

## Feature 1 — True cancel of an in-progress analysis

### app/api/jobs.py
- Added `"cancelled": False` to the record dict in `create()`
- Added `cancel(job_id: str) -> None`: sets `cancelled=True` and `status="cancelled"` under `_LOCK`; no-op on unknown id

### app/api/routes.py
- Added module-level `class _Cancelled(Exception): pass`
- In both `detect` and `export` run() closures, replaced inline lambda with a named `_cb(f)` that checks `rec["cancelled"]` before updating progress — raises `_Cancelled` if true
- Added `except _Cancelled: jobs.update(job_id, status="cancelled")` before the broad `except Exception` in both closures
- Added `POST /api/jobs/{job_id}/cancel` endpoint: 404 on unknown id, else calls `jobs.cancel()` and returns the updated record

### app/analyzer/motion.py
- Wrapped the `while True:` frame-reading loop in `try:` / `finally: cap.release()` so the VideoCapture is always released even if the progress callback raises mid-loop
- Function signature and return type unchanged

### tests/test_jobs.py (3 new tests)
- `test_create_has_cancelled_false` — verifies new field is False on creation
- `test_cancel_sets_cancelled_true` — verifies cancel() sets both `cancelled=True` and `status="cancelled"`
- `test_cancel_unknown_is_noop` — verifies cancel() on unknown id does not raise

### tests/test_api.py (2 new tests)
- `test_cancel_unknown_job_404` — POST to unknown id returns 404
- `test_cancel_sets_status` — creates a detect job, immediately POSTs cancel, asserts response has `cancelled=True` and `status="cancelled"` (non-racy: asserts endpoint response only)

---

## Feature 2 — Fix upload→detect flash

### frontend/src/App.tsx
- Removed `setSelectedFile(null)` from `handleAnalyze` — selectedFile is now kept set through the analysis flow, so SelectedVideo can reappear on cancel
- Changed detecting view condition from `detectJob && detect.status === "running"` to `(analyzing || detectJob)` — loader now shows during upload phase too
- Added `!analyzing` guard to review UI condition: `videoId && !detectJob && !analyzing`
- Net effect: no state combo renders the review UI with an empty timeline before detection completes

---

## Feature 3 — Play button on each trimmed clip

### frontend/src/components/Player.tsx
- Extended `PlayerHandle` interface with `playSegment(start: number, end: number): void`
- Added `const segListenerRef = useRef<((e: Event) => void) | null>(null)` inside component
- `playSegment` implementation: clears any previous timeupdate listener, seeks to `start`, attaches new listener that pauses at `end` and removes itself, then calls `play()`

### frontend/src/components/RallyList.tsx
- Added `import { Play } from "lucide-react"`
- Added `onPlay: (rally: Rally) => void` to props interface
- Added Play icon button per row (between checkbox and jump button): `text-[var(--teal)] hover:text-[var(--accent)]`, calls `onPlay(r)` with the Rally object

### frontend/src/api.ts
- Added `export async function cancelJob(jobId: string): Promise<void>` using `postJSON<unknown>`, consistent with other API clients

### frontend/src/App.tsx (wiring)
- Cancel button in detecting view: disabled during `analyzing` (no job yet), calls `api.cancelJob(detectJob)` then resets `detectJob`, `analyzing`, `videoId` to null while keeping `selectedFile` — SelectedVideo reappears
- `onPlay={(r) => player.current?.playSegment(r.start, r.end)}` passed to RallyList

---

## Test Results

### Backend — pytest -v
```
40 passed, 3 warnings in 3.93s
```
(35 existing + 5 new cancel tests; 3 pre-existing deprecation warnings)

### Frontend — npm run build
```
tsc -b && vite build
✓ built in 916ms  —  0 TS errors
```

### Frontend — npm run test
```
vitest run
✓ src/test/timeline-math.test.ts  (7 tests)
✓ src/test/api.test.ts            (4 tests)
✓ src/test/useJob.test.ts         (2 tests)
✓ src/test/SelectedVideo.test.tsx (4 tests)
✓ src/test/App.test.tsx           (4 tests)
Tests  21 passed (21)
```

---

## Concerns / Notes
- None. All existing tests (40 backend, 21 frontend) pass with no new failures.
- The 3 backend deprecation warnings (`on_event`, `httpx/starlette`) are pre-existing and unrelated to these changes.
- The Cancel button is disabled during the upload phase (before `detectJob` is set) to prevent calling cancelJob with a null id — the onClick guard `if (detectJob)` also protects against this.
