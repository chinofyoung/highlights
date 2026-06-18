# Modern Frontend (Vite + React) — Design

**Date:** 2026-06-17
**Status:** Approved design, pending implementation plan
**Builds on:** 2026-06-17-pickleball-highlights-design.md (the existing app)

## Summary

Replace the existing vanilla-JS review UI (`app/web/*`) with a modern Vite +
React + TypeScript + Tailwind single-page app, served as static files by the
existing FastAPI backend. The rebuild keeps the same flow (upload → review →
export) but makes it polished and easy to use, adds **real progress feedback**
(so analysis/export never feels stuck), and adds **per-rally drag-to-trim** on
the timeline.

Running the app for normal use stays exactly what it is today:
`uvicorn app.main:app`.

## Goals

- Modern, clean, **clean & sporty** look with system-aware **light + dark** modes.
- **Progress feedback:** a live progress bar for detection and export, driven by
  real backend progress (fraction complete), replacing today's static
  "Detecting rallies…" string.
- **Drag-to-trim:** per-rally start/end handles and body-drag on the timeline,
  the documented v1 follow-up.
- Preserve all existing behavior: upload, rally detection, include/exclude,
  click-to-preview, sensitivity slider, export to clips + stitched video.
- Zero added runtime for normal use — FastAPI serves the built SPA.

## Non-goals (deferred)

- "Best rallies only" ranking/scoring (still deferred).
- Multi-user / hosted deployment.
- Authentication.
- Replacing the detection algorithm (motion + audio is unchanged).

## Architecture

```
DEV:   Vite dev server (:5173)  ──proxy /api/* ──►  FastAPI (:8000)
PROD:  npm run build → frontend/dist/  ──StaticFiles──►  FastAPI (:8000)
```

- A new top-level `frontend/` directory holds the Vite/React/TS project.
- `npm run build` emits `frontend/dist/` (static assets).
- `app/main.py`'s static mount is repointed from `app/web/` to
  `frontend/dist/`. The old `app/web/*` files are deleted.
- **Dev workflow:** run `uvicorn app.main:app` and `npm run dev` together; Vite's
  dev server proxies `/api/*` to `:8000` (configured in `vite.config.ts`), giving
  hot reload while talking to the real backend.
- **Normal use:** build once, then just `uvicorn app.main:app`.

### Dependencies

- Frontend: `react`, `react-dom`, `vite`, `typescript`, `@vitejs/plugin-react`,
  `tailwindcss` (+ `postcss`, `autoprefixer`), `lucide-react` (icons),
  `vitest` + `@testing-library/react` + `jsdom` (tests). No large component
  framework — UI primitives are handcrafted with Tailwind.
- Backend: no new packages (background work uses stdlib `threading`; FastAPI
  already present).

## Backend changes — job-based progress

Today `POST /api/detect` runs analysis synchronously and blocks. To report real
progress, analysis and export become background jobs the frontend polls.

### Job registry (`app/api/jobs.py`, new)

- An in-memory registry mapping `job_id` → job record:
  `{status: "running"|"done"|"error", progress: float (0.0–1.0), result: dict|None, error: str|None}`.
- Functions: `create() -> job_id`, `update(job_id, *, progress=None, status=None,
  result=None, error=None)`, `get(job_id) -> dict|None`.
- Thread-safe via a `threading.Lock` (background threads update it; request
  handlers read it).

### Progress callbacks (analyzer + exporter)

- `app/analyzer/motion.py`: `motion_energy(video_path, sample_fps,
  progress_callback=None)`. The frame-decode loop calls
  `progress_callback(fraction)` periodically (e.g. every ~30 processed frames),
  where `fraction` uses the total frame count from
  `cap.get(cv2.CAP_PROP_FRAME_COUNT)` when available (falls back to no callback
  if the count is unavailable/zero). Default `None` preserves the existing
  signature behavior for all current callers/tests.
- `app/analyzer/pipeline.py`: `analyze(video_id, video_path, params,
  progress_callback=None)` forwards the callback to `motion_energy`. Motion
  decoding is the dominant cost, so motion progress maps to overall detect
  progress; audio extraction/segmentation are fast and reported as the final
  jump to ~1.0.
- `app/exporter/ffmpeg.py`: `export(src, ranges, out_dir, progress_callback=None)`
  reports `progress = clips_done / total` as each clip finishes, then the concat
  step as the final step.

### Endpoints (`app/api/routes.py`)

Changed/added (all existing endpoints otherwise unchanged):

- `POST /api/detect` `{video_id, params?}` → `{job_id}`. Creates a job, spawns a
  background thread running `analyze(..., progress_callback=updater)`; on success
  stores `result = {"rallies": [...]}` and `status="done"`; on exception stores
  `status="error", error=str(e)`.
- `POST /api/export` `{video_id, ranges}` → `{job_id}`. Same pattern; result is
  the exporter dict `{clips, stitched}`.
- `GET /api/jobs/{job_id}` → the job record
  `{status, progress, result, error}`; 404 if unknown.
- `POST /api/resegment` stays **synchronous** (it only reads cached signals and
  is effectively instant) → `{rallies}` as today.
- `POST /api/upload` and `GET /api/video/{video_id}` unchanged.

Note: this changes the `detect`/`export` response contract (now returns a
`job_id` instead of results directly). The frontend is rewritten in lockstep, so
there is no compatibility concern; the existing backend tests for these two
endpoints are updated to assert the job flow.

