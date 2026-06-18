# Cancel Capability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add true background-thread cancellation for detection/export jobs plus a Cancel button in the frontend that returns the user to the confirm screen without losing the selected file.

**Architecture:** Backend adds a `cancelled` flag to the in-memory job store; a `_Cancelled` sentinel exception propagates out of the progress callback when the flag is set; `motion_energy` wraps the frame loop in `try/finally` to guarantee `cap.release()` on any exception. A new `POST /api/jobs/{job_id}/cancel` endpoint flips the flag. The frontend adds a `cancelJob` API helper and a Cancel button that clears only `detectJob`/`analyzing`/`videoId` while keeping `selectedFile` so the confirm screen reappears.

**Tech Stack:** Python 3.11+, FastAPI, OpenCV, threading; React 18, TypeScript (strict), Tailwind, Vitest + Testing Library.

## Global Constraints

- Strict TypeScript — zero TS errors on `npm run build`.
- All 21 existing frontend tests must stay green (`npm run test`).
- Full backend pytest suite must stay green (`pytest -v`, activate `.venv` first).
- No git/commit commands.
- Report output path: `/Users/chinoyoung/Code/highlights/docs/superpowers/plans/briefs-fe/cancel-report.md`
- Reuse CSS design tokens (`--accent`, `--line`, `--muted`, `--ink`, etc.) for new UI.
- `threshold = 1 - sensitivity` convention must be preserved.
- Do NOT change the returned values or signature of `motion_energy`.

---

### Task 1: Backend — Add `cancelled` field to jobs store

**Files:**
- Modify: `app/api/jobs.py`

**Interfaces:**
- Produces:
  - `jobs.create() -> str` — returned record now includes `"cancelled": False`
  - `jobs.cancel(job_id: str) -> None` — sets `cancelled=True` under the lock; no-op if unknown
  - `jobs.get(job_id)` — returned dict now includes `"cancelled"` key

- [ ] **Step 1: Write the failing tests**

In `tests/test_jobs.py`, append at the end:

```python
def test_create_has_cancelled_false():
    jid = jobs.create()
    rec = jobs.get(jid)
    assert rec["cancelled"] is False


def test_cancel_sets_cancelled_true():
    jid = jobs.create()
    jobs.cancel(jid)
    assert jobs.get(jid)["cancelled"] is True


def test_cancel_unknown_is_noop():
    jobs.cancel("does-not-exist")  # must not raise
    assert jobs.get("does-not-exist") is None
```

- [ ] **Step 2: Run the failing tests**

```bash
cd /Users/chinoyoung/Code/highlights && source .venv/bin/activate && pytest tests/test_jobs.py::test_create_has_cancelled_false tests/test_jobs.py::test_cancel_sets_cancelled_true tests/test_jobs.py::test_cancel_unknown_is_noop -v
```

Expected: 3 FAILED (AttributeError / KeyError — `cancelled` does not exist yet).

- [ ] **Step 3: Implement the changes in `app/api/jobs.py`**

Replace the entire file with:

```python
import threading
import uuid

_LOCK = threading.Lock()
_JOBS: dict[str, dict] = {}


def create() -> str:
    job_id = uuid.uuid4().hex[:12]
    with _LOCK:
        _JOBS[job_id] = {
            "status": "running",
            "progress": 0.0,
            "result": None,
            "error": None,
            "cancelled": False,
        }
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


def cancel(job_id: str) -> None:
    """Mark a job as cancelled. No-op if job_id is unknown."""
    with _LOCK:
        rec = _JOBS.get(job_id)
        if rec is not None:
            rec["cancelled"] = True


def get(job_id: str) -> dict | None:
    with _LOCK:
        rec = _JOBS.get(job_id)
        return dict(rec) if rec is not None else None
```

- [ ] **Step 4: Run the new tests plus the full jobs test suite**

```bash
cd /Users/chinoyoung/Code/highlights && source .venv/bin/activate && pytest tests/test_jobs.py -v
```

Expected: All tests PASS (original 5 + new 3 = 8 total).

---

### Task 2: Backend — Fix `motion_energy` VideoCapture leak on callback raise

