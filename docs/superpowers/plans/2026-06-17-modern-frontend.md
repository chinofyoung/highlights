# Modern Frontend (Vite + React) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the vanilla-JS review UI with a modern Vite + React + TS + Tailwind SPA served by FastAPI, add real progress feedback for detection/export, and add per-rally drag-to-trim.

**Architecture:** Backend gains an in-memory job registry; `detect`/`export` run in background threads and report progress via callbacks; the frontend polls `GET /api/jobs/{id}`. The React SPA builds to `frontend/dist/`, which the existing FastAPI StaticFiles mount serves — normal use stays `uvicorn app.main:app`.

**Tech Stack:** Backend: FastAPI, stdlib `threading` (no new deps). Frontend: Vite 6, React 18, TypeScript 5, Tailwind CSS 4, lucide-react, Vitest + React Testing Library.

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

## File Structure

```
highlights/
  app/
    api/
      jobs.py                 # NEW: in-memory job registry (thread-safe)
      routes.py               # MODIFY: detect/export → background jobs; GET /api/jobs/{id}
    analyzer/
      motion.py               # MODIFY: optional progress_callback
      pipeline.py             # MODIFY: optional progress_callback, forwarded
    exporter/
      ffmpeg.py               # MODIFY: optional progress_callback
    main.py                   # MODIFY (Task 11): static mount → frontend/dist
    web/                      # DELETE (Task 11)
  tests/
    test_jobs.py              # NEW
    test_progress.py          # NEW
    test_api.py               # MODIFY (Task 4): job flow
  frontend/                   # NEW Vite project
    package.json
    vite.config.ts
    tsconfig.json
    tsconfig.node.json
    index.html
    src/
      main.tsx
      index.css
      types.ts
      api.ts
      useJob.ts
      timeline-math.ts
      App.tsx
      components/
        ProgressBar.tsx
        Player.tsx
        UploadView.tsx
        RallyList.tsx
        Controls.tsx
        ThemeToggle.tsx
        ResultPanel.tsx
        Timeline.tsx
      test/
        setup.ts
        api.test.ts
        useJob.test.ts
        timeline-math.test.ts
    dist/                     # build output (generated)
  README.md                   # MODIFY (Task 12)
```

---

## Task 1: Job registry (backend)

**Files:**
- Create: `app/api/jobs.py`
- Test: `tests/test_jobs.py`

**Interfaces:**
- Produces in `app/api/jobs.py`:
  - `def create() -> str` — returns a new `job_id` (uuid hex, 12 chars); initial record `{"status":"running","progress":0.0,"result":None,"error":None}`.
  - `def update(job_id: str, *, progress: float | None = None, status: str | None = None, result: dict | None = None, error: str | None = None) -> None` — mutates only provided fields; no-op if job_id unknown.
  - `def get(job_id: str) -> dict | None` — returns a copy of the record, or None.
  - Thread-safe via a module-level `threading.Lock`.

- [ ] **Step 1: Write failing tests `tests/test_jobs.py`**

```python
from app.api import jobs


def test_create_returns_running_job():
    jid = jobs.create()
    rec = jobs.get(jid)
    assert rec["status"] == "running"
    assert rec["progress"] == 0.0
    assert rec["result"] is None and rec["error"] is None


def test_update_sets_fields():
    jid = jobs.create()
    jobs.update(jid, progress=0.5)
    assert jobs.get(jid)["progress"] == 0.5
    jobs.update(jid, status="done", result={"rallies": []}, progress=1.0)
    rec = jobs.get(jid)
    assert rec["status"] == "done" and rec["result"] == {"rallies": []}


def test_get_returns_copy_not_reference():
    jid = jobs.create()
    rec = jobs.get(jid)
    rec["progress"] = 9.9
    assert jobs.get(jid)["progress"] == 0.0


def test_update_unknown_job_is_noop():
    jobs.update("nope", progress=1.0)  # must not raise
    assert jobs.get("nope") is None


def test_concurrent_updates_are_safe():
    import threading
    jid = jobs.create()
    def bump():
        for _ in range(100):
            cur = jobs.get(jid)["progress"]
            jobs.update(jid, progress=cur)
    threads = [threading.Thread(target=bump) for _ in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert jobs.get(jid)["status"] == "running"  # no crash / corruption
```

- [ ] **Step 2: Run, expect FAIL**

Run: `source .venv/bin/activate && pytest tests/test_jobs.py -v`
Expected: FAIL (module not defined).

- [ ] **Step 3: Implement `app/api/jobs.py`**

```python
import threading
import uuid

_LOCK = threading.Lock()
_JOBS: dict[str, dict] = {}


def create() -> str:
    job_id = uuid.uuid4().hex[:12]
    with _LOCK:
        _JOBS[job_id] = {"status": "running", "progress": 0.0,
                         "result": None, "error": None}
    return job_id


def update(job_id: str, *, progress: float | None = None,
           status: str | None = None, result: dict | None = None,
           error: str | None = None) -> None:
    with _LOCK:
        rec = _JOBS.get(job_id)
        if rec is None:
            return
        if progress is not None:
            rec["progress"] = progress
        if status is not None:
            rec["status"] = status
        if result is not None:
            rec["result"] = result
        if error is not None:
            rec["error"] = error


def get(job_id: str) -> dict | None:
    with _LOCK:
        rec = _JOBS.get(job_id)
        return dict(rec) if rec is not None else None
```

- [ ] **Step 4: Run, expect PASS**

Run: `source .venv/bin/activate && pytest tests/test_jobs.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Checkpoint** — `source .venv/bin/activate && pytest -v`. Confirm green (29 passed).

---

## Task 2: Progress callbacks — motion + pipeline (backend)

**Files:**
- Modify: `app/analyzer/motion.py`, `app/analyzer/pipeline.py`
- Test: `tests/test_progress.py` (motion portion)

**Interfaces:**
- Consumes: existing `motion_energy`, `analyze` behavior.
- Produces:
  - `motion_energy(video_path: str, sample_fps: int, progress_callback=None) -> np.ndarray` — when `progress_callback` is given and the total frame count is known (>0), calls `progress_callback(fraction)` periodically with non-decreasing `fraction` in `[0,1]`. Default `None` → unchanged behavior.
  - `analyze(video_id: str, video_path: str, params, progress_callback=None) -> list[dict]` — forwards a scaled callback to `motion_energy` (motion mapped to 0–0.9), then calls `progress_callback(1.0)` after caching. Default `None` → unchanged.

- [ ] **Step 1: Write failing tests `tests/test_progress.py`**

```python
import numpy as np
from app.config import DetectionParams
from app import workdir
from app.analyzer import motion, pipeline
from tests.conftest import requires_ffmpeg


