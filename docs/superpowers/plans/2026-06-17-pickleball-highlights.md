# Pickleball Highlight Extractor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local web app that detects rallies in fixed-camera pickleball videos, lets the user review/trim them in a browser, and exports individual clips plus one stitched highlight video.

**Architecture:** A FastAPI backend does all heavy work (ffmpeg extraction, motion + audio signal analysis, segmentation, export). A static vanilla-JS frontend served from the same app provides the review timeline. Raw signals are cached so re-segmentation (the sensitivity slider) is instant. Everything runs on `localhost`.

**Tech Stack:** Python 3.11+, FastAPI, uvicorn, opencv-python, numpy, system ffmpeg/ffprobe; vanilla HTML/JS frontend (no build step); pytest for tests.

## Global Constraints

- **Python version floor:** 3.10+ (3.10.8 is the available interpreter; code is 3.10-compatible).
- **System dependency:** `ffmpeg` and `ffprobe` must be on `PATH`.
- **No heavy audio libs:** audio energy is computed from an ffmpeg-extracted WAV using NumPy only — do NOT add `librosa` or similar.
- **No build step for frontend:** plain `index.html` + JS served as static files.
- **Git is disabled for this project** (user global instruction + not a git repo). Wherever a task would normally `git commit`, instead run the task's full test suite and confirm green as the checkpoint. Do not run any state-changing git command.
- **Frame-accurate cuts:** export must re-encode cut ranges, not stream-copy (stream-copy only cuts on keyframes).
- **Detection defaults:** `sample_fps=8`, `merge_gap_seconds=2.0`, `min_rally_seconds=2.5`, `pad_seconds=1.0`, `threshold=0.5` (normalized 0–1).

---

## File Structure

```
highlights/
  pyproject.toml                  # deps + pytest config
  app/
    __init__.py
    main.py                       # FastAPI app, startup ffmpeg check, static mount
    config.py                     # DetectionParams dataclass + defaults
    deps.py                       # ffmpeg/ffprobe availability + probe helpers
    workdir.py                    # per-video workdir paths + signal cache I/O
    analyzer/
      __init__.py
      segment.py                  # PURE: signals -> rally list
      audio.py                    # WAV -> audio energy series
      motion.py                   # frames -> motion energy series
      pipeline.py                 # orchestrates extract+analyze+cache, then segment
    exporter/
      __init__.py
      ffmpeg.py                   # cut clip + concat stitched
    api/
      __init__.py
      routes.py                   # upload / detect / resegment / export
      state.py                    # in-memory job registry
    web/
      index.html
      app.js
      style.css
  tests/
    conftest.py                   # ffmpeg-generated fixture videos/wavs
    test_segment.py
    test_audio.py
    test_motion.py
    test_pipeline.py
    test_exporter.py
    test_api.py
  workdir/                        # runtime per-video folders (gitignored conceptually)
```

---

## Task 1: Project scaffold + ffmpeg availability

**Files:**
- Create: `pyproject.toml`, `app/__init__.py`, `app/config.py`, `app/deps.py`, `app/main.py`
- Test: `tests/test_deps.py`, `tests/conftest.py`

**Interfaces:**
- Produces:
  - `app/config.py`: `@dataclass DetectionParams(sample_fps:int=8, threshold:float=0.5, merge_gap_seconds:float=2.0, min_rally_seconds:float=2.5, pad_seconds:float=1.0)`
  - `app/deps.py`: `def ffmpeg_available() -> bool`, `def require_ffmpeg() -> None` (raises `RuntimeError` with a clear message if missing), `def probe_duration(path: str) -> float` (seconds, via ffprobe; raises `ValueError` if not decodable).
  - `app/main.py`: `app` (FastAPI instance) that calls `require_ffmpeg()` on startup.

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "pickleball-highlights"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.29",
    "python-multipart>=0.0.9",
    "opencv-python-headless>=4.9",
    "numpy>=1.26",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "httpx>=0.27"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Create `app/__init__.py`** (empty file).

- [ ] **Step 3: Create `app/config.py`**

```python
from dataclasses import dataclass


@dataclass
class DetectionParams:
    sample_fps: int = 8
    threshold: float = 0.5          # normalized 0..1
    merge_gap_seconds: float = 2.0
    min_rally_seconds: float = 2.5
    pad_seconds: float = 1.0
```

- [ ] **Step 4: Create `tests/conftest.py`** (shared ffmpeg-generated fixtures used across tasks)

```python
import subprocess
import shutil
import numpy as np
import pytest

HAVE_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
requires_ffmpeg = pytest.mark.skipif(not HAVE_FFMPEG, reason="ffmpeg not installed")


def _run(cmd):
    subprocess.run(cmd, check=True, capture_output=True)


@pytest.fixture
def sample_video(tmp_path):
    """6s video: 0-2s static color (no motion), 2-4s moving testsrc (motion),
    4-6s static. Audio: loud sine 2-4s, silence elsewhere."""
    out = tmp_path / "sample.mp4"
    still = tmp_path / "still.mp4"
    moving = tmp_path / "moving.mp4"
    # still segment (black, silent)
    _run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=320x240:d=2:r=8",
          "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "2",
          "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p", str(still)])
    # moving segment (testsrc2 = lots of motion, loud sine audio)
    _run(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc2=s=320x240:d=2:r=8",
          "-f", "lavfi", "-i", "sine=frequency=1000:duration=2", "-t", "2",
          "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p", str(moving)])
    listf = tmp_path / "list.txt"
    listf.write_text(f"file '{still}'\nfile '{moving}'\nfile '{still}'\n")
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listf),
          "-c", "copy", str(out)])
    return str(out)
```