**Files:**
- Modify: `app/analyzer/motion.py`

**Interfaces:**
- Consumes: existing `motion_energy(video_path, sample_fps, progress_callback)` signature (unchanged)
- Produces: same signature, same return type — but `cap.release()` now runs in `finally` even if `progress_callback` raises

- [ ] **Step 1: Write the failing test**

In `tests/test_jobs.py`, append at the end (we use test_jobs to keep things isolated — or better, create a new dedicated file `tests/test_motion.py`):

Create `tests/test_motion.py`:

```python
import numpy as np
import pytest
from unittest.mock import patch, MagicMock


def test_motion_energy_releases_cap_on_callback_raise(tmp_path):
    """cap.release() must be called even when progress_callback raises."""
    from app.analyzer.motion import motion_energy

    released = []

    class FakeCap:
        def isOpened(self):
            return True

        def get(self, prop):
            import cv2
            if prop == cv2.CAP_PROP_FPS:
                return 30.0
            if prop == cv2.CAP_PROP_FRAME_COUNT:
                return 90  # enough frames to trigger callback
            return 0

        _idx = 0

        def read(self):
            import numpy as np
            self._idx += 1
            if self._idx > 90:
                return False, None
            frame = np.zeros((120, 160, 3), dtype=np.uint8)
            return True, frame

        def release(self):
            released.append(True)

    with patch("cv2.VideoCapture", return_value=FakeCap()):
        with pytest.raises(RuntimeError, match="cancelled"):
            motion_energy(
                "fake.mp4",
                sample_fps=5,
                progress_callback=lambda f: (_ for _ in ()).throw(RuntimeError("cancelled")),
            )

    assert len(released) == 1, "cap.release() must have been called exactly once"
```

- [ ] **Step 2: Run the failing test**

```bash
cd /Users/chinoyoung/Code/highlights && source .venv/bin/activate && pytest tests/test_motion.py::test_motion_energy_releases_cap_on_callback_raise -v
```

Expected: FAILED — `cap.release()` is called 0 times because the current code calls it only after the normal loop exit.

- [ ] **Step 3: Fix `app/analyzer/motion.py` to use `try/finally`**

Replace the entire file with:

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
    try:
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
    finally:
        cap.release()
    if progress_callback is not None and total > 0 and last_reported < 1.0:
        progress_callback(1.0)
    return np.asarray(energies, dtype=float)
```

Note: `progress_callback(1.0)` after the `finally` block is intentionally outside the try/finally — if the loop was cancelled via a raised exception, this line is never reached (the exception propagates after `cap.release()`). This is the correct behavior.

- [ ] **Step 4: Run the new test**

```bash
cd /Users/chinoyoung/Code/highlights && source .venv/bin/activate && pytest tests/test_motion.py -v
```

Expected: PASS.

---

### Task 3: Backend — Wire cancellation into routes and add cancel endpoint

**Files:**
- Modify: `app/api/routes.py`

**Interfaces:**
- Consumes:
  - `jobs.cancel(job_id: str) -> None` (from Task 1)
  - `jobs.get(job_id: str) -> dict | None` (from Task 1, now includes `"cancelled"`)
- Produces:
  - `POST /api/jobs/{job_id}/cancel` — 404 if unknown, else returns job record with `cancelled=True` and `status="cancelled"`
  - Both `detect` and `export` background threads raise `_Cancelled` when the flag is set mid-run, ending with `status="cancelled"` not `"error"`

- [ ] **Step 1: Write the failing API cancel test**

In `tests/test_api.py`, append:

```python
def test_cancel_unknown_job_returns_404():
    client = _client()
    r = client.post("/api/jobs/doesnotexist/cancel")
    assert r.status_code == 404


def test_cancel_known_job_sets_cancelled():
    """Cancel endpoint immediately flips the flag without waiting for thread."""
    from app import workdir
    import tempfile
    import os

    client = _client()

    # We need a real upload to get a video_id for detect — but we can also
    # test the cancel endpoint by directly creating a job and cancelling it.
    # Use a mock job to avoid needing a real video.
    from app.api import jobs as _jobs
    jid = _jobs.create()

    r = client.post(f"/api/jobs/{jid}/cancel")
    assert r.status_code == 200
    body = r.json()
    assert body["cancelled"] is True
    assert body["status"] == "cancelled"
