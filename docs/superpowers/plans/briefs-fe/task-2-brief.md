# Task 2 (modern-frontend)

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