@requires_ffmpeg
def test_motion_reports_monotonic_progress(sample_video):
    seen = []
    motion.motion_energy(sample_video, sample_fps=8,
                         progress_callback=lambda f: seen.append(f))
    assert seen, "callback was never called"
    assert all(0.0 <= f <= 1.0 for f in seen)
    assert seen == sorted(seen)               # non-decreasing
    assert seen[-1] <= 1.0


@requires_ffmpeg
def test_motion_without_callback_unchanged(sample_video):
    e = motion.motion_energy(sample_video, sample_fps=8)
    assert len(e) >= 40                        # same as before


@requires_ffmpeg
def test_analyze_reports_progress_ending_at_one(tmp_path, monkeypatch, sample_video):
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)
    seen = []
    pipeline.analyze("vidp", sample_video, DetectionParams(),
                     progress_callback=lambda f: seen.append(f))
    assert seen and seen[-1] == 1.0
    assert all(0.0 <= f <= 1.0 for f in seen)
    assert seen == sorted(seen)
```

- [ ] **Step 2: Run, expect FAIL**

Run: `source .venv/bin/activate && pytest tests/test_progress.py -v`
Expected: FAIL (unexpected keyword `progress_callback`).

- [ ] **Step 3: Modify `app/analyzer/motion.py`** — replace the function with:

```python
import cv2
import numpy as np


def motion_energy(video_path: str, sample_fps: int, progress_callback=None) -> np.ndarray:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")
    src_fps = cap.get(cv2.CAP_PROP_FPS) or sample_fps
    step = max(1, int(round(src_fps / sample_fps)))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    energies = []
    prev = None
    idx = 0
    last_reported = -1.0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % step == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, (160, 120))
            if prev is None:
                energies.append(0.0)
            else:
                energies.append(float(np.mean(np.abs(gray.astype(np.int16) -
                                                      prev.astype(np.int16)))))
            prev = gray
        idx += 1
        if progress_callback is not None and total > 0 and idx % 30 == 0:
            frac = min(1.0, idx / total)
            if frac > last_reported:
                last_reported = frac
                progress_callback(frac)
    cap.release()
    if progress_callback is not None and total > 0 and last_reported < 1.0:
        progress_callback(1.0)
    return np.asarray(energies, dtype=float)
```

- [ ] **Step 4: Modify `app/analyzer/pipeline.py`** — change `analyze` to accept and forward the callback (leave `_resample` and `resegment` untouched):

```python
def analyze(video_id: str, video_path: str, params: DetectionParams,
            progress_callback=None) -> list[dict]:
    hop = 1.0 / params.sample_fps
    motion_cb = None
    if progress_callback is not None:
        motion_cb = lambda f: progress_callback(min(0.9, f * 0.9))
    motion = motion_mod.motion_energy(video_path, params.sample_fps,
                                      progress_callback=motion_cb)

    wav = str(workdir.video_dir(video_id) / "audio.wav")
    audio_mod.extract_wav(video_path, wav)
    audio = audio_mod.audio_energy(wav, hop_seconds=hop)
    audio = _resample(audio, len(motion))

    workdir.save_signals(video_id, motion, audio, hop)
    result = resegment(video_id, params)
    if progress_callback is not None:
        progress_callback(1.0)
    return result
```

- [ ] **Step 5: Run, expect PASS**

Run: `source .venv/bin/activate && pytest tests/test_progress.py -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Checkpoint** — `source .venv/bin/activate && pytest -v`. Confirm green (32 passed; existing motion/pipeline tests still pass because the new param defaults to None).

---

## Task 3: Progress callback — exporter (backend)

**Files:**
- Modify: `app/exporter/ffmpeg.py`
- Test: `tests/test_progress.py` (exporter portion — append)

**Interfaces:**
- Produces: `export(src: str, ranges: list[dict], out_dir: str, progress_callback=None) -> dict` — reports `progress = clips_done / (len(ranges) + 1)` after each clip, then `1.0` after concat. Default `None` → unchanged. `cut_clip`/`concat_clips` unchanged.

- [ ] **Step 1: Append failing test to `tests/test_progress.py`**

```python
from app.exporter import ffmpeg as exporter


@requires_ffmpeg
def test_export_reports_progress(sample_video, tmp_path):
    seen = []
    exporter.export(sample_video,
                    [{"start": 0.5, "end": 2.0}, {"start": 3.0, "end": 5.0}],
                    str(tmp_path), progress_callback=lambda f: seen.append(f))
    assert seen and seen[-1] == 1.0
    assert all(0.0 <= f <= 1.0 for f in seen)
    assert seen == sorted(seen)


@requires_ffmpeg
def test_export_empty_ranges_no_progress_crash(sample_video, tmp_path):
    res = exporter.export(sample_video, [], str(tmp_path),
                          progress_callback=lambda f: None)
    assert res == {"clips": [], "stitched": None}
```

- [ ] **Step 2: Run, expect FAIL**

Run: `source .venv/bin/activate && pytest tests/test_progress.py -k export -v`
Expected: FAIL (unexpected keyword `progress_callback`).

- [ ] **Step 3: Modify `export` in `app/exporter/ffmpeg.py`** (keep `cut_clip` and `concat_clips` as-is):

```python
def export(src: str, ranges: list[dict], out_dir: str,
           progress_callback=None) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    if not ranges:
        return {"clips": [], "stitched": None}
    total = len(ranges) + 1            # clips + concat step
    clips = []
    for i, r in enumerate(ranges, start=1):
        clip_path = str(out / f"clip_{i:03d}.mp4")
        cut_clip(src, float(r["start"]), float(r["end"]), clip_path)
        clips.append(clip_path)
        if progress_callback is not None:
            progress_callback(i / total)
    stitched = str(out / "highlights.mp4")
    concat_clips(clips, stitched)
    if progress_callback is not None:
        progress_callback(1.0)
    return {"clips": clips, "stitched": stitched}
```

- [ ] **Step 4: Run, expect PASS**

Run: `source .venv/bin/activate && pytest tests/test_progress.py -v`
Expected: PASS (5 tests in file).

- [ ] **Step 5: Checkpoint** — `source .venv/bin/activate && pytest -v`. Confirm green (34 passed; existing exporter tests unaffected).

---

## Task 4: Async job endpoints (backend)