```

- [ ] **Step 2: Run the failing tests**

```bash
cd /Users/chinoyoung/Code/highlights && source .venv/bin/activate && pytest tests/test_api.py::test_cancel_unknown_job_returns_404 tests/test_api.py::test_cancel_known_job_sets_cancelled -v
```

Expected: FAILED — endpoint does not exist.

- [ ] **Step 3: Implement the changes in `app/api/routes.py`**

Replace the entire file with:

```python
import dataclasses
import threading
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.config import DetectionParams
from app.deps import probe_duration
from app import workdir
from app.api import jobs, state
from app.analyzer import pipeline
from app.exporter import ffmpeg as exporter

router = APIRouter(prefix="/api")


class _Cancelled(Exception):
    """Raised by the progress callback when a job has been cancelled."""


class DetectBody(BaseModel):
    video_id: str
    params: dict | None = None


class ExportBody(BaseModel):
    video_id: str
    ranges: list[dict]


def _params(d: dict | None) -> DetectionParams:
    allowed = {f.name for f in dataclasses.fields(DetectionParams)}
    filtered = {k: v for k, v in (d or {}).items() if k in allowed}
    return DetectionParams(**filtered)


def _require(video_id: str) -> dict:
    info = state.get(video_id)
    if not info:
        raise HTTPException(404, "Unknown video_id")
    return info


def _make_progress_cb(job_id: str):
    """Return a progress callback that raises _Cancelled if the job was cancelled."""
    def _cb(f: float) -> None:
        rec = jobs.get(job_id)
        if rec and rec["cancelled"]:
            raise _Cancelled()
        jobs.update(job_id, progress=f)
    return _cb


@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    video_id = uuid.uuid4().hex[:12]
    ext = Path(file.filename or "video.mp4").suffix or ".mp4"
    dest = workdir.video_dir(video_id) / f"source{ext}"
    dest.write_bytes(await file.read())
    try:
        duration = probe_duration(str(dest))
    except ValueError:
        raise HTTPException(400, "Uploaded file is not a decodable video")
    state.put(video_id, {"path": str(dest), "duration": duration})
    return {"video_id": video_id, "duration": duration}


@router.post("/detect")
def detect(body: DetectBody):
    info = _require(body.video_id)
    params = _params(body.params)
    job_id = jobs.create()

    def run():
        try:
            rallies = pipeline.analyze(
                body.video_id, info["path"], params,
                progress_callback=_make_progress_cb(job_id),
            )
            jobs.update(job_id, status="done", progress=1.0,
                        result={"rallies": rallies})
        except _Cancelled:
            jobs.update(job_id, status="cancelled")
        except Exception as e:  # noqa: BLE001 - surface to client as job error
            jobs.update(job_id, status="error", error=str(e))

    threading.Thread(target=run, daemon=True).start()
    return {"job_id": job_id}


@router.post("/resegment")
def resegment(body: DetectBody):
    _require(body.video_id)
    return {"rallies": pipeline.resegment(body.video_id, _params(body.params))}


@router.post("/export")
def export(body: ExportBody):
    info = _require(body.video_id)
    out_dir = str(workdir.video_dir(body.video_id) / "output")
    job_id = jobs.create()

    def run():
        try:
            result = exporter.export(
                info["path"], body.ranges, out_dir,
                progress_callback=_make_progress_cb(job_id),
            )
            jobs.update(job_id, status="done", progress=1.0, result=result)
        except _Cancelled:
            jobs.update(job_id, status="cancelled")
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


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    rec = jobs.get(job_id)
    if rec is None:
        raise HTTPException(404, "Unknown job_id")
    jobs.cancel(job_id)
    jobs.update(job_id, status="cancelled")
    return jobs.get(job_id)


@router.get("/video/{video_id}")
def get_video(video_id: str):
    info = _require(video_id)
    return FileResponse(info["path"])