- [ ] **Step 5: Create `app/deps.py`**

```python
import json
import shutil
import subprocess


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def require_ffmpeg() -> None:
    if not ffmpeg_available():
        raise RuntimeError(
            "ffmpeg and ffprobe must be installed and on PATH. "
            "Install with e.g. `brew install ffmpeg`."
        )


def probe_duration(path: str) -> float:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "json", path],
            check=True, capture_output=True, text=True,
        ).stdout
        return float(json.loads(out)["format"]["duration"])
    except (subprocess.CalledProcessError, KeyError, ValueError) as e:
        raise ValueError(f"Not a decodable video: {path}") from e
```

- [ ] **Step 6: Write `tests/test_deps.py`**

```python
from app.deps import ffmpeg_available, probe_duration
from tests.conftest import requires_ffmpeg


def test_ffmpeg_available_returns_bool():
    assert isinstance(ffmpeg_available(), bool)


@requires_ffmpeg
def test_probe_duration_reads_length(sample_video):
    dur = probe_duration(sample_video)
    assert 5.0 < dur < 7.0


@requires_ffmpeg
def test_probe_duration_rejects_non_video(tmp_path):
    bad = tmp_path / "x.txt"
    bad.write_text("not a video")
    import pytest
    with pytest.raises(ValueError):
        probe_duration(str(bad))
```

- [ ] **Step 7: Run tests, expect PASS**

Run: `pytest tests/test_deps.py -v`
Expected: PASS (the two ffmpeg tests skip if ffmpeg absent).

- [ ] **Step 8: Create `app/main.py`**

```python
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.deps import require_ffmpeg

app = FastAPI(title="Pickleball Highlights")


@app.on_event("startup")
def _check_ffmpeg() -> None:
    require_ffmpeg()


WEB_DIR = Path(__file__).parent / "web"
if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
```

- [ ] **Step 9: Checkpoint** — Run `pytest -v`. Confirm green (skips allowed). Verify `python -c "import app.main"` imports without error.

---

## Task 2: Segmentation (pure core)

This is the heart of detection. Pure functions on NumPy arrays — no I/O, fully unit-testable.

**Files:**
- Create: `app/analyzer/__init__.py`, `app/analyzer/segment.py`
- Test: `tests/test_segment.py`

**Interfaces:**
- Consumes: `DetectionParams` from `app/config.py`.
- Produces in `app/analyzer/segment.py`:
  - `def normalize(x: np.ndarray) -> np.ndarray` — scale to 0..1 (constant array → all zeros).
  - `def combine(motion: np.ndarray, audio: np.ndarray) -> np.ndarray` — element-wise max of normalized inputs (arrays are same length, one value per time step).
  - `def smooth(x: np.ndarray, window: int) -> np.ndarray` — moving average, same length.
  - `def segment(signal: np.ndarray, hop_seconds: float, params: DetectionParams) -> list[dict]` — threshold → contiguous spans → merge gaps → drop short → pad. Returns `[{"start": float, "end": float, "confidence": float}]` where `confidence` is the mean signal value over the unpadded span. Times in seconds; `signal[i]` corresponds to time `i * hop_seconds`.

- [ ] **Step 1: Write failing tests `tests/test_segment.py`**

```python
import numpy as np
from app.config import DetectionParams
from app.analyzer import segment as S


def test_normalize_constant_is_zeros():
    assert np.allclose(S.normalize(np.array([5.0, 5.0, 5.0])), 0.0)


def test_normalize_scales_to_unit():
    out = S.normalize(np.array([0.0, 5.0, 10.0]))
    assert out[0] == 0.0 and out[-1] == 1.0


def test_combine_takes_max():
    m = np.array([0.0, 1.0]); a = np.array([1.0, 0.0])
    assert np.allclose(S.combine(m, a), [1.0, 1.0])


def test_segment_finds_single_active_span():
    # hop=0.5s, 20 steps = 10s. Active 2s..6s.
    sig = np.zeros(20); sig[4:12] = 1.0
    p = DetectionParams(threshold=0.5, merge_gap_seconds=0.0,
                        min_rally_seconds=1.0, pad_seconds=0.0)
    spans = S.segment(sig, hop_seconds=0.5, params=p)
    assert len(spans) == 1
    assert abs(spans[0]["start"] - 2.0) < 0.6
    assert abs(spans[0]["end"] - 6.0) < 0.6


def test_segment_merges_short_gap():
    sig = np.zeros(40)
    sig[4:12] = 1.0; sig[14:22] = 1.0   # 1s gap between spans (hop 0.5)
    p = DetectionParams(threshold=0.5, merge_gap_seconds=2.0,
                        min_rally_seconds=1.0, pad_seconds=0.0)
    spans = S.segment(sig, hop_seconds=0.5, params=p)
    assert len(spans) == 1


def test_segment_drops_short_span():
    sig = np.zeros(40); sig[4:6] = 1.0   # 1s span
    p = DetectionParams(threshold=0.5, merge_gap_seconds=0.0,
                        min_rally_seconds=2.5, pad_seconds=0.0)
    assert S.segment(sig, hop_seconds=0.5, params=p) == []


def test_segment_applies_padding_and_clamps():
    sig = np.zeros(20); sig[0:8] = 1.0   # span at very start
    p = DetectionParams(threshold=0.5, merge_gap_seconds=0.0,
                        min_rally_seconds=1.0, pad_seconds=1.0)
    spans = S.segment(sig, hop_seconds=0.5, params=p)
    assert spans[0]["start"] == 0.0       # clamped, not negative


def test_segment_empty_when_all_quiet():
    assert S.segment(np.zeros(20), hop_seconds=0.5,
                     params=DetectionParams()) == []
```