## Frontend structure

Small, focused modules under `frontend/src/`:

- `api.ts` — typed fetch client: `uploadVideo(file) -> {video_id, duration}`,
  `startDetect(video_id, params) -> {job_id}`, `startExport(video_id, ranges) ->
  {job_id}`, `getJob(job_id) -> JobRecord`, `resegment(video_id, params) ->
  {rallies}`, `videoUrl(video_id) -> string`. Throws on non-OK responses with
  the server `detail`.
- `types.ts` — `Rally {start, end, confidence, included}`, `JobRecord`,
  `DetectionParams` subset.
- `useJob.ts` — hook: given a `job_id`, polls `getJob` every 500ms until
  `status` is `done`/`error`, exposes `{status, progress, result, error}`,
  cleans up the interval on unmount/!done.
- `App.tsx` — top-level state machine: `idle → uploading → detecting → review →
  exporting → done`, holds `videoId`, `duration`, `rallies`, current `job_id`.
- Components:
  - `UploadView.tsx` — drag-drop zone + file picker; shows upload errors.
  - `ProgressBar.tsx` — reusable labeled bar driven by a 0–1 fraction.
  - `Player.tsx` — `<video>` with an imperative `seekTo(t)` / `play()` ref API.
  - `Timeline.tsx` — rally blocks + drag-to-trim (see below).
  - `RallyList.tsx` — list with include/exclude checkbox, jump-to, duration,
    confidence.
  - `Controls.tsx` — sensitivity slider (calls `resegment`) + Export button.
  - `ThemeToggle.tsx` — light/dark/system.
  - `ResultPanel.tsx` — shows exported clip paths + stitched path.

## Drag-to-trim timeline

`Timeline.tsx` renders the video duration as a horizontal track; each rally is an
absolutely-positioned block at `left = start/duration`, `width =
(end-start)/duration` (as percentages).

Interactions (pointer events, no drag library):

- **Left handle:** drag adjusts `start`; clamped to `[prevRally.end ?? 0,
  end - MIN_RALLY_GAP]`.
- **Right handle:** drag adjusts `end`; clamped to `[start + MIN_RALLY_GAP,
  nextRally.start ?? duration]`.
- **Body drag:** moves the whole block, preserving its length, clamped between
  neighbors and `[0, duration]`.
- During any drag, the player live-seeks to the edge being moved so the user sees
  the exact frame.
- Click on a block body (without dragging) = seek to its start and play
  (preview), preserving the existing click-to-preview behavior.

Pixel→time conversion uses the track's measured pixel width
(`getBoundingClientRect`). Trim math is pure and unit-tested independently of the
DOM.

## Sensitivity slider

Keeps the corrected semantics from the current app: higher slider = more
sensitive = more rallies. The control sends `threshold = 1 - sliderValue` to
`resegment`. After re-segmentation, any prior manual trims are replaced by the
new rally set (re-segmenting is a fresh detection pass) — this is expected and
matches today's behavior; the UI notes it.

## Visual direction

Clean & sporty. Tailwind with a single energetic accent color, system-aware
light/dark via a `dark` class toggle (defaulting to system preference), generous
spacing, and the timeline as the visual centerpiece. The frontend-design skill
will be used during implementation to make the result distinctive rather than
templated. Icons from `lucide-react`.

## Error handling

- Upload: non-video rejection shows an inline error (already a backend 400).
- Detect/export jobs: if `status === "error"`, show the `error` message and let
  the user retry; the poller stops.
- Polling: network failure during a poll surfaces an error state rather than
  spinning forever.
- Empty rally set (e.g. very strict sensitivity): timeline shows an empty state
  with guidance to lower sensitivity.
- Export with zero included rallies: Export disabled until at least one rally is
  included.

## Testing

**Backend (pytest, extends existing suite — all 24 current tests stay green):**
- `app/api/jobs.py`: create/update/get transitions; concurrent update safety
  (basic lock test).
- `motion_energy` and `export` invoke `progress_callback` with non-decreasing
  fractions in `[0,1]` (use a recording callback + the existing `sample_video`
  fixture).
- `POST /api/detect` returns a `job_id`, and polling `GET /api/jobs/{id}`
  eventually reports `status="done"` with `result.rallies`; `POST /api/export`
  job likewise yields `result.stitched`.
- Unknown `job_id` → 404.

**Frontend (Vitest + React Testing Library + jsdom):**
- `useJob`: polls until done; stops after done/error; cleans up on unmount
  (fake timers + mocked `getJob`).
- Timeline trim math (pure functions): left/right handle clamping, neighbor
  collision, body-move bounds, pixel↔time conversion.
- `api.ts`: throws on non-OK with server detail (mocked fetch).

## Migration

1. Create `frontend/` Vite project; implement components + tests.
2. Add job registry + progress callbacks + job endpoints to the backend; update
   the two affected backend tests.
3. Repoint `app/main.py` static mount to `frontend/dist/`; delete `app/web/*`.
4. `npm run build`; verify `uvicorn app.main:app` serves the SPA and the full
   flow works.
5. Update `README.md`: add a "Frontend development" section (`npm install`,
   `npm run dev` + proxy, `npm run build`) and note the build step before running.

## Future enhancements (out of scope)

- "Best rallies only" ranking.
- Keyboard shortcuts for trimming.
- Persisting review sessions across restarts.