```

- [ ] **Step 4: Run new and full API test suite**

```bash
cd /Users/chinoyoung/Code/highlights && source .venv/bin/activate && pytest tests/test_api.py -v
```

Expected: All tests pass including the two new cancel tests.

- [ ] **Step 5: Run the full backend test suite**

```bash
cd /Users/chinoyoung/Code/highlights && source .venv/bin/activate && pytest -v
```

Expected: All tests PASS. Record the full output for the report.

---

### Task 4: Frontend — Add `cancelJob` API helper

**Files:**
- Modify: `frontend/src/api.ts`

**Interfaces:**
- Produces: `export async function cancelJob(jobId: string): Promise<void>`

- [ ] **Step 1: Add `cancelJob` to `frontend/src/api.ts`**

Append to the end of `frontend/src/api.ts`:

```typescript
export async function cancelJob(jobId: string): Promise<void> {
  const r = await fetch(`/api/jobs/${jobId}/cancel`, { method: "POST" });
  if (!r.ok) {
    const detail = (await r.json().catch(() => ({}))).detail;
    throw new Error(detail || r.statusText);
  }
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /Users/chinoyoung/Code/highlights/frontend && npm run build
```

Expected: 0 errors.

---

### Task 5: Frontend — Cancel button + fix upload-in-flight flash in `App.tsx`

**Files:**
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `cancelJob(jobId: string): Promise<void>` from Task 4
- Produces: Cancel button visible during detection; confirmed screen reappears after cancel with `selectedFile` intact; review UI never flashes during upload→detect handoff.

**Key state decisions (read before implementing):**

Current flow clears `selectedFile` in `handleAnalyze()` before calling `startDetect`. This must change: keep `selectedFile` set through the whole analysis so that Cancel can return to the confirm screen.

The flash bug: after `handleAnalyze` completes (upload done, `setVideoId` called, `setDetectJob` called), there is a brief render cycle where `videoId` is set but `detectJob` is also set. The current View 4 guard is `{videoId && !detectJob && ...}` — so that's correct, but the original code clears `selectedFile` before `detectJob` is set, which can create a window where neither View 2 nor View 3 is active. Keeping `selectedFile` through analysis AND using `analyzing || (detectJob && detect.status === "running")` for View 3 eliminates the gap.

- [ ] **Step 1: Write the new failing tests**

In `frontend/src/test/App.test.tsx`, append inside the `describe` block:

```typescript
  it("Cancel button calls cancelJob and returns to SelectedVideo confirm screen", async () => {
    vi.mocked(api.uploadVideo).mockResolvedValue({ video_id: "v1", duration: 120 });
    vi.mocked(api.startDetect).mockResolvedValue({ job_id: "j1" });
    vi.mocked(api.getJob).mockResolvedValue({
      status: "running",
      progress: 0.3,
      result: null,
      error: null,
      cancelled: false,
    });
    // cancelJob is a new export — add to mock
    const cancelJobMock = vi.fn().mockResolvedValue(undefined);
    vi.mocked(api as any).cancelJob = cancelJobMock;

    render(<App />);

    const input = document.querySelector<HTMLInputElement>("input[type=file]")!;
    const file = new File(["video"], "match.mp4", { type: "video/mp4" });
    await userEvent.upload(input, file);

    await waitFor(() =>
      expect(screen.getByRole("button", { name: /analyze video/i })).toBeInTheDocument()
    );
    await userEvent.click(screen.getByRole("button", { name: /analyze video/i }));

    // detecting view should appear
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /cancel/i })).toBeInTheDocument()
    );

    await userEvent.click(screen.getByRole("button", { name: /cancel/i }));

    // Should return to SelectedVideo confirm screen
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /analyze video/i })).toBeInTheDocument()
    );

    // Review UI must NOT be visible
    expect(screen.queryByRole("button", { name: /export/i })).not.toBeInTheDocument();
  });