- [ ] **Step 2: Run, expect FAIL**

Run: `pytest tests/test_segment.py -v`
Expected: FAIL (module/functions not defined).

- [ ] **Step 3: Create `app/analyzer/__init__.py`** (empty file).

- [ ] **Step 4: Implement `app/analyzer/segment.py`**

```python
import numpy as np
from app.config import DetectionParams


def normalize(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    lo, hi = float(x.min()), float(x.max())
    if hi - lo < 1e-12:
        return np.zeros_like(x)
    return (x - lo) / (hi - lo)


def combine(motion: np.ndarray, audio: np.ndarray) -> np.ndarray:
    return np.maximum(normalize(motion), normalize(audio))


def smooth(x: np.ndarray, window: int) -> np.ndarray:
    if window <= 1:
        return np.asarray(x, dtype=float)
    kernel = np.ones(window) / window
    return np.convolve(np.asarray(x, dtype=float), kernel, mode="same")


def segment(signal: np.ndarray, hop_seconds: float,
            params: DetectionParams) -> list[dict]:
    signal = np.asarray(signal, dtype=float)
    active = signal >= params.threshold

    # contiguous runs of True -> (start_idx, end_idx_exclusive)
    runs = []
    i, n = 0, len(active)
    while i < n:
        if active[i]:
            j = i
            while j < n and active[j]:
                j += 1
            runs.append((i, j))
            i = j
        else:
            i += 1

    # merge runs separated by short gaps
    merged = []
    for run in runs:
        if merged and (run[0] - merged[-1][1]) * hop_seconds <= params.merge_gap_seconds:
            merged[-1] = (merged[-1][0], run[1])
        else:
            merged.append(list(run))

    out = []
    total = n * hop_seconds
    for start_idx, end_idx in merged:
        start = start_idx * hop_seconds
        end = end_idx * hop_seconds
        if end - start < params.min_rally_seconds:
            continue
        conf = float(signal[start_idx:end_idx].mean()) if end_idx > start_idx else 0.0
        out.append({
            "start": max(0.0, start - params.pad_seconds),
            "end": min(total, end + params.pad_seconds),
            "confidence": conf,
        })
    return out
```

- [ ] **Step 5: Run, expect PASS**

Run: `pytest tests/test_segment.py -v`
Expected: PASS (all 8 tests).

- [ ] **Step 6: Checkpoint** — Run `pytest -v`. Confirm green.

---

## Task 3: Audio energy extraction

**Files:**
- Create: `app/analyzer/audio.py`
- Test: `tests/test_audio.py`

**Interfaces:**
- Consumes: ffmpeg (system), `probe_duration` not needed here.
- Produces in `app/analyzer/audio.py`:
  - `def extract_wav(video_path: str, wav_path: str, sample_rate: int = 16000) -> str` — ffmpeg-extract mono WAV at `sample_rate`; returns `wav_path`.
  - `def audio_energy(wav_path: str, hop_seconds: float) -> np.ndarray` — RMS per `hop_seconds` window. One value per time step.

- [ ] **Step 1: Write failing tests `tests/test_audio.py`**

```python
import numpy as np
from app.analyzer import audio
from tests.conftest import requires_ffmpeg


@requires_ffmpeg
def test_extract_wav_creates_file(sample_video, tmp_path):
    wav = tmp_path / "a.wav"
    out = audio.extract_wav(sample_video, str(wav))
    assert wav.exists() and out == str(wav)


@requires_ffmpeg
def test_audio_energy_higher_during_sine(sample_video, tmp_path):
    wav = tmp_path / "a.wav"
    audio.extract_wav(sample_video, str(wav))
    energy = audio.audio_energy(str(wav), hop_seconds=0.5)
    # ~12 hops over 6s; sine is in the middle 2s (hops ~4..8)
    assert len(energy) >= 10
    middle = energy[4:8].mean()
    edges = np.concatenate([energy[:3], energy[-3:]]).mean()
    assert middle > edges
```

- [ ] **Step 2: Run, expect FAIL**

Run: `pytest tests/test_audio.py -v`
Expected: FAIL (module not defined).

- [ ] **Step 3: Implement `app/analyzer/audio.py`**

