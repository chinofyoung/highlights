# Cancel + Play Features — Implementation Plan

## Global Constraints
- Project: pickleball highlights app
- Backend: FastAPI in `app/` — activate venv with `source .venv/bin/activate`
- Frontend: React+TS+Tailwind in `frontend/` — run npm from there
- CSS vars: `--accent` (optic lime CTA), `--accent-ink`, `--teal`, `--ink`, `--muted`, `--line`, `--surface`, `--bg`, `--danger`; fonts `--font-display`/`--font-body`/`--font-mono`
- Strict TS: noUnusedLocals/noUnusedParams — every declared prop/variable must be used
- Tests are type-checked (no tsconfig excludes)
- NO git operations of any kind
- Report contract: write full report to `/Users/chinoyoung/Code/highlights/docs/superpowers/plans/briefs-fe/cancel-play-report.md`

## Tasks

### Task 1 — Backend cancel support (jobs.py + routes.py + motion.py + tests)

**Files to change:**
- `app/api/jobs.py`
- `app/api/routes.py`  
- `app/analyzer/motion.py`
- `tests/test_jobs.py`
- `tests/test_api.py`

**jobs.py changes:**
1. Add `"cancelled": False` to the record created in `create()`
2. Add a `cancel(job_id: str) -> None` function that sets `cancelled=True` and `status="cancelled"` under the lock (no-op if unknown id)

**routes.py changes:**
1. Add module-level `class _Cancelled(Exception): pass`
2. In BOTH `detect` and `export` background `run()` closures, replace the inline lambda progress callbacks with a checking callback:
   ```python
   def _cb(f):
       rec = jobs.get(job_id)
       if rec and rec["cancelled"]:
           raise _Cancelled()
       jobs.update(job_id, progress=f)
   ```
3. Catch `_Cancelled` separately (before the broad `except Exception`) and call `jobs.update(job_id, status="cancelled")`
4. Add `POST /api/jobs/{job_id}/cancel` endpoint:
   - Unknown id → `HTTPException(404)`
   - Known id → call `jobs.cancel(job_id)` (which sets cancelled+status), return the updated record

**motion.py changes:**
- Wrap the frame-reading loop so `cap.release()` is called in a `finally` block (currently it's called only at normal loop end — a callback raising mid-loop would leak the VideoCapture)
- Do NOT change the function signature or return type

**tests/test_jobs.py new tests:**
- `test_create_has_cancelled_false`: newly created job has `cancelled == False`
- `test_cancel_sets_cancelled_true`: after `jobs.cancel(jid)`, `jobs.get(jid)["cancelled"] == True` and `jobs.get(jid)["status"] == "cancelled"`  
- `test_cancel_unknown_is_noop`: `jobs.cancel("nope")` does not raise, `jobs.get("nope")` is None

**tests/test_api.py new tests:**
- `test_cancel_unknown_job_404`: `POST /api/jobs/doesnotexist/cancel` → 404
- `test_cancel_sets_status`: create a job via `POST /api/detect` (with `sample_video` fixture and `tmp_path` + `monkeypatch`), immediately `POST /api/jobs/{job_id}/cancel` — assert response is 200, `cancelled == True`, `status == "cancelled"`. This test must be NON-racy: assert the endpoint's own response, not thread-stop timing.

### Task 2 — Frontend cancel button + flash fix + play-per-rally

**Files to change:**
- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/components/Player.tsx`
- `frontend/src/components/RallyList.tsx`

**api.ts:**
- Add: `export async function cancelJob(jobId: string): Promise<void>` → POST to `/api/jobs/${jobId}/cancel`, throw on non-OK with server detail (same pattern as other functions using `postJSON`)

**App.tsx — Cancel button:**
- In the detecting view (the block that shows BallLoader + ProgressBar), add a secondary Cancel button below the progress bar
- Style: `border border-[var(--line)] text-[var(--muted)] hover:text-[var(--ink)]` — NOT lime/accent
- On click: call `await cancelJob(detectJob)`, then reset to confirm screen:
  - Clear `detectJob` (set to null)
  - Clear `analyzing` (set to false)  
  - Clear `videoId` (set to null)
  - Keep `selectedFile` set — so `SelectedVideo` reappears
- IMPORTANT: In `handleAnalyze`, do NOT call `setSelectedFile(null)` — keep `selectedFile` set through the analysis flow. This fixes the upload→detect flash issue too.

**App.tsx — Flash fix:**
- The detecting view condition must be: `analyzing || (detectJob && detect.status === "running")`
- The review UI (Player/Timeline/Controls/RallyList) must ONLY render when: `videoId && !detectJob && !analyzing && rallies.length > 0` — actually use `videoId && !detectJob` with the rallies conditional inside, but make sure `analyzing` also gates it out
- Actually: the current condition `videoId && !detectJob` already gates the review UI once the job completes. The issue is `setSelectedFile(null)` being called in handleAnalyze before the job starts — removing that call fixes the brief flash where neither SelectedVideo nor detecting view shows.
- Show detecting view whenever `analyzing || detectJob` (regardless of detect.status) to avoid any flash

**Player.tsx — playSegment:**
- Extend `PlayerHandle` interface with: `playSegment(start: number, end: number): void`
- Implementation in `useImperativeHandle`:
  ```typescript
  playSegment(start, end) {
    if (!v.current) return;
    // clear any previous segment listener
    if (segListenerRef.current) {
      v.current.removeEventListener("timeupdate", segListenerRef.current);
      segListenerRef.current = null;
    }
    v.current.currentTime = start;
    const listener = () => {
      if (v.current && v.current.currentTime >= end) {
        v.current.pause();
        v.current.removeEventListener("timeupdate", listener);
        segListenerRef.current = null;
      }
    };
    segListenerRef.current = listener;
    v.current.addEventListener("timeupdate", listener);
    v.current.play();
  }
  ```
- Add `const segListenerRef = useRef<((e: Event) => void) | null>(null)` inside the component
- Keep existing `seekTo` and `play` unchanged

**RallyList.tsx — per-rally Play button:**
- Add `onPlay: (rally: Rally) => void` to the props interface
- On each rally row, add a Play icon button (from `lucide-react`, use the `Play` icon)
- Place it between the checkbox and the existing jump-to button  
- Style: `text-[var(--teal)] hover:text-[var(--accent)]` with `p-1 rounded focus-visible:outline-2 focus-visible:outline-[var(--teal)]`
- On click: call `onPlay(r)` (the rally object, not the index)
- Every prop must be used (strict TS)

**App.tsx — wire onPlay:**
- Pass to RallyList: `onPlay={(r) => player.current?.playSegment(r.start, r.end)}`
- (The ref is named `player` in App.tsx)

## Verification

**Backend:** `source .venv/bin/activate && pytest -v` → all green

**Frontend:** from `frontend/`:
- `npm run build` → 0 TS errors
- `npm run test` → all tests pass (existing App test "no-auto-analyze" must still pass; keeping `selectedFile` set through analysis must not break it)