```

Also update the mock declaration at the top of the file to include `cancelJob`:

Find the existing `vi.mock("../api", () => ({` block and add `cancelJob: vi.fn(),`:

```typescript
vi.mock("../api", () => ({
  uploadVideo: vi.fn(),
  startDetect: vi.fn(),
  startExport: vi.fn(),
  cancelJob: vi.fn(),
  getJob: vi.fn(),
  resegment: vi.fn(),
  videoUrl: vi.fn((id: string) => `/api/video/${id}`),
}));
```

- [ ] **Step 2: Run the failing test**

```bash
cd /Users/chinoyoung/Code/highlights/frontend && npm run test -- --reporter=verbose 2>&1 | tail -40
```

Expected: The new Cancel test FAILS (no Cancel button exists yet). Existing 21 tests should still pass — if any break, fix before proceeding.

- [ ] **Step 3: Implement the changes in `frontend/src/App.tsx`**

Replace the entire file with:

```typescript
import { useRef, useState } from "react";
import * as api from "./api";
import { useJob } from "./useJob";
import type { Rally } from "./types";
import { UploadView } from "./components/UploadView";
import { SelectedVideo } from "./components/SelectedVideo";
import { BallLoader } from "./components/BallLoader";
import { ProgressBar } from "./components/ProgressBar";
import { Player, type PlayerHandle } from "./components/Player";
import { Timeline } from "./components/Timeline";
import { RallyList } from "./components/RallyList";
import { Controls } from "./components/Controls";
import { ThemeToggle } from "./components/ThemeToggle";
import { ResultPanel } from "./components/ResultPanel";

export default function App() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [videoId, setVideoId] = useState<string | null>(null);
  const [duration, setDuration] = useState(0);
  const [rallies, setRallies] = useState<Rally[]>([]);
  const [sensitivity, setSensitivity] = useState(0.5);
  const [detectJob, setDetectJob] = useState<string | null>(null);
  const [exportJob, setExportJob] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const player = useRef<PlayerHandle>(null);

  const detect = useJob(detectJob);
  const exp = useJob(exportJob);

  // detect job completed → load rallies
  if (detect.status === "done" && detectJob && detect.result) {
    const rs: Rally[] = detect.result.rallies.map((r: any) => ({ ...r, included: true }));
    setRallies(rs);
    setDetectJob(null);
  }

  function handleFileSelected(file: File) {
    setUploadError(null);
    setSelectedFile(file);
  }

  async function handleAnalyze() {
    if (!selectedFile) return;
    setUploadError(null);
    setAnalyzing(true);
    try {
      const up = await api.uploadVideo(selectedFile);
      setVideoId(up.video_id);
      setDuration(up.duration);
      // NOTE: do NOT clear selectedFile here — Cancel needs it to return to confirm screen
      const { job_id } = await api.startDetect(up.video_id, { threshold: 1 - sensitivity });
      setDetectJob(job_id);
    } catch (e) {
      setUploadError(String(e instanceof Error ? e.message : e));
    } finally {
      setAnalyzing(false);
    }
  }

  function handleReset() {
    setSelectedFile(null);
    setUploadError(null);
  }

  async function handleCancel() {
    if (detectJob) {
      try {
        await api.cancelJob(detectJob);
      } catch {
        // best-effort: still reset UI even if the cancel request fails
      }
    }
    // Return to confirm screen: clear analysis state but keep selectedFile
    setDetectJob(null);
    setAnalyzing(false);
    setVideoId(null);
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

  // Detecting view: covers the full upload→detect handoff (analyzing flag) AND the running job
  const isDetecting = analyzing || (detectJob !== null && detect.status === "running");

  // Review view: only when we have a video, no active detect job, NOT in the analyzing handoff,
  // and we actually have a non-empty rally result (i.e. detect completed)
  const isReviewing = videoId !== null && !detectJob && !analyzing;

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--ink)]">
      <header className="flex items-center justify-between border-b border-[var(--line)] px-6 py-4 sm:px-8">
        <h1 className="font-display text-lg font-bold tracking-tight text-[var(--ink)]">
          Pickleball<span className="text-[var(--teal)]">.</span>highlights
        </h1>
        <ThemeToggle />
      </header>

      <main className="mx-auto flex max-w-3xl flex-col gap-6 px-4 pb-16 pt-8 sm:px-8">
        {/* View 1: no file selected, no video uploaded, not detecting */}
        {!selectedFile && !videoId && !isDetecting && (
          <UploadView onFile={handleFileSelected} error={uploadError} />
        )}

        {/* View 2: file selected, not yet uploaded/detecting */}
        {selectedFile && !isDetecting && !videoId && (
          <SelectedVideo
            file={selectedFile}
            onAnalyze={handleAnalyze}
            onReset={handleReset}
            analyzing={analyzing}
          />
        )}

        {/* View 3: detecting — shown for full upload+detect handoff, no review UI can bleed through */}
        {isDetecting && (
          <>
            <BallLoader />
            <ProgressBar label="Finding rallies…" fraction={detect.progress} />
            <div className="flex justify-center">
              <button
                onClick={handleCancel}
                className="rounded-lg border border-[var(--line)] px-4 py-2 text-sm text-[var(--muted)] hover:text-[var(--ink)] transition-colors"
              >
                Cancel
              </button>
            </div>
          </>
        )}
        {detect.status === "error" && (
          <p className="text-sm text-[var(--danger)]">Detection failed: {detect.error}</p>
        )}

        {/* View 4: review + export — gated: never shows while detecting or during upload handoff */}
        {isReviewing && (
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
              <ProgressBar label="Exporting highlights…" fraction={exp.progress} />
            )}
            {exp.status === "error" && (
              <p className="text-sm text-[var(--danger)]">Export failed: {exp.error}</p>
            )}
            {exp.status === "done" && exp.result && <ResultPanel result={exp.result} />}
          </>
        )}
      </main>
    </div>
  );
}
```

- [ ] **Step 4: Run the frontend test suite**

```bash
cd /Users/chinoyoung/Code/highlights/frontend && npm run test -- --reporter=verbose 2>&1 | tail -60
```

Expected: All 22 tests pass (21 original + 1 new Cancel test).

- [ ] **Step 5: Run TypeScript build**

```bash
cd /Users/chinoyoung/Code/highlights/frontend && npm run build 2>&1
```

Expected: 0 TS errors, successful build.

---

### Task 6: Write the final report

**Files:**
- Create: `docs/superpowers/plans/briefs-fe/cancel-report.md`

**Interfaces:**
- Consumes: all test output from Tasks 1–5
- Produces: final report per spec contract

- [ ] **Step 1: Run complete backend suite and capture output**

```bash
cd /Users/chinoyoung/Code/highlights && source .venv/bin/activate && pytest -v 2>&1
```

Record the full output for embedding in the report.

- [ ] **Step 2: Run complete frontend suite and build and capture output**

```bash
cd /Users/chinoyoung/Code/highlights/frontend && npm run test -- --reporter=verbose 2>&1 && npm run build 2>&1
```

Record the full output for embedding in the report.

- [ ] **Step 3: Write the report to `docs/superpowers/plans/briefs-fe/cancel-report.md`**

The report must cover:

1. **Backend cancellation mechanism** — `cancelled` field in `jobs.py`, `_make_progress_cb` helper in `routes.py`, `_Cancelled` sentinel exception, how cancellation propagates from callback to thread to job status.
2. **Cancel endpoint** — `POST /api/jobs/{job_id}/cancel` path, behavior (404 unknown, sets `cancelled=True` + `status="cancelled"` immediately, returns updated record).
3. **`motion.py` finally fix** — what changed, why it prevents a VideoCapture leak.
4. **Frontend Cancel button** — how `cancelJob` is called, what state is cleared vs kept (`selectedFile` kept, `detectJob`/`analyzing`/`videoId` cleared), which view reappears.
5. **Frontend gating fix** — `isDetecting` and `isReviewing` booleans, why the flash was possible before, why it's eliminated now.
6. **New tests** — list each new test and what it verifies.
7. **Backend `pytest -v` result** — full terminal output.
8. **Frontend `npm run build` result** — full terminal output.
9. **Frontend `npm run test` result** — full terminal output.