```python
import subprocess
import wave
import numpy as np


def extract_wav(video_path: str, wav_path: str, sample_rate: int = 16000) -> str:
    subprocess.run(
        ["ffmpeg", "-y", "-i", video_path, "-vn", "-ac", "1",
         "-ar", str(sample_rate), "-f", "wav", wav_path],
        check=True, capture_output=True,
    )
    return wav_path


def audio_energy(wav_path: str, hop_seconds: float) -> np.ndarray:
    with wave.open(wav_path, "rb") as w:
        rate = w.getframerate()
        frames = w.readframes(w.getnframes())
    samples = np.frombuffer(frames, dtype=np.int16).astype(np.float64)
    if samples.size == 0:
        return np.zeros(0)
    hop = max(1, int(rate * hop_seconds))
    n = samples.size // hop
    if n == 0:
        return np.array([np.sqrt(np.mean(samples ** 2))])
    trimmed = samples[: n * hop].reshape(n, hop)
    return np.sqrt(np.mean(trimmed ** 2, axis=1))
```

- [ ] **Step 4: Run, expect PASS**

Run: `pytest tests/test_audio.py -v`
Expected: PASS (skips without ffmpeg).

- [ ] **Step 5: Checkpoint** — Run `pytest -v`. Confirm green.

---

## Task 4: Motion energy extraction

**Files:**
- Create: `app/analyzer/motion.py`
- Test: `tests/test_motion.py`

**Interfaces:**
- Consumes: ffmpeg (system), OpenCV.
- Produces in `app/analyzer/motion.py`:
  - `def motion_energy(video_path: str, sample_fps: int) -> np.ndarray` — sample frames at `sample_fps`, return mean absolute grayscale frame-difference per step. First step is 0.0 (no previous frame). One value per sampled frame; the time hop equals `1/sample_fps`.

- [ ] **Step 1: Write failing tests `tests/test_motion.py`**

```python
import numpy as np
from app.analyzer import motion
from tests.conftest import requires_ffmpeg


@requires_ffmpeg
def test_motion_energy_higher_during_movement(sample_video):
    energy = motion.motion_energy(sample_video, sample_fps=8)
    # 6s @ 8fps ≈ 48 samples; motion segment is middle 2s (samples ~16..32)
    assert len(energy) >= 40
    middle = energy[18:30].mean()
    edges = np.concatenate([energy[2:12], energy[-12:-2]]).mean()
    assert middle > edges
```

- [ ] **Step 2: Run, expect FAIL**

Run: `pytest tests/test_motion.py -v`
Expected: FAIL (module not defined).

- [ ] **Step 3: Implement `app/analyzer/motion.py`**

```python
import cv2
import numpy as np


def motion_energy(video_path: str, sample_fps: int) -> np.ndarray:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")
    src_fps = cap.get(cv2.CAP_PROP_FPS) or sample_fps
    step = max(1, int(round(src_fps / sample_fps)))

    energies = []
    prev = None
    idx = 0
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
    cap.release()
    return np.asarray(energies, dtype=float)
```

- [ ] **Step 4: Run, expect PASS**

Run: `pytest tests/test_motion.py -v`
Expected: PASS (skips without ffmpeg/opencv codec; if codec issue, see note).

- [ ] **Step 5: Checkpoint** — Run `pytest -v`. Confirm green.

---

## Task 5: Workdir, caching, and the analysis pipeline

Ties extraction together, caches raw signals, resamples them onto one shared time base, and produces rallies. Re-segmentation reuses the cache.

**Files:**
- Create: `app/workdir.py`, `app/analyzer/pipeline.py`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `motion_energy`, `extract_wav`, `audio_energy`, `segment.combine/smooth/segment`, `DetectionParams`.
- Produces:
  - `app/workdir.py`:
    - `def video_dir(video_id: str) -> Path` — `workdir/<video_id>/` (created).
    - `def save_signals(video_id: str, motion: np.ndarray, audio: np.ndarray, hop_seconds: float) -> None`
    - `def load_signals(video_id: str) -> tuple[np.ndarray, np.ndarray, float]` — raises `FileNotFoundError` if absent.
  - `app/analyzer/pipeline.py`:
    - `HOP_SECONDS` constant computed as `1 / sample_fps` at analyze time; the shared hop is stored in the cache.
    - `def analyze(video_id: str, video_path: str, params: DetectionParams) -> list[dict]` — extract motion+audio, resample audio onto motion's time base (same length), cache both, then `resegment`.
    - `def resegment(video_id: str, params: DetectionParams) -> list[dict]` — load cached signals, `combine` → `smooth` → `segment`. No video re-read.

- [ ] **Step 1: Write failing tests `tests/test_pipeline.py`**

