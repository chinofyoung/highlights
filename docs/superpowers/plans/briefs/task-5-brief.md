# Task 5: (brief)

## Global Constraints

- **Python version floor:** 3.10+ (3.10.8 is the available interpreter; code is 3.10-compatible).
- **System dependency:** `ffmpeg` and `ffprobe` must be on `PATH`.
- **No heavy audio libs:** audio energy is computed from an ffmpeg-extracted WAV using NumPy only — do NOT add `librosa` or similar.
- **No build step for frontend:** plain `index.html` + JS served as static files.
- **Git is disabled for this project** (user global instruction + not a git repo). Wherever a task would normally `git commit`, instead run the task's full test suite and confirm green as the checkpoint. Do not run any state-changing git command.
- **Frame-accurate cuts:** export must re-encode cut ranges, not stream-copy (stream-copy only cuts on keyframes).
- **Detection defaults:** `sample_fps=8`, `merge_gap_seconds=2.0`, `min_rally_seconds=2.5`, `pad_seconds=1.0`, `threshold=0.5` (normalized 0–1).



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