**Files:**
- Modify: `app/api/routes.py`
- Test: `tests/test_api.py` (rewrite the detect/export flow tests)

**Interfaces:**
- Consumes: `jobs.create/update/get`, `pipeline.analyze(..., progress_callback=)`, `exporter.export(..., progress_callback=)`, existing `_require`, `_params`, `state`.
- Produces:
  - `POST /api/detect` `{video_id, params?}` → `{"job_id": str}` (runs `analyze` in a background thread).
  - `POST /api/export` `{video_id, ranges}` → `{"job_id": str}` (runs `export` in a background thread).
  - `GET /api/jobs/{job_id}` → job record; 404 if unknown.
  - `POST /api/resegment`, `POST /api/upload`, `GET /api/video/{id}` unchanged.

- [ ] **Step 1: Rewrite the flow tests in `tests/test_api.py`** — replace `test_full_flow` with the job-based version below; keep `test_upload_rejects_non_video` and `test_params_ignores_unknown_keys` unchanged. Add a polling helper.

```python
import time

def _poll(client, job_id, timeout=60.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        rec = client.get(f"/api/jobs/{job_id}").json()
        if rec["status"] in ("done", "error"):
            return rec
        time.sleep(0.2)
    raise AssertionError("job did not finish in time")


@requires_ffmpeg
def test_full_flow_jobs(sample_video, tmp_path, monkeypatch):
    from app import workdir
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)
    client = _client()

    with open(sample_video, "rb") as f:
        up = client.post("/api/upload", files={"file": ("m.mp4", f, "video/mp4")})
    assert up.status_code == 200
    vid = up.json()["video_id"]

    det = client.post("/api/detect", json={"video_id": vid,
                      "params": {"threshold": 0.4, "min_rally_seconds": 1.0}})
    assert det.status_code == 200
    job_id = det.json()["job_id"]
    rec = _poll(client, job_id)
    assert rec["status"] == "done"
    assert isinstance(rec["result"]["rallies"], list)
    assert rec["progress"] == 1.0

    exp = client.post("/api/export", json={"video_id": vid,
                      "ranges": [{"start": 0.5, "end": 2.0}]})
    assert exp.status_code == 200
    erec = _poll(client, exp.json()["job_id"])
    assert erec["status"] == "done"
    assert erec["result"]["stitched"] is not None


def test_unknown_job_404():
    client = _client()
    assert client.get("/api/jobs/doesnotexist").status_code == 404
```

- [ ] **Step 2: Run, expect FAIL**

Run: `source .venv/bin/activate && pytest tests/test_api.py -v`
Expected: FAIL (detect returns rallies/no job_id; `/api/jobs` route missing).

- [ ] **Step 3: Modify `app/api/routes.py`** — add the import, the job endpoints, and convert detect/export to background threads. Add near the existing imports:

```python
import threading
from fastapi import BackgroundTasks  # (optional import; threads used directly below)
from app.api import jobs
```

Replace the existing `detect` and `export` handlers with:

```python
@router.post("/detect")
def detect(body: DetectBody):
    info = _require(body.video_id)
    params = _params(body.params)
    job_id = jobs.create()

    def run():
        try:
            rallies = pipeline.analyze(
                body.video_id, info["path"], params,
                progress_callback=lambda f: jobs.update(job_id, progress=f),
            )
            jobs.update(job_id, status="done", progress=1.0,
                        result={"rallies": rallies})
        except Exception as e:  # noqa: BLE001 - surface to client as job error
            jobs.update(job_id, status="error", error=str(e))

    threading.Thread(target=run, daemon=True).start()
    return {"job_id": job_id}


@router.post("/export")
def export(body: ExportBody):
    info = _require(body.video_id)
    out_dir = str(workdir.video_dir(body.video_id) / "output")
    job_id = jobs.create()

    def run():
        try:
            result = exporter.export(
                info["path"], body.ranges, out_dir,
                progress_callback=lambda f: jobs.update(job_id, progress=f),
            )
            jobs.update(job_id, status="done", progress=1.0, result=result)
        except Exception as e:  # noqa: BLE001
            jobs.update(job_id, status="error", error=str(e))

    threading.Thread(target=run, daemon=True).start()
    return {"job_id": job_id}


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    rec = jobs.get(job_id)
    if rec is None:
        raise HTTPException(404, "Unknown job_id")
    return rec
```

- [ ] **Step 4: Run, expect PASS**

Run: `source .venv/bin/activate && pytest tests/test_api.py -v`
Expected: PASS (full-flow-jobs, unknown-job-404, upload-reject, params-ignore).

- [ ] **Step 5: Checkpoint** — `source .venv/bin/activate && pytest -v`. Confirm green (whole backend suite). Backend is now job-based.

---

## Task 5: Frontend scaffold (Vite + React + TS + Tailwind)

**Files:**
- Create: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/tsconfig.node.json`, `frontend/index.html`, `frontend/src/main.tsx`, `frontend/src/index.css`, `frontend/src/App.tsx` (placeholder), `frontend/src/test/setup.ts`

**Interfaces:**
- Produces a runnable Vite project: `npm run dev` (port 5173, proxies `/api` → 8000), `npm run build` (→ `dist/`), `npm run test` (Vitest). Tailwind 4 active with class-based dark mode.

- [ ] **Step 1: Create `frontend/package.json`**

```json
{
  "name": "highlights-frontend",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run"
  },
  "dependencies": {
    "lucide-react": "^0.460.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@tailwindcss/vite": "^4.0.0",
    "@testing-library/jest-dom": "^6.4.0",
    "@testing-library/react": "^16.0.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "jsdom": "^25.0.0",
    "tailwindcss": "^4.0.0",
    "typescript": "^5.5.0",
    "vite": "^6.0.0",
    "vitest": "^2.1.0"
  }
}
```

- [ ] **Step 2: Create config files**

`frontend/vite.config.ts`:
```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: { "/api": "http://localhost:8000" },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
  },
});
```

`frontend/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

`frontend/tsconfig.node.json`:
```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "noEmit": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 3: Create `frontend/index.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Pickleball Highlights</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 4: Create `frontend/src/index.css`** (Tailwind 4 + class-based dark variant)

```css
@import "tailwindcss";

@custom-variant dark (&:where(.dark, .dark *));

:root { color-scheme: light dark; }
body { margin: 0; }
```

- [ ] **Step 5: Create `frontend/src/main.tsx`**

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

- [ ] **Step 6: Create placeholder `frontend/src/App.tsx`**