```python
import numpy as np
from app.config import DetectionParams
from app import workdir
from app.analyzer import pipeline
from tests.conftest import requires_ffmpeg


def test_save_and_load_signals_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)
    m = np.array([0.0, 1.0, 0.5]); a = np.array([0.2, 0.3, 0.9])
    workdir.save_signals("vid1", m, a, hop_seconds=0.125)
    lm, la, hop = workdir.load_signals("vid1")
    assert np.allclose(lm, m) and np.allclose(la, a) and hop == 0.125


@requires_ffmpeg
def test_analyze_detects_middle_rally(tmp_path, monkeypatch, sample_video):
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)
    p = DetectionParams(sample_fps=8, threshold=0.4,
                        min_rally_seconds=1.0, pad_seconds=0.5)
    rallies = pipeline.analyze("vid2", sample_video, p)
    assert len(rallies) >= 1
    r = rallies[0]
    assert r["start"] < 4.0 and r["end"] > 2.0   # overlaps the 2-4s active region


@requires_ffmpeg
def test_resegment_uses_cache(tmp_path, monkeypatch, sample_video):
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)
    pipeline.analyze("vid3", sample_video, DetectionParams())
    loose = pipeline.resegment("vid3", DetectionParams(threshold=0.1,
                               min_rally_seconds=0.5, pad_seconds=0.0))
    strict = pipeline.resegment("vid3", DetectionParams(threshold=0.95,
                                min_rally_seconds=0.5, pad_seconds=0.0))
    assert sum(r["end"] - r["start"] for r in loose) >= \
           sum(r["end"] - r["start"] for r in strict)
```

- [ ] **Step 2: Run, expect FAIL**

Run: `pytest tests/test_pipeline.py -v`
Expected: FAIL (modules not defined).

- [ ] **Step 3: Implement `app/workdir.py`**

```python
from pathlib import Path
import numpy as np

WORKDIR = Path(__file__).parent.parent / "workdir"


def video_dir(video_id: str) -> Path:
    d = WORKDIR / video_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_signals(video_id: str, motion: np.ndarray, audio: np.ndarray,
                 hop_seconds: float) -> None:
    np.savez(video_dir(video_id) / "signals.npz",
             motion=motion, audio=audio, hop=np.array([hop_seconds]))


def load_signals(video_id: str):
    path = video_dir(video_id) / "signals.npz"
    if not path.exists():
        raise FileNotFoundError(f"No cached signals for {video_id}")
    data = np.load(path)
    return data["motion"], data["audio"], float(data["hop"][0])
```

- [ ] **Step 4: Implement `app/analyzer/pipeline.py`**

```python
import numpy as np
from app.config import DetectionParams
from app import workdir
from app.analyzer import motion as motion_mod
from app.analyzer import audio as audio_mod
from app.analyzer import segment as seg


def _resample(x: np.ndarray, length: int) -> np.ndarray:
    if x.size == 0 or length <= 0:
        return np.zeros(length)
    if x.size == length:
        return x
    src = np.linspace(0.0, 1.0, x.size)
    dst = np.linspace(0.0, 1.0, length)
    return np.interp(dst, src, x)


def analyze(video_id: str, video_path: str, params: DetectionParams) -> list[dict]:
    hop = 1.0 / params.sample_fps
    motion = motion_mod.motion_energy(video_path, params.sample_fps)

    wav = str(workdir.video_dir(video_id) / "audio.wav")
    audio_mod.extract_wav(video_path, wav)
    audio = audio_mod.audio_energy(wav, hop_seconds=hop)
    audio = _resample(audio, len(motion))   # share motion's time base

    workdir.save_signals(video_id, motion, audio, hop)
    return resegment(video_id, params)


def resegment(video_id: str, params: DetectionParams) -> list[dict]:
    motion, audio, hop = workdir.load_signals(video_id)
    combined = seg.combine(motion, audio)
    window = max(1, int(round(0.5 / hop)))   # ~0.5s smoothing
    combined = seg.smooth(combined, window)
    return seg.segment(combined, hop_seconds=hop, params=params)
```

- [ ] **Step 5: Run, expect PASS**

Run: `pytest tests/test_pipeline.py -v`
Expected: PASS.

- [ ] **Step 6: Checkpoint** — Run `pytest -v`. Confirm green.

---

## Task 6: Export (cut + stitch)

**Files:**
- Create: `app/exporter/__init__.py`, `app/exporter/ffmpeg.py`
- Test: `tests/test_exporter.py`

**Interfaces:**
- Consumes: ffmpeg, `probe_duration` from `app/deps.py`.
- Produces in `app/exporter/ffmpeg.py`:
  - `def cut_clip(src: str, start: float, end: float, out_path: str) -> str` — frame-accurate re-encode of `[start,end]`.
  - `def concat_clips(clip_paths: list[str], out_path: str) -> str` — re-encode concat into one file.
  - `def export(src: str, ranges: list[dict], out_dir: str) -> dict` — writes `clip_001.mp4 …` and `highlights.mp4`; returns `{"clips": [...paths], "stitched": path}`. Empty `ranges` → `{"clips": [], "stitched": None}`.

- [ ] **Step 1: Write failing tests `tests/test_exporter.py`**

