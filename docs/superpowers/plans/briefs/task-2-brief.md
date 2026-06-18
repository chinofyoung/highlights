# Task 2: (brief)

## Global Constraints

- **Python version floor:** 3.10+ (3.10.8 is the available interpreter; code is 3.10-compatible).
- **System dependency:** `ffmpeg` and `ffprobe` must be on `PATH`.
- **No heavy audio libs:** audio energy is computed from an ffmpeg-extracted WAV using NumPy only — do NOT add `librosa` or similar.
- **No build step for frontend:** plain `index.html` + JS served as static files.
- **Git is disabled for this project** (user global instruction + not a git repo). Wherever a task would normally `git commit`, instead run the task's full test suite and confirm green as the checkpoint. Do not run any state-changing git command.
- **Frame-accurate cuts:** export must re-encode cut ranges, not stream-copy (stream-copy only cuts on keyframes).
- **Detection defaults:** `sample_fps=8`, `merge_gap_seconds=2.0`, `min_rally_seconds=2.5`, `pad_seconds=1.0`, `threshold=0.5` (normalized 0–1).



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