```tsx
export default function App() {
  return <div className="p-8 text-2xl font-bold">Pickleball Highlights</div>;
}
```

- [ ] **Step 7: Create `frontend/src/test/setup.ts`**

```ts
import "@testing-library/jest-dom";
```

- [ ] **Step 8: Install and verify build + dev**

Run (from `frontend/`):
```bash
cd frontend && npm install
npm run build
```
Expected: install succeeds; `npm run build` produces `frontend/dist/index.html` and assets with no TypeScript errors. (If a pinned version fails to resolve, install the latest compatible and note it in the report.)

Then verify dev serving + proxy (backend must be running):
```bash
# in repo root, separate shell: source .venv/bin/activate && uvicorn app.main:app
cd frontend && (npm run dev &) && sleep 4
curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/   # expect 200
# stop the dev server afterwards (kill the vite process)
```

- [ ] **Step 9: Checkpoint** — `cd frontend && npm run build` succeeds and `npm run test` runs (0 tests so far is fine: it should exit 0 or report "no test files"; if Vitest errors on no tests, that's acceptable until Task 6 adds tests).

---

## Task 6: API client + types (frontend)

**Files:**
- Create: `frontend/src/types.ts`, `frontend/src/api.ts`, `frontend/src/test/api.test.ts`

**Interfaces:**
- Produces:
  - `types.ts`: `Rally {start:number; end:number; confidence:number; included:boolean}`, `JobRecord {status:"running"|"done"|"error"; progress:number; result:any; error:string|null}`, `DetectParams {threshold?:number}`.
  - `api.ts`: `uploadVideo(file:File): Promise<{video_id:string; duration:number}>`, `startDetect(videoId:string, params:DetectParams): Promise<{job_id:string}>`, `startExport(videoId:string, ranges:{start:number;end:number}[]): Promise<{job_id:string}>`, `getJob(jobId:string): Promise<JobRecord>`, `resegment(videoId:string, params:DetectParams): Promise<{rallies:Rally[]}>`, `videoUrl(videoId:string): string`. All throw `Error(detail)` on non-OK.

- [ ] **Step 1: Write failing tests `frontend/src/test/api.test.ts`**

```ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import * as api from "../api";

beforeEach(() => { vi.restoreAllMocks(); });

function mockFetch(status: number, body: any) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response);
}

describe("api client", () => {
  it("startDetect posts and returns job_id", async () => {
    global.fetch = mockFetch(200, { job_id: "abc" }) as any;
    const res = await api.startDetect("v1", { threshold: 0.3 });
    expect(res.job_id).toBe("abc");
    expect(global.fetch).toHaveBeenCalledWith(
      "/api/detect",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("throws with server detail on non-OK", async () => {
    global.fetch = mockFetch(400, { detail: "bad video" }) as any;
    await expect(api.uploadVideo(new File([""], "x.txt"))).rejects.toThrow("bad video");
  });

  it("getJob returns the record", async () => {
    global.fetch = mockFetch(200, { status: "done", progress: 1, result: { rallies: [] }, error: null }) as any;
    const rec = await api.getJob("j1");
    expect(rec.status).toBe("done");
  });

  it("videoUrl builds the right path", () => {
    expect(api.videoUrl("v9")).toBe("/api/video/v9");
  });
});
```

- [ ] **Step 2: Run, expect FAIL**

Run: `cd frontend && npx vitest run src/test/api.test.ts`
Expected: FAIL (module/exports missing).

- [ ] **Step 3: Create `frontend/src/types.ts`**

```ts
export interface Rally {
  start: number;
  end: number;
  confidence: number;
  included: boolean;
}

export interface JobRecord {
  status: "running" | "done" | "error";
  progress: number;
  result: any;
  error: string | null;
}

export interface DetectParams {
  threshold?: number;
}
```

- [ ] **Step 4: Create `frontend/src/api.ts`**

```ts
import type { JobRecord, Rally, DetectParams } from "./types";

async function postJSON<T>(url: string, body: unknown): Promise<T> {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const detail = (await r.json().catch(() => ({}))).detail;
    throw new Error(detail || r.statusText);
  }
  return r.json();
}

export async function uploadVideo(file: File): Promise<{ video_id: string; duration: number }> {
  const fd = new FormData();
  fd.append("file", file);
  const r = await fetch("/api/upload", { method: "POST", body: fd });
  if (!r.ok) {
    const detail = (await r.json().catch(() => ({}))).detail;
    throw new Error(detail || r.statusText);
  }
  return r.json();
}

export function startDetect(videoId: string, params: DetectParams) {
  return postJSON<{ job_id: string }>("/api/detect", { video_id: videoId, params });
}

export function startExport(videoId: string, ranges: { start: number; end: number }[]) {
  return postJSON<{ job_id: string }>("/api/export", { video_id: videoId, ranges });
}

export async function getJob(jobId: string): Promise<JobRecord> {
  const r = await fetch(`/api/jobs/${jobId}`);
  if (!r.ok) throw new Error("job lookup failed");
  return r.json();
}

export function resegment(videoId: string, params: DetectParams) {
  return postJSON<{ rallies: Rally[] }>("/api/resegment", { video_id: videoId, params });
}

export function videoUrl(videoId: string): string {
  return `/api/video/${videoId}`;
}
```

- [ ] **Step 5: Run, expect PASS**

Run: `cd frontend && npx vitest run src/test/api.test.ts`
Expected: PASS (4 tests).

- [ ] **Step 6: Checkpoint** — `cd frontend && npm run build && npm run test`. Both green.

---

## Task 7: useJob polling hook (frontend)

**Files:**
- Create: `frontend/src/useJob.ts`, `frontend/src/test/useJob.test.ts`

**Interfaces:**
- Consumes: `api.getJob`.
- Produces: `useJob(jobId: string | null): { status, progress, result, error }`. Polls `getJob` every 500ms while a non-null jobId is `running`; stops on `done`/`error` or when jobId becomes null; cleans up the interval on unmount.

- [ ] **Step 1: Write failing tests `frontend/src/test/useJob.test.ts`**

```ts
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useJob } from "../useJob";
import * as api from "../api";

beforeEach(() => { vi.useFakeTimers(); });
afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); });

describe("useJob", () => {
  it("polls until done and exposes result", async () => {
    const seq = [
      { status: "running", progress: 0.5, result: null, error: null },
      { status: "done", progress: 1, result: { rallies: [] }, error: null },
    ];
    vi.spyOn(api, "getJob").mockImplementation(async () => seq.shift() as any ?? seq[0]);

    const { result } = renderHook(() => useJob("j1"));
    await vi.advanceTimersByTimeAsync(600);
    await waitFor(() => expect(result.current.status).toBe("running"));
    await vi.advanceTimersByTimeAsync(600);
    await waitFor(() => expect(result.current.status).toBe("done"));
    expect(result.current.result).toEqual({ rallies: [] });
  });

  it("does nothing when jobId is null", async () => {
    const spy = vi.spyOn(api, "getJob");
    renderHook(() => useJob(null));
    await vi.advanceTimersByTimeAsync(1000);
    expect(spy).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run, expect FAIL**

Run: `cd frontend && npx vitest run src/test/useJob.test.ts`
Expected: FAIL (module missing).

- [ ] **Step 3: Create `frontend/src/useJob.ts`**

```ts
import { useEffect, useState } from "react";
import { getJob } from "./api";
import type { JobRecord } from "./types";

const IDLE: JobRecord = { status: "running", progress: 0, result: null, error: null };

export function useJob(jobId: string | null): JobRecord {
  const [rec, setRec] = useState<JobRecord>(IDLE);

  useEffect(() => {
    if (!jobId) return;
    setRec(IDLE);
    let active = true;

    const tick = async () => {
      try {
        const next = await getJob(jobId);
        if (!active) return;
        setRec(next);
        if (next.status !== "running") clearInterval(id);
      } catch (e) {
        if (!active) return;
        setRec({ status: "error", progress: 0, result: null, error: String(e) });
        clearInterval(id);
      }
    };

    const id = setInterval(tick, 500);
    tick();
    return () => { active = false; clearInterval(id); };
  }, [jobId]);

  return rec;
}
```

- [ ] **Step 4: Run, expect PASS**

Run: `cd frontend && npx vitest run src/test/useJob.test.ts`
Expected: PASS (2 tests).

- [ ] **Step 5: Checkpoint** — `cd frontend && npm run build && npm run test`. Green.

---

## Task 8: Timeline trim math (frontend, pure)

**Files:**
- Create: `frontend/src/timeline-math.ts`, `frontend/src/test/timeline-math.test.ts`

**Interfaces:**
- Produces (pure functions, no DOM):
  - `pxToTime(px:number, trackWidthPx:number, duration:number):number`
  - `clampStart(newStart:number, rally:{start:number;end:number}, prevEnd:number, minGap:number):number` — clamps to `[prevEnd, rally.end - minGap]`.
  - `clampEnd(newEnd:number, rally:{start:number;end:number}, nextStart:number, minGap:number):number` — clamps to `[rally.start + minGap, nextStart]`.
  - `moveBody(deltaT:number, rally:{start:number;end:number}, prevEnd:number, nextStart:number):{start:number;end:number}` — shifts both edges by `deltaT`, preserving length, clamped between `prevEnd` and `nextStart`.
  - `MIN_GAP = 0.2`.

- [ ] **Step 1: Write failing tests `frontend/src/test/timeline-math.test.ts`**

```ts
import { describe, it, expect } from "vitest";
import { pxToTime, clampStart, clampEnd, moveBody, MIN_GAP } from "../timeline-math";

describe("timeline math", () => {
  it("pxToTime maps proportionally", () => {
    expect(pxToTime(50, 100, 10)).toBe(5);
    expect(pxToTime(0, 100, 10)).toBe(0);
  });

  it("clampStart respects prevEnd floor", () => {
    expect(clampStart(1, { start: 5, end: 8 }, 3, MIN_GAP)).toBe(3);
  });

  it("clampStart respects min gap ceiling", () => {
    expect(clampStart(7.9, { start: 5, end: 8 }, 0, MIN_GAP)).toBe(8 - MIN_GAP);
  });

  it("clampEnd respects nextStart ceiling", () => {
    expect(clampEnd(12, { start: 5, end: 8 }, 10, MIN_GAP)).toBe(10);
  });

  it("clampEnd respects min gap floor", () => {
    expect(clampEnd(5.1, { start: 5, end: 8 }, 99, MIN_GAP)).toBe(5 + MIN_GAP);
  });

  it("moveBody preserves length and clamps to prevEnd", () => {
    const r = moveBody(-10, { start: 5, end: 8 }, 2, 99);
    expect(r.end - r.start).toBeCloseTo(3);
    expect(r.start).toBe(2);
  });

  it("moveBody clamps to nextStart", () => {
    const r = moveBody(10, { start: 5, end: 8 }, 0, 12);
    expect(r.end).toBe(12);
    expect(r.end - r.start).toBeCloseTo(3);
  });
});
```

- [ ] **Step 2: Run, expect FAIL**

Run: `cd frontend && npx vitest run src/test/timeline-math.test.ts`
Expected: FAIL (module missing).

- [ ] **Step 3: Create `frontend/src/timeline-math.ts`**

```ts
export const MIN_GAP = 0.2;

export function pxToTime(px: number, trackWidthPx: number, duration: number): number {
  if (trackWidthPx <= 0) return 0;
  return (px / trackWidthPx) * duration;
}

export function clampStart(
  newStart: number,
  rally: { start: number; end: number },
  prevEnd: number,
  minGap: number,
): number {
  return Math.min(Math.max(newStart, prevEnd), rally.end - minGap);
}

export function clampEnd(
  newEnd: number,
  rally: { start: number; end: number },
  nextStart: number,
  minGap: number,
): number {
  return Math.max(Math.min(newEnd, nextStart), rally.start + minGap);
}

export function moveBody(
  deltaT: number,
  rally: { start: number; end: number },
  prevEnd: number,
  nextStart: number,
): { start: number; end: number } {
  const len = rally.end - rally.start;
  let start = rally.start + deltaT;
  start = Math.max(prevEnd, Math.min(start, nextStart - len));
  return { start, end: start + len };
}
```

- [ ] **Step 4: Run, expect PASS**

Run: `cd frontend && npx vitest run src/test/timeline-math.test.ts`
Expected: PASS (7 tests).

- [ ] **Step 5: Checkpoint** — `cd frontend && npm run build && npm run test`. All green (api + useJob + timeline-math).

---

## Task 9: Presentational components (frontend)

**Files:**
- Create: `frontend/src/components/ProgressBar.tsx`, `Player.tsx`, `UploadView.tsx`, `RallyList.tsx`, `Controls.tsx`, `ThemeToggle.tsx`, `ResultPanel.tsx`

**Interfaces:**
- Produces (props are the contract App wires in Task 10):
  - `ProgressBar({label, fraction})`
  - `Player` — `forwardRef<PlayerHandle, {src:string}>`; `PlayerHandle = {seekTo(t):void; play():void}`.
  - `UploadView({onFile, error})`
  - `RallyList({rallies, onToggle, onJump})`
  - `Controls({sensitivity, onSensitivity, onExport, exportDisabled})`
  - `ThemeToggle()`
  - `ResultPanel({result})` where result is `{clips:string[]; stitched:string|null}`.

- [ ] **Step 1: Create `frontend/src/components/ProgressBar.tsx`**

```tsx
export function ProgressBar({ label, fraction }: { label: string; fraction: number }) {
  const pct = Math.round(Math.min(1, Math.max(0, fraction)) * 100);
  return (
    <div className="w-full">
      <div className="mb-1 flex justify-between text-sm text-slate-600 dark:text-slate-300">
        <span>{label}</span><span>{pct}%</span>
      </div>
      <div className="h-3 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
        <div className="h-full rounded-full bg-emerald-500 transition-all duration-200"
             style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create `frontend/src/components/Player.tsx`**

```tsx
import { forwardRef, useImperativeHandle, useRef } from "react";

export interface PlayerHandle { seekTo(t: number): void; play(): void; }

export const Player = forwardRef<PlayerHandle, { src: string }>(({ src }, ref) => {
  const v = useRef<HTMLVideoElement>(null);
  useImperativeHandle(ref, () => ({
    seekTo(t) { if (v.current) v.current.currentTime = t; },
    play() { v.current?.play(); },
  }));
  return (
    <video ref={v} src={src} controls
           className="w-full rounded-lg bg-black shadow-lg" />
  );
});
```

- [ ] **Step 3: Create `frontend/src/components/UploadView.tsx`**

```tsx
import { Upload } from "lucide-react";

export function UploadView({ onFile, error }: { onFile: (f: File) => void; error: string | null }) {
  return (
    <div className="flex flex-col items-center gap-4">
      <label className="flex cursor-pointer flex-col items-center gap-3 rounded-2xl border-2
                        border-dashed border-slate-300 px-12 py-16 transition hover:border-emerald-500
                        dark:border-slate-600">
        <Upload className="h-10 w-10 text-emerald-500" />
        <span className="text-lg font-medium">Drop a match video or click to choose</span>
        <span className="text-sm text-slate-500">Fixed-camera footage works best</span>
        <input type="file" accept="video/*" className="hidden"
               onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])} />
      </label>
      {error && <p className="text-sm text-red-500">{error}</p>}
    </div>
  );
}
```

- [ ] **Step 4: Create `frontend/src/components/RallyList.tsx`**

```tsx
import type { Rally } from "../types";

export function RallyList({ rallies, onToggle, onJump }: {
  rallies: Rally[];
  onToggle: (i: number) => void;
  onJump: (t: number) => void;
}) {
  if (!rallies.length) {
    return <p className="text-sm text-slate-500">No rallies — try raising sensitivity.</p>;
  }
  return (
    <ul className="flex flex-col gap-1">
      {rallies.map((r, i) => (
        <li key={i} className="flex items-center gap-3 rounded-lg px-3 py-2
                               hover:bg-slate-100 dark:hover:bg-slate-800">
          <input type="checkbox" checked={r.included} onChange={() => onToggle(i)}
                 className="h-4 w-4 accent-emerald-500" />
          <button onClick={() => onJump(r.start)} className="flex-1 text-left text-sm">
            Rally {i + 1}: {r.start.toFixed(1)}s – {r.end.toFixed(1)}s
            <span className="ml-2 text-slate-400">conf {r.confidence.toFixed(2)}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}
```

- [ ] **Step 5: Create `frontend/src/components/Controls.tsx`**

```tsx
import { Scissors } from "lucide-react";

export function Controls({ sensitivity, onSensitivity, onExport, exportDisabled }: {
  sensitivity: number;
  onSensitivity: (v: number) => void;
  onExport: () => void;
  exportDisabled: boolean;
}) {
  return (
    <div className="flex flex-wrap items-center gap-6">
      <label className="flex items-center gap-3 text-sm">
        Sensitivity
        <input type="range" min={0} max={1} step={0.05} value={sensitivity}
               onChange={(e) => onSensitivity(parseFloat(e.target.value))}
               className="accent-emerald-500" />
      </label>
      <button onClick={onExport} disabled={exportDisabled}
              className="flex items-center gap-2 rounded-lg bg-emerald-500 px-4 py-2 font-medium
                         text-white transition hover:bg-emerald-600 disabled:opacity-40">
        <Scissors className="h-4 w-4" /> Export
      </button>
    </div>
  );
}
```

- [ ] **Step 6: Create `frontend/src/components/ThemeToggle.tsx`**

```tsx
import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

export function ThemeToggle() {
  const [dark, setDark] = useState(
    () => window.matchMedia("(prefers-color-scheme: dark)").matches,
  );
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);
  return (
    <button onClick={() => setDark((d) => !d)} aria-label="Toggle theme"
            className="rounded-lg p-2 hover:bg-slate-100 dark:hover:bg-slate-800">
      {dark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
    </button>
  );
}
```

- [ ] **Step 7: Create `frontend/src/components/ResultPanel.tsx`**

```tsx
export function ResultPanel({ result }: { result: { clips: string[]; stitched: string | null } }) {
  return (
    <div className="rounded-lg bg-slate-100 p-4 text-sm dark:bg-slate-800">
      <p className="font-medium text-emerald-600 dark:text-emerald-400">Export complete</p>
      {result.stitched && <p className="mt-2 break-all">Stitched: {result.stitched}</p>}
      <p className="mt-2 break-all">Clips: {result.clips.length}</p>
      <ul className="mt-1 list-inside list-disc break-all text-slate-500">
        {result.clips.map((c) => <li key={c}>{c}</li>)}
      </ul>
    </div>
  );
}
```

- [ ] **Step 8: Checkpoint** — `cd frontend && npm run build`. Compiles with no TS errors (unused-locals/params are errors per tsconfig, so every prop must be used). `npm run test` still green.

---

## Task 10: Timeline + App integration (frontend)

**Files:**
- Create: `frontend/src/components/Timeline.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `timeline-math` (pxToTime/clampStart/clampEnd/moveBody/MIN_GAP), all components, `api`, `useJob`, `types`.
- Produces:
  - `Timeline({rallies, duration, onChange, onPreview})` — renders blocks with left/right drag handles + body drag; calls `onChange(index, {start,end})` during drag and `onPreview(t)` to live-seek.
  - `App` — full flow state machine wiring upload → detect job (ProgressBar) → review (Player + Timeline + RallyList + Controls) → export job (ProgressBar) → ResultPanel.

- [ ] **Step 1: Create `frontend/src/components/Timeline.tsx`**

```tsx
import { useRef } from "react";
import type { Rally } from "../types";
import { pxToTime, clampStart, clampEnd, moveBody, MIN_GAP } from "../timeline-math";

type Drag = { index: number; mode: "start" | "end" | "body"; startX: number; orig: Rally } | null;

export function Timeline({ rallies, duration, onChange, onPreview }: {
  rallies: Rally[];
  duration: number;
  onChange: (index: number, next: { start: number; end: number }) => void;
  onPreview: (t: number) => void;
}) {
  const track = useRef<HTMLDivElement>(null);
  const drag = useRef<Drag>(null);

  const onPointerDown = (e: React.PointerEvent, index: number, mode: "start" | "end" | "body") => {
    e.stopPropagation();
    (e.target as Element).setPointerCapture(e.pointerId);
    drag.current = { index, mode, startX: e.clientX, orig: rallies[index] };
  };

  const onPointerMove = (e: React.PointerEvent) => {
    const d = drag.current;
    if (!d || !track.current) return;
    const width = track.current.getBoundingClientRect().width;
    const deltaT = pxToTime(e.clientX - d.startX, width, duration);
    const prevEnd = d.index > 0 ? rallies[d.index - 1].end : 0;
    const nextStart = d.index < rallies.length - 1 ? rallies[d.index + 1].start : duration;

    if (d.mode === "start") {
      const start = clampStart(d.orig.start + deltaT, d.orig, prevEnd, MIN_GAP);
      onChange(d.index, { start, end: d.orig.end });
      onPreview(start);
    } else if (d.mode === "end") {
      const end = clampEnd(d.orig.end + deltaT, d.orig, nextStart, MIN_GAP);
      onChange(d.index, { start: d.orig.start, end });
      onPreview(end);
    } else {
      const moved = moveBody(deltaT, d.orig, prevEnd, nextStart);
      onChange(d.index, moved);
      onPreview(moved.start);
    }
  };

  const onPointerUp = () => { drag.current = null; };

  return (
    <div ref={track} onPointerMove={onPointerMove} onPointerUp={onPointerUp}
         className="relative h-12 w-full rounded-lg bg-slate-200 dark:bg-slate-700"
         style={{ touchAction: "none" }}>
      {rallies.map((r, i) => {
        const left = (100 * r.start) / duration;
        const width = (100 * (r.end - r.start)) / duration;
        return (
          <div key={i}
               className={`absolute top-0 h-full rounded ${r.included ? "bg-emerald-500/80" : "bg-slate-400/60"}`}
               style={{ left: `${left}%`, width: `${width}%` }}
               onPointerDown={(e) => onPointerDown(e, i, "body")}
               onClick={() => onPreview(r.start)}>
            <div onPointerDown={(e) => onPointerDown(e, i, "start")}
                 className="absolute left-0 top-0 h-full w-2 cursor-ew-resize rounded-l bg-white/70" />
            <div onPointerDown={(e) => onPointerDown(e, i, "end")}
                 className="absolute right-0 top-0 h-full w-2 cursor-ew-resize rounded-r bg-white/70" />
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 2: Replace `frontend/src/App.tsx`** with the full flow

```tsx
import { useRef, useState } from "react";
import * as api from "./api";
import { useJob } from "./useJob";
import type { Rally } from "./types";
import { UploadView } from "./components/UploadView";
import { ProgressBar } from "./components/ProgressBar";
import { Player, type PlayerHandle } from "./components/Player";
import { Timeline } from "./components/Timeline";
import { RallyList } from "./components/RallyList";
import { Controls } from "./components/Controls";
import { ThemeToggle } from "./components/ThemeToggle";
import { ResultPanel } from "./components/ResultPanel";

export default function App() {
  const [videoId, setVideoId] = useState<string | null>(null);
  const [duration, setDuration] = useState(0);
  const [rallies, setRallies] = useState<Rally[]>([]);
  const [sensitivity, setSensitivity] = useState(0.5);
  const [detectJob, setDetectJob] = useState<string | null>(null);
  const [exportJob, setExportJob] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const player = useRef<PlayerHandle>(null);

  const detect = useJob(detectJob);
  const exp = useJob(exportJob);

  // detect job completed → load rallies
  if (detect.status === "done" && detectJob && detect.result) {
    const rs: Rally[] = detect.result.rallies.map((r: any) => ({ ...r, included: true }));
    setRallies(rs);
    setDetectJob(null);
  }

  async function handleFile(file: File) {
    setUploadError(null);
    try {
      const up = await api.uploadVideo(file);
      setVideoId(up.video_id);
      setDuration(up.duration);
      const { job_id } = await api.startDetect(up.video_id, { threshold: 1 - sensitivity });
      setDetectJob(job_id);
    } catch (e) {
      setUploadError(String(e instanceof Error ? e.message : e));
    }
  }

  async function handleSensitivity(v: number) {
    setSensitivity(v);
    if (!videoId) return;
    try {
      const { rallies: rs } = await api.resegment(videoId, { threshold: 1 - v });
      setRallies(rs.map((r) => ({ ...r, included: true })));
    } catch { /* surfaced via UI elsewhere if needed */ }
  }

  async function handleExport() {
    if (!videoId) return;
    const ranges = rallies.filter((r) => r.included).map((r) => ({ start: r.start, end: r.end }));
    const { job_id } = await api.startExport(videoId, ranges);
    setExportJob(job_id);
  }

  const includedCount = rallies.filter((r) => r.included).length;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-900 dark:text-slate-100">
      <header className="flex items-center justify-between px-8 py-5">
        <h1 className="text-xl font-bold">🎾 Pickleball Highlights</h1>
        <ThemeToggle />
      </header>

      <main className="mx-auto flex max-w-3xl flex-col gap-6 px-8 pb-16">
        {!videoId && <UploadView onFile={handleFile} error={uploadError} />}

        {detectJob && detect.status === "running" && (
          <ProgressBar label="Detecting rallies…" fraction={detect.progress} />
        )}
        {detect.status === "error" && (
          <p className="text-sm text-red-500">Detection failed: {detect.error}</p>
        )}

        {videoId && !detectJob && (
          <>
            <Player ref={player} src={api.videoUrl(videoId)} />
            <Timeline rallies={rallies} duration={duration}
                      onChange={(i, next) => setRallies((rs) =>
                        rs.map((r, j) => (j === i ? { ...r, ...next } : r)))}
                      onPreview={(t) => { player.current?.seekTo(t); }} />
            <Controls sensitivity={sensitivity} onSensitivity={handleSensitivity}
                      onExport={handleExport} exportDisabled={includedCount === 0} />
            <RallyList rallies={rallies}
                       onToggle={(i) => setRallies((rs) =>
                         rs.map((r, j) => (j === i ? { ...r, included: !r.included } : r)))}
                       onJump={(t) => { player.current?.seekTo(t); player.current?.play(); }} />

            {exportJob && exp.status === "running" && (
              <ProgressBar label="Exporting…" fraction={exp.progress} />
            )}
            {exp.status === "error" && (
              <p className="text-sm text-red-500">Export failed: {exp.error}</p>
            )}
            {exp.status === "done" && exp.result && <ResultPanel result={exp.result} />}
          </>
        )}
      </main>
    </div>
  );
}
```

- [ ] **Step 3: Build to verify it compiles**

Run: `cd frontend && npm run build`
Expected: PASS — no TypeScript errors, `dist/` regenerated.

- [ ] **Step 4: Run all frontend tests**

Run: `cd frontend && npm run test`
Expected: PASS (api + useJob + timeline-math; 13 tests).

- [ ] **Step 5: Apply visual polish with the frontend-design skill**

Invoke the `frontend-design` skill to refine the aesthetic (typography scale, spacing rhythm, accent palette, the timeline as centerpiece, light/dark balance) so it reads as distinctive rather than templated. Keep all component prop contracts and the flow unchanged; only adjust classes/markup styling. Re-run `npm run build` and `npm run test` afterward; both must stay green.

- [ ] **Step 6: Checkpoint** — `cd frontend && npm run build && npm run test`. Green.

---

## Task 11: Serve the SPA from FastAPI + remove old UI

**Files:**
- Modify: `app/main.py`
- Delete: `app/web/index.html`, `app/web/app.js`, `app/web/style.css`

**Interfaces:**
- Consumes: built `frontend/dist/`.
- Produces: FastAPI serving the SPA at `/` with `/api/*` still routed.

- [ ] **Step 1: Modify `app/main.py`** — repoint the static mount

```python
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.deps import require_ffmpeg
from app.api.routes import router

app = FastAPI(title="Pickleball Highlights")


@app.on_event("startup")
def _check_ffmpeg() -> None:
    require_ffmpeg()


app.include_router(router)

WEB_DIR = Path(__file__).parent.parent / "frontend" / "dist"
if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
```

- [ ] **Step 2: Delete the old vanilla UI**

Remove `app/web/index.html`, `app/web/app.js`, `app/web/style.css` (and the `app/web/` directory if empty).

- [ ] **Step 3: Build the frontend so dist exists**

Run: `cd frontend && npm run build`
Expected: `frontend/dist/index.html` present.

- [ ] **Step 4: Verify FastAPI serves the SPA and API together**

Run (repo root):
```bash
source .venv/bin/activate
uvicorn app.main:app --port 8000   # background
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/            # expect 200
curl -s http://localhost:8000/ | grep -c "root"                          # expect >=1 (SPA mount div)
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/jobs/nope   # expect 404 (API not shadowed)
# stop the server
```

- [ ] **Step 5: Backend regression check**

Run: `source .venv/bin/activate && pytest -v`
Expected: full backend suite green.

- [ ] **Step 6: Manual end-to-end verification**

With ffmpeg installed and the server running, open `http://localhost:8000`, upload a real fixed-camera pickleball clip, and confirm: a real progress bar advances during detection; rallies render on the timeline; dragging a rally's handles trims it and the player seeks to the edge; the sensitivity slider changes the rally set; Export shows a progress bar then the result panel with output paths; light/dark toggle works. Note any issues in the report. (No bundled sample match video — this final check needs a real clip.)

- [ ] **Step 7: Checkpoint** — backend `pytest -v` green and `frontend npm run test` green.

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

## Self-Review

**Spec coverage:**
- Vite+React+TS+Tailwind SPA served by FastAPI → Tasks 5, 11. ✓
- Dev proxy + prod static serving → Task 5 (vite proxy), Task 11 (mount). ✓
- Job registry → Task 1. ✓
- Progress callbacks (motion/pipeline/exporter) → Tasks 2, 3. ✓
- Async detect/export endpoints + GET /api/jobs/{id} + resegment stays sync → Task 4. ✓
- Typed api client + types → Task 6. ✓
- useJob polling hook → Task 7. ✓
- Drag-to-trim (math + component) → Tasks 8, 10. ✓
- Progress bar UI for detect + export → Tasks 9, 10. ✓
- Sensitivity = 1 - slider, re-segment replaces trims → Task 10 (App). ✓
- Light/dark, clean & sporty, frontend-design polish → Tasks 5 (dark variant), 9, 10 (step 5). ✓
- Components per spec (UploadView, ProgressBar, Player, Timeline, RallyList, Controls, ThemeToggle, ResultPanel) → Tasks 9, 10. ✓
- Error handling (upload reject, job error, empty rallies, export-disabled) → Tasks 6, 9, 10. ✓
- Remove app/web → Task 11. ✓
- Tests: backend job/progress/api; frontend api/useJob/timeline-math → Tasks 1–4, 6–8. ✓
- README → Task 12. ✓

**Placeholder scan:** No TBD/TODO; every code step contains full code. The frontend-design step (Task 10 Step 5) is an intentional skill invocation, not a code placeholder — component contracts are already fully implemented before it runs.

**Type consistency:** `JobRecord`/`Rally`/`DetectParams` consistent across types.ts, api.ts, useJob.ts, App.tsx. Job record shape matches backend (`status/progress/result/error`). `PlayerHandle` (`seekTo`,`play`) consistent between Player.tsx and App.tsx. Timeline `onChange(index, {start,end})` / `onPreview(t)` consistent between Timeline.tsx and App.tsx. `progress_callback` keyword consistent across motion/pipeline/exporter/routes. detect/export return `{job_id}`; result shapes match what App reads (`result.rallies`, `result.clips/stitched`).

**Note (known minor, deferred):** `App.tsx` sets state during render when a detect job completes (the `if (detect.status === "done" …)` block) — this works in React 18 (triggers an immediate re-render) but an effect would be cleaner. Flagged for the final review to decide; not a blocker for a local single-user tool.