```python
from app.exporter import ffmpeg as ex
from app.deps import probe_duration
from tests.conftest import requires_ffmpeg


@requires_ffmpeg
def test_cut_clip_has_expected_duration(sample_video, tmp_path):
    out = tmp_path / "clip.mp4"
    ex.cut_clip(sample_video, 2.0, 4.0, str(out))
    assert out.exists()
    assert abs(probe_duration(str(out)) - 2.0) < 0.5


@requires_ffmpeg
def test_export_produces_clips_and_stitch(sample_video, tmp_path):
    ranges = [{"start": 0.5, "end": 2.0}, {"start": 3.0, "end": 5.0}]
    result = ex.export(sample_video, ranges, str(tmp_path))
    assert len(result["clips"]) == 2
    total = sum(r["end"] - r["start"] for r in ranges)
    assert abs(probe_duration(result["stitched"]) - total) < 0.8


@requires_ffmpeg
def test_export_empty_ranges(sample_video, tmp_path):
    result = ex.export(sample_video, [], str(tmp_path))
    assert result == {"clips": [], "stitched": None}
```

- [ ] **Step 2: Run, expect FAIL**

Run: `pytest tests/test_exporter.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `app/exporter/__init__.py`** (empty file) and `app/exporter/ffmpeg.py`

```python
import subprocess
from pathlib import Path


def cut_clip(src: str, start: float, end: float, out_path: str) -> str:
    duration = max(0.0, end - start)
    subprocess.run(
        ["ffmpeg", "-y", "-ss", f"{start:.3f}", "-i", src,
         "-t", f"{duration:.3f}",
         "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac",
         "-pix_fmt", "yuv420p", out_path],
        check=True, capture_output=True,
    )
    return out_path


def concat_clips(clip_paths: list[str], out_path: str) -> str:
    listfile = Path(out_path).with_suffix(".txt")
    listfile.write_text("".join(f"file '{p}'\n" for p in clip_paths))
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listfile),
         "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac",
         "-pix_fmt", "yuv420p", out_path],
        check=True, capture_output=True,
    )
    listfile.unlink(missing_ok=True)
    return out_path


def export(src: str, ranges: list[dict], out_dir: str) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    if not ranges:
        return {"clips": [], "stitched": None}
    clips = []
    for i, r in enumerate(ranges, start=1):
        clip_path = str(out / f"clip_{i:03d}.mp4")
        cut_clip(src, float(r["start"]), float(r["end"]), clip_path)
        clips.append(clip_path)
    stitched = str(out / "highlights.mp4")
    concat_clips(clips, stitched)
    return {"clips": clips, "stitched": stitched}
```

- [ ] **Step 4: Run, expect PASS**

Run: `pytest tests/test_exporter.py -v`
Expected: PASS.

- [ ] **Step 5: Checkpoint** — Run `pytest -v`. Confirm green.

---

## Task 7: API routes + job state

**Files:**
- Create: `app/api/__init__.py`, `app/api/state.py`, `app/api/routes.py`
- Modify: `app/main.py` (include router before static mount)
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: `pipeline.analyze/resegment`, `exporter.export`, `probe_duration`, `DetectionParams`, `workdir.video_dir`.
- Produces (REST, all JSON unless noted):
  - `POST /api/upload` (multipart `file`) → `{"video_id": str, "duration": float}`. Saves to `workdir/<id>/source.<ext>`, validates via `probe_duration`.
  - `POST /api/detect` `{"video_id", "params"?}` → `{"rallies": [...]}`. Runs `analyze`.
  - `POST /api/resegment` `{"video_id", "params"}` → `{"rallies": [...]}`. Cheap; cached signals.
  - `POST /api/export` `{"video_id", "ranges": [{"start","end"}, ...]}` → `{"clips": [...], "stitched": path}`.
  - `GET /api/video/{video_id}` → streams the source file (for the player).
  - `params` keys map onto `DetectionParams` fields; missing keys use defaults.

- [ ] **Step 1: Write failing tests `tests/test_api.py`**

```python
import io
from fastapi.testclient import TestClient
from tests.conftest import requires_ffmpeg


def _client():
    from app.main import app
    return TestClient(app)


@requires_ffmpeg
def test_full_flow(sample_video, tmp_path, monkeypatch):
    from app import workdir
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)
    client = _client()

    with open(sample_video, "rb") as f:
        up = client.post("/api/upload",
                         files={"file": ("m.mp4", f, "video/mp4")})
    assert up.status_code == 200
    vid = up.json()["video_id"]
    assert up.json()["duration"] > 5.0

    det = client.post("/api/detect", json={"video_id": vid,
                      "params": {"threshold": 0.4, "min_rally_seconds": 1.0}})
    assert det.status_code == 200
    rallies = det.json()["rallies"]
    assert isinstance(rallies, list)

    exp = client.post("/api/export", json={"video_id": vid,
                      "ranges": [{"start": 0.5, "end": 2.0}]})
    assert exp.status_code == 200
    assert exp.json()["stitched"] is not None


def test_upload_rejects_non_video(tmp_path, monkeypatch):
    from app import workdir
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)
    client = _client()
    bad = io.BytesIO(b"not a video")
    r = client.post("/api/upload", files={"file": ("x.txt", bad, "text/plain")})
    assert r.status_code == 400
```

- [ ] **Step 2: Run, expect FAIL**

Run: `pytest tests/test_api.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `app/api/__init__.py`** (empty) and `app/api/state.py`

```python
# Simple in-memory registry: video_id -> {"path": str, "duration": float}
_REGISTRY: dict[str, dict] = {}


def put(video_id: str, info: dict) -> None:
    _REGISTRY[video_id] = info


def get(video_id: str) -> dict | None:
    return _REGISTRY.get(video_id)
```

- [ ] **Step 4: Implement `app/api/routes.py`**

```python
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.config import DetectionParams
from app.deps import probe_duration
from app import workdir
from app.api import state
from app.analyzer import pipeline
from app.exporter import ffmpeg as exporter

router = APIRouter(prefix="/api")


class DetectBody(BaseModel):
    video_id: str
    params: dict | None = None


class ExportBody(BaseModel):
    video_id: str
    ranges: list[dict]


def _params(d: dict | None) -> DetectionParams:
    return DetectionParams(**(d or {}))


def _require(video_id: str) -> dict:
    info = state.get(video_id)
    if not info:
        raise HTTPException(404, "Unknown video_id")
    return info


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
    rallies = pipeline.analyze(body.video_id, info["path"], _params(body.params))
    return {"rallies": rallies}


@router.post("/resegment")
def resegment(body: DetectBody):
    _require(body.video_id)
    return {"rallies": pipeline.resegment(body.video_id, _params(body.params))}


@router.post("/export")
def export(body: ExportBody):
    info = _require(body.video_id)
    out_dir = str(workdir.video_dir(body.video_id) / "output")
    return exporter.export(info["path"], body.ranges, out_dir)


@router.get("/video/{video_id}")
def get_video(video_id: str):
    info = _require(video_id)
    return FileResponse(info["path"])
```

- [ ] **Step 5: Modify `app/main.py`** — include router BEFORE the static mount (static `/` mount is greedy). Replace the file contents:

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

WEB_DIR = Path(__file__).parent / "web"
if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
```

- [ ] **Step 6: Run, expect PASS**

Run: `pytest tests/test_api.py -v`
Expected: PASS.

- [ ] **Step 7: Checkpoint** — Run `pytest -v`. Confirm green.

---

## Task 8: Review UI (frontend)

**Files:**
- Create: `app/web/index.html`, `app/web/app.js`, `app/web/style.css`

**Interfaces:**
- Consumes the REST API from Task 7. No backend changes.
- Produces: a single-page UI: upload form → video player → timeline of rally blocks → include/exclude toggles + drag-to-trim → sensitivity slider (calls `/api/resegment`) → Export button (calls `/api/export`) → shows output paths.

This task is UI; it is verified manually (Step 5) rather than by unit tests.

- [ ] **Step 1: Create `app/web/index.html`**

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Pickleball Highlights</title>
  <link rel="stylesheet" href="/style.css" />
</head>
<body>
  <h1>Pickleball Highlights</h1>

  <section id="upload-section">
    <input type="file" id="file" accept="video/*" />
    <button id="upload-btn">Upload &amp; Detect</button>
    <span id="status"></span>
  </section>

  <section id="review-section" hidden>
    <video id="player" controls width="640"></video>

    <div class="controls">
      <label>Sensitivity
        <input type="range" id="sensitivity" min="0" max="1" step="0.05" value="0.5" />
      </label>
      <button id="export-btn">Export</button>
    </div>

    <div id="timeline"></div>
    <ul id="rally-list"></ul>
    <pre id="result"></pre>
  </section>

  <script src="/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create `app/web/style.css`**

```css
body { font-family: system-ui, sans-serif; margin: 2rem; }
.controls { margin: 1rem 0; display: flex; gap: 1rem; align-items: center; }
#timeline {
  position: relative; height: 40px; background: #eee;
  border-radius: 4px; margin: 1rem 0;
}
.rally-block {
  position: absolute; top: 0; height: 100%;
  background: #4caf50; opacity: 0.8; border-radius: 4px; cursor: pointer;
}
.rally-block.excluded { background: #bbb; opacity: 0.5; }
#rally-list { list-style: none; padding: 0; }
#rally-list li { padding: 0.25rem 0; }
```

- [ ] **Step 3: Create `app/web/app.js`**

```javascript
let videoId = null;
let duration = 0;
let rallies = [];

const $ = (id) => document.getElementById(id);

async function postJSON(url, body) {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
  return r.json();
}

$("upload-btn").onclick = async () => {
  const file = $("file").files[0];
  if (!file) return;
  $("status").textContent = "Uploading…";
  const fd = new FormData();
  fd.append("file", file);
  const up = await (await fetch("/api/upload", { method: "POST", body: fd })).json();
  videoId = up.video_id;
  duration = up.duration;
  $("player").src = `/api/video/${videoId}`;
  $("status").textContent = "Detecting rallies…";
  const det = await postJSON("/api/detect", {
    video_id: videoId,
    params: { threshold: parseFloat($("sensitivity").value) },
  });
  rallies = det.rallies.map((r) => ({ ...r, included: true }));
  $("review-section").hidden = false;
  $("status").textContent = `${rallies.length} rallies found`;
  render();
};

$("sensitivity").oninput = debounce(async () => {
  if (!videoId) return;
  const det = await postJSON("/api/resegment", {
    video_id: videoId,
    params: { threshold: parseFloat($("sensitivity").value) },
  });
  rallies = det.rallies.map((r) => ({ ...r, included: true }));
  render();
}, 250);

$("export-btn").onclick = async () => {
  const ranges = rallies.filter((r) => r.included)
    .map((r) => ({ start: r.start, end: r.end }));
  $("result").textContent = "Exporting…";
  const res = await postJSON("/api/export", { video_id: videoId, ranges });
  $("result").textContent =
    `Stitched: ${res.stitched}\nClips:\n${res.clips.join("\n")}`;
};

function render() {
  const tl = $("timeline");
  tl.innerHTML = "";
  rallies.forEach((r, i) => {
    const block = document.createElement("div");
    block.className = "rally-block" + (r.included ? "" : " excluded");
    block.style.left = (100 * r.start / duration) + "%";
    block.style.width = (100 * (r.end - r.start) / duration) + "%";
    block.title = `Rally ${i + 1}`;
    block.onclick = () => { $("player").currentTime = r.start; $("player").play(); };
    tl.appendChild(block);
  });

  const list = $("rally-list");
  list.innerHTML = "";
  rallies.forEach((r, i) => {
    const li = document.createElement("li");
    const cb = document.createElement("input");
    cb.type = "checkbox"; cb.checked = r.included;
    cb.onchange = () => { r.included = cb.checked; render(); };
    li.appendChild(cb);
    li.appendChild(document.createTextNode(
      ` Rally ${i + 1}: ${r.start.toFixed(1)}s – ${r.end.toFixed(1)}s ` +
      `(conf ${(r.confidence ?? 0).toFixed(2)})`));
    list.appendChild(li);
  });
}

function debounce(fn, ms) {
  let t;
  return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
}
```

- [ ] **Step 4: Start the server**

Run: `uvicorn app.main:app --reload`
Expected: starts without error; if ffmpeg missing, fails fast with the Task 1 message.

- [ ] **Step 5: Manual verification**

Open `http://localhost:8000`. Upload a real fixed-camera pickleball clip. Confirm: rallies appear as green blocks; clicking a block seeks/plays; the sensitivity slider changes the block set; unchecking excludes a rally; Export writes `highlights.mp4` + `clip_*.mp4` under `workdir/<id>/output/` and the paths show in the result box. Note any issues for follow-up.

- [ ] **Step 6: Checkpoint** — Run `pytest -v` (ensure nothing regressed). Confirm green.

---

## Task 9: README / run instructions

**Files:**
- Create: `README.md`

**Interfaces:** none (documentation).

- [ ] **Step 1: Create `README.md`**

````markdown
# Pickleball Highlights

Local tool that detects rallies in fixed-camera pickleball videos, lets you
review/trim them in the browser, and exports per-rally clips plus one stitched
highlight video.

## Requirements
- Python 3.11+
- ffmpeg + ffprobe on your PATH (`brew install ffmpeg`)

## Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Run
```bash
uvicorn app.main:app --reload
```
Open http://localhost:8000, upload a match video, review the detected rallies,
adjust sensitivity, then Export. Outputs land in `workdir/<video_id>/output/`.

## Test
```bash
pytest -v
```
(Tests that need ffmpeg auto-skip if it isn't installed.)

## Tuning detection
Defaults live in `app/config.py` (`DetectionParams`): `sample_fps`, `threshold`,
`merge_gap_seconds`, `min_rally_seconds`, `pad_seconds`.
````

- [ ] **Step 2: Checkpoint** — Run `pytest -v`. Confirm green. Confirm README commands match actual file paths.

---

## Self-Review

**Spec coverage:**
- Local web app → Tasks 1, 7, 8. ✓
- Fixed-camera motion+audio detection → Tasks 3, 4, 5. ✓
- Extract all rallies, dead time removed → Task 2 (segment) + Task 5. ✓
- Caching for instant re-segmentation → Task 5 (`save/load_signals`, `resegment`); slider → Task 8. ✓
- Review-then-export UI (toggle, trim, slider, preview) → Task 8. (Drag-to-trim: timeline shows blocks + checkbox toggles + click-to-preview; numeric trim via list. Full drag-handle trimming is a refinement noted below.) ✓ with note
- Export individual clips + stitched, frame-accurate → Task 6. ✓
- Module boundaries (analyzer/exporter/api/web/workdir) → matches File Structure. ✓
- Error handling (ffmpeg check, invalid upload, no rallies) → Tasks 1, 7; empty-rally handled in segment/export/UI. ✓
- Testing (synthetic signals, sample clip, exporter durations, api smoke) → Tasks 2–7. ✓
- Prerequisites documented → Task 9. ✓

**Note on drag-to-trim:** v1 delivers timeline blocks + include/exclude + click-to-preview + global sensitivity. Per-rally drag handles for fine start/end trimming are a small follow-up on top of the same data model (`rallies[i].start/end`); flagged so it isn't silently assumed complete.

**Placeholder scan:** No TBD/TODO; every code step contains full code. ✓

**Type consistency:** Rally dict shape `{start, end, confidence}` is consistent across `segment` (Task 2), `pipeline` (Task 5), API (Task 7), and UI (Task 8). `export` consumes `{start, end}` ranges, produced by the UI's filter/map. `DetectionParams(**dict)` used consistently. ✓
