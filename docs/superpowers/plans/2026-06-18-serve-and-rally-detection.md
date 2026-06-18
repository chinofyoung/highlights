# Serve Detection + Rally Accuracy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add paddle-hit onset detection to derive filterable serve clips from rallies, and improve rally accuracy via onset gating, smarter motion/audio combination, and adaptive thresholding — all validated by a ground-truth eval harness.

**Architecture:** A new numpy onset detector runs once during `analyze()` and is cached alongside motion/audio. `resegment()` gains a new pipeline order (combine → adaptive threshold → segment → onset-gate → serve-derive), all computed from cached signals so retuning stays instant. The frontend surfaces a serve variant and a rally variant of each segment behind filter chips.

**Tech Stack:** Python 3.10+, FastAPI, numpy, OpenCV, `wave`, ffmpeg CLI; React + TypeScript + Vite + Tailwind frontend; pytest.

## Global Constraints

- **No new Python dependencies.** Onset detection must use numpy + `wave` only (no librosa/scipy).
- **Re-segmentation must stay instant** — no re-extraction of motion/audio/onsets in `resegment()`; everything reads from the cached `signals.npz`.
- **Backward compatibility:** `max`-like combine and fixed-threshold behavior must remain reachable via params (`require_both=False`, `adaptive_threshold=False`).
- **Git is disabled for this project** (not a git repo; user policy forbids state-changing git). Each task ends with a **Checkpoint** step that runs the full test suite instead of a commit.
- **Segment dicts** keep their existing keys (`start`, `end`, `confidence`) and only gain new ones (`serve_start`, `serve_end`, `serve_resolved`).
- **Tests that assert ffmpeg behavior** must use the existing `requires_ffmpeg` marker from `tests/conftest.py`.

---

### Task 1: Detection params

**Files:**
- Modify: `app/config.py:4-10`
- Test: `tests/test_config.py` (create)

**Interfaces:**
- Produces: `DetectionParams` with new fields — `onset_low_hz: float`, `onset_high_hz: float`, `onset_min_separation_s: float`, `onset_sensitivity: float`, `serve_pad_seconds: float`, `serve_fallback_seconds: float`, `motion_weight: float`, `audio_weight: float`, `motion_floor: float`, `audio_floor: float`, `require_both: bool`, `adaptive_threshold: bool`, `threshold_k: float`, `min_onsets_per_rally: int`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
from app.config import DetectionParams


def test_new_defaults_present():
    p = DetectionParams()
    assert p.onset_low_hz == 1500.0
    assert p.onset_high_hz == 8000.0
    assert p.onset_min_separation_s == 0.20
    assert p.onset_sensitivity == 3.0
    assert p.serve_pad_seconds == 1.0
    assert p.serve_fallback_seconds == 3.0
    assert p.motion_weight == 1.0
    assert p.audio_weight == 1.0
    assert p.motion_floor == 0.3
    assert p.audio_floor == 0.3
    assert p.require_both is True
    assert p.adaptive_threshold is True
    assert p.threshold_k == 2.0
    assert p.min_onsets_per_rally == 2


def test_existing_defaults_unchanged():
    p = DetectionParams()
    assert p.sample_fps == 8
    assert p.threshold == 0.5
    assert p.merge_gap_seconds == 2.0
    assert p.min_rally_seconds == 2.5
    assert p.pad_seconds == 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — `AttributeError`/assertion on missing `onset_low_hz`.

- [ ] **Step 3: Add the fields**

```python
# app/config.py
from dataclasses import dataclass


@dataclass
class DetectionParams:
    sample_fps: int = 8
    threshold: float = 0.5          # normalized 0..1 (fixed-threshold fallback)
    merge_gap_seconds: float = 2.0
    min_rally_seconds: float = 2.5
    pad_seconds: float = 1.0

    # onsets
    onset_low_hz: float = 1500.0
    onset_high_hz: float = 8000.0
    onset_min_separation_s: float = 0.20
    onset_sensitivity: float = 3.0      # adaptive peak threshold over noise floor

    # serve derivation
    serve_pad_seconds: float = 1.0      # tail after the 2nd hit
    serve_fallback_seconds: float = 3.0 # used when onsets don't resolve

    # combine
    motion_weight: float = 1.0
    audio_weight: float = 1.0
    motion_floor: float = 0.3           # AND-gate floors (normalized)
    audio_floor: float = 0.3
    require_both: bool = True

    # adaptive threshold
    adaptive_threshold: bool = True
    threshold_k: float = 2.0            # noise_floor + k*spread

    # onset gating
    min_onsets_per_rally: int = 2
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Checkpoint**

Run: `pytest -q`
Expected: all existing tests still pass (new params are additive; `_params()` in `app/api/routes.py` auto-allows them since it derives the allowlist from `dataclasses.fields(DetectionParams)`).

---

### Task 2: Onset detection module

**Files:**
- Create: `app/analyzer/onsets.py`
- Test: `tests/test_onsets.py` (create)

**Interfaces:**
- Consumes: `DetectionParams` (Task 1); 16kHz mono WAV produced by `app/analyzer/audio.py:extract_wav`.
- Produces: `detect_onsets(wav_path: str, params: DetectionParams) -> np.ndarray` returning a sorted array of onset times in **seconds**. Helpers `_bandpass(x, rate, low, high)` and `_pick_peaks(env, thr, min_sep)` are internal.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_onsets.py
import wave
import numpy as np
from app.config import DetectionParams
from app.analyzer.onsets import detect_onsets


def _write_wav(path, samples, rate=16000):
    data = np.clip(samples, -1, 1)
    pcm = (data * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())


def _click(rate, t, dur=0.005, freq=3000.0):
    n = int(rate * dur)
    idx = np.arange(n)
    env = np.exp(-idx / (n / 4))
    return np.sin(2 * np.pi * freq * idx / rate) * env


def test_detects_clicks_at_expected_times(tmp_path):
    rate = 16000
    sig = np.zeros(int(rate * 3.0))
    for t in (0.5, 1.5, 2.5):
        start = int(rate * t)
        c = _click(rate, t)
        sig[start:start + c.size] += c
    wav = tmp_path / "clicks.wav"
    _write_wav(wav, sig, rate)

    onsets = detect_onsets(str(wav), DetectionParams())
    assert len(onsets) == 3
    for expected, got in zip((0.5, 1.5, 2.5), sorted(onsets)):
        assert abs(got - expected) < 0.05


def test_silence_yields_no_onsets(tmp_path):
    wav = tmp_path / "silence.wav"
    _write_wav(wav, np.zeros(16000), 16000)
    onsets = detect_onsets(str(wav), DetectionParams())
    assert len(onsets) == 0


def test_empty_audio_returns_empty(tmp_path):
    wav = tmp_path / "empty.wav"
    _write_wav(wav, np.zeros(0), 16000)
    assert detect_onsets(str(wav), DetectionParams()).size == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_onsets.py -v`
Expected: FAIL — `ModuleNotFoundError: app.analyzer.onsets`.

- [ ] **Step 3: Implement the module**

```python
# app/analyzer/onsets.py
import wave
import numpy as np
from app.config import DetectionParams


def _read_wav(wav_path: str):
    with wave.open(wav_path, "rb") as w:
        rate = w.getframerate()
        frames = w.readframes(w.getnframes())
    samples = np.frombuffer(frames, dtype=np.int16).astype(np.float64)
    return samples, rate


def _bandpass(x: np.ndarray, rate: int, low: float, high: float) -> np.ndarray:
    n = x.size
    if n == 0:
        return x
    freqs = np.fft.rfftfreq(n, d=1.0 / rate)
    spec = np.fft.rfft(x)
    mask = (freqs >= low) & (freqs <= high)
    return np.fft.irfft(spec * mask, n=n)


def _pick_peaks(env: np.ndarray, thr: float, min_sep: int) -> np.ndarray:
    n = env.size
    if n == 0:
        return np.zeros(0)
    above = env >= thr
    peaks = []
    last = -min_sep - 1
    i = 0
    while i < n:
        if above[i]:
            j = i
            while j < n and above[j]:
                j += 1
            local = i + int(np.argmax(env[i:j]))
            if local - last >= min_sep:
                peaks.append(local)
                last = local
            i = j
        else:
            i += 1
    return np.asarray(peaks, dtype=float)


def detect_onsets(wav_path: str, params: DetectionParams) -> np.ndarray:
    samples, rate = _read_wav(wav_path)
    if samples.size == 0:
        return np.zeros(0)
    band = _bandpass(samples, rate, params.onset_low_hz, params.onset_high_hz)
    env = np.abs(band)
    win = max(1, int(rate * 0.01))  # ~10ms envelope smoothing
    env = np.convolve(env, np.ones(win) / win, mode="same")
    floor = float(np.median(env))
    mad = float(np.median(np.abs(env - floor))) * 1.4826  # robust std
    if mad < 1e-9:
        return np.zeros(0)
    thr = floor + params.onset_sensitivity * mad
    min_sep = max(1, int(rate * params.onset_min_separation_s))
    peak_idx = _pick_peaks(env, thr, min_sep)
    return np.sort(peak_idx / rate)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_onsets.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Checkpoint**

Run: `pytest -q`
Expected: all pass.

---

### Task 3: Persist onsets in cached signals

**Files:**
- Modify: `app/workdir.py:13-24`
- Test: `tests/test_workdir.py` (create)

**Interfaces:**
- Produces: `save_signals(video_id, motion, audio, hop_seconds, onsets=None)` (new optional `onsets` arg, defaults to empty). `load_signals(video_id)` now returns a **4-tuple** `(motion, audio, hop, onsets)`; missing `onsets` in an old file loads as an empty array.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_workdir.py
import numpy as np
from app import workdir


def test_roundtrip_with_onsets(tmp_path, monkeypatch):
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)
    motion = np.array([0.1, 0.2, 0.3])
    audio = np.array([0.4, 0.5, 0.6])
    onsets = np.array([0.5, 1.5])
    workdir.save_signals("vid", motion, audio, 0.125, onsets)
    m, a, hop, o = workdir.load_signals("vid")
    assert np.allclose(m, motion)
    assert np.allclose(a, audio)
    assert hop == 0.125
    assert np.allclose(o, onsets)


def test_roundtrip_without_onsets(tmp_path, monkeypatch):
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)
    workdir.save_signals("vid", np.array([0.1]), np.array([0.2]), 0.1)
    _, _, _, o = workdir.load_signals("vid")
    assert o.size == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_workdir.py -v`
Expected: FAIL — `load_signals` returns a 3-tuple / `save_signals` rejects the `onsets` arg.

- [ ] **Step 3: Update workdir**

```python
# app/workdir.py  (replace save_signals and load_signals)
def save_signals(video_id: str, motion: np.ndarray, audio: np.ndarray,
                 hop_seconds: float, onsets: np.ndarray | None = None) -> None:
    onsets = np.zeros(0) if onsets is None else np.asarray(onsets, dtype=float)
    np.savez(video_dir(video_id) / "signals.npz",
             motion=motion, audio=audio, hop=np.array([hop_seconds]),
             onsets=onsets)


def load_signals(video_id: str):
    path = video_dir(video_id) / "signals.npz"
    if not path.exists():
        raise FileNotFoundError(f"No cached signals for {video_id}")
    data = np.load(path)
    onsets = data["onsets"] if "onsets" in data.files else np.zeros(0)
    return data["motion"], data["audio"], float(data["hop"][0]), onsets
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_workdir.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Checkpoint**

Run: `pytest -q`
Expected: `tests/test_workdir.py` passes. NOTE: `app/analyzer/pipeline.py:41` still unpacks a 3-tuple and will be fixed in Task 8; if any pipeline test fails here it is expected and resolved by Task 8.

---

### Task 4: Smarter channel combine

**Files:**
- Modify: `app/analyzer/segment.py:15-16`
- Test: `tests/test_segment.py` (add cases)

**Interfaces:**
- Consumes: `DetectionParams` (Task 1).
- Produces: `combine(motion, audio, params) -> np.ndarray` — weighted, normalized envelope with an optional AND-gate. **Signature changes** from `combine(motion, audio)`; the call site in `pipeline.py` is updated in Task 8.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_segment.py  (append)
import numpy as np
from app.config import DetectionParams
from app.analyzer.segment import combine


def test_combine_and_gate_suppresses_single_channel():
    # motion active, audio silent -> gated to ~0 when require_both
    motion = np.array([0.0, 1.0, 0.0])
    audio = np.array([0.0, 0.0, 0.0])
    p = DetectionParams(require_both=True, motion_floor=0.3, audio_floor=0.3)
    out = combine(motion, audio, p)
    assert np.all(out == 0.0)


def test_combine_passes_when_both_active():
    motion = np.array([0.0, 1.0, 0.0])
    audio = np.array([0.0, 1.0, 0.0])
    p = DetectionParams(require_both=True)
    out = combine(motion, audio, p)
    assert out[1] > out[0]
    assert out[1] > out[2]


def test_combine_require_both_false_is_max_like():
    motion = np.array([0.0, 1.0, 0.0])
    audio = np.array([0.0, 0.0, 0.0])
    p = DetectionParams(require_both=False, motion_weight=1.0, audio_weight=0.0)
    out = combine(motion, audio, p)
    assert out[1] > 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_segment.py -k combine -v`
Expected: FAIL — `combine()` takes 2 positional args, not 3.

- [ ] **Step 3: Update combine**

```python
# app/analyzer/segment.py  (replace combine)
def combine(motion: np.ndarray, audio: np.ndarray,
            params: DetectionParams) -> np.ndarray:
    m = normalize(motion)
    a = normalize(audio)
    denom = params.motion_weight + params.audio_weight
    env = params.motion_weight * m + params.audio_weight * a
    if denom > 0:
        env = env / denom
    if params.require_both:
        gate = (m >= params.motion_floor) & (a >= params.audio_floor)
        env = env * gate
    return env
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_segment.py -k combine -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Checkpoint**

Run: `pytest tests/test_segment.py -v`
Expected: combine tests pass. Existing segmentation tests that call `combine(a, b)` (if any) must be updated to `combine(a, b, DetectionParams())`; do so now if the run surfaces them.

---

### Task 5: Adaptive threshold + threshold-aware segment

**Files:**
- Modify: `app/analyzer/segment.py:27-66`
- Test: `tests/test_segment.py` (add cases)

**Interfaces:**
- Consumes: `DetectionParams` (Task 1).
- Produces: `compute_threshold(signal, params) -> float`. `segment(signal, hop_seconds, params, threshold=None)` — when `threshold` is None it falls back to `params.threshold` (preserves existing callers/tests).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_segment.py  (append)
from app.analyzer.segment import compute_threshold, segment


def test_compute_threshold_fixed_when_disabled():
    sig = np.array([0.0, 0.5, 1.0])
    p = DetectionParams(adaptive_threshold=False, threshold=0.42)
    assert compute_threshold(sig, p) == 0.42


def test_compute_threshold_adaptive_scales_with_noise():
    quiet = np.concatenate([np.zeros(90), np.ones(10)])
    p = DetectionParams(adaptive_threshold=True, threshold_k=2.0)
    thr = compute_threshold(quiet, p)
    assert 0.0 < thr <= 1.0


def test_segment_accepts_explicit_threshold():
    # half active above 0.6
    sig = np.concatenate([np.zeros(40), np.full(40, 0.9), np.zeros(40)])
    p = DetectionParams(min_rally_seconds=0.0, pad_seconds=0.0, merge_gap_seconds=0.0)
    out = segment(sig, hop_seconds=0.1, params=p, threshold=0.6)
    assert len(out) == 1
    assert out[0]["start"] >= 4.0 - 1e-6
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_segment.py -k "threshold" -v`
Expected: FAIL — `compute_threshold` undefined; `segment()` has no `threshold` kwarg.

- [ ] **Step 3: Implement**

```python
# app/analyzer/segment.py  (add compute_threshold; update segment signature)
def compute_threshold(signal: np.ndarray, params: DetectionParams) -> float:
    if not params.adaptive_threshold:
        return params.threshold
    s = np.asarray(signal, dtype=float)
    if s.size == 0:
        return params.threshold
    floor = float(np.median(s))
    spread = float(np.median(np.abs(s - floor))) * 1.4826  # robust std (MAD)
    return float(floor + params.threshold_k * spread)


def segment(signal: np.ndarray, hop_seconds: float,
            params: DetectionParams, threshold: float | None = None) -> list[dict]:
    signal = np.asarray(signal, dtype=float)
    thr = params.threshold if threshold is None else threshold
    active = signal >= thr
    # ... (rest of the existing run/merge/pad/min-duration body unchanged,
    #      but use `thr` where it previously used `params.threshold`)
```

Apply only the two-line change inside the existing body: replace the `active = signal >= params.threshold` line with the `thr`-based version above; everything from the `# contiguous runs` comment down stays identical.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_segment.py -k "threshold" -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Checkpoint**

Run: `pytest tests/test_segment.py -v`
Expected: all segment tests pass (existing tests call `segment(sig, hop, params)` with no `threshold` → fall back to `params.threshold`, unchanged behavior).

---

### Task 6: Onset gating

**Files:**
- Modify: `app/analyzer/segment.py`
- Test: `tests/test_segment.py` (add cases)

**Interfaces:**
- Consumes: `DetectionParams` (Task 1); segment dicts with `start`/`end`.
- Produces: `gate_by_onsets(segments: list[dict], onsets: np.ndarray, params) -> list[dict]` — drops segments containing fewer than `min_onsets_per_rally` onsets in `[start, end]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_segment.py  (append)
from app.analyzer.segment import gate_by_onsets


def test_gating_drops_low_onset_segments():
    segs = [
        {"start": 0.0, "end": 5.0, "confidence": 0.9},   # 3 onsets -> keep
        {"start": 10.0, "end": 15.0, "confidence": 0.9}, # 1 onset  -> drop
    ]
    onsets = np.array([0.5, 1.0, 1.5, 11.0])
    p = DetectionParams(min_onsets_per_rally=2)
    out = gate_by_onsets(segs, onsets, p)
    assert len(out) == 1
    assert out[0]["start"] == 0.0


def test_gating_disabled_when_zero():
    segs = [{"start": 0.0, "end": 5.0, "confidence": 0.9}]
    p = DetectionParams(min_onsets_per_rally=0)
    assert gate_by_onsets(segs, np.zeros(0), p) == segs
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_segment.py -k gating -v`
Expected: FAIL — `gate_by_onsets` undefined.

- [ ] **Step 3: Implement**

```python
# app/analyzer/segment.py  (append)
def gate_by_onsets(segments: list[dict], onsets: np.ndarray,
                   params: DetectionParams) -> list[dict]:
    if params.min_onsets_per_rally <= 0:
        return segments
    onsets = np.asarray(onsets, dtype=float)
    out = []
    for s in segments:
        count = int(np.sum((onsets >= s["start"]) & (onsets <= s["end"])))
        if count >= params.min_onsets_per_rally:
            out.append(s)
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_segment.py -k gating -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Checkpoint**

Run: `pytest tests/test_segment.py -v`
Expected: all pass.

---

### Task 7: Serve derivation

**Files:**
- Create: `app/analyzer/serve.py`
- Test: `tests/test_serve.py` (create)

**Interfaces:**
- Consumes: `DetectionParams` (Task 1); a segment dict with `start`/`end`/`confidence`; onset times array.
- Produces: `derive_serve(segment: dict, onsets: np.ndarray, params) -> dict` returning the segment plus `serve_start`, `serve_end`, `serve_resolved`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_serve.py
import numpy as np
from app.config import DetectionParams
from app.analyzer.serve import derive_serve

SEG = {"start": 10.0, "end": 20.0, "confidence": 0.8}


def test_two_onsets_use_second_hit():
    p = DetectionParams(serve_pad_seconds=1.0)
    out = derive_serve(SEG, np.array([10.5, 11.5, 14.0]), p)
    assert out["serve_start"] == 10.0
    assert out["serve_end"] == 12.5      # 11.5 + 1.0
    assert out["serve_resolved"] is True
    assert out["start"] == 10.0 and out["end"] == 20.0


def test_one_onset_uses_first_hit():
    p = DetectionParams(serve_pad_seconds=1.0)
    out = derive_serve(SEG, np.array([10.5]), p)
    assert out["serve_end"] == 11.5
    assert out["serve_resolved"] is True


def test_no_onsets_falls_back_to_fixed():
    p = DetectionParams(serve_fallback_seconds=3.0)
    out = derive_serve(SEG, np.zeros(0), p)
    assert out["serve_end"] == 13.0      # 10.0 + 3.0
    assert out["serve_resolved"] is False


def test_serve_end_clamped_to_segment_end():
    p = DetectionParams(serve_fallback_seconds=999.0)
    out = derive_serve(SEG, np.zeros(0), p)
    assert out["serve_end"] == 20.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_serve.py -v`
Expected: FAIL — `ModuleNotFoundError: app.analyzer.serve`.

- [ ] **Step 3: Implement**

```python
# app/analyzer/serve.py
import numpy as np
from app.config import DetectionParams


def derive_serve(segment: dict, onsets: np.ndarray,
                 params: DetectionParams) -> dict:
    onsets = np.asarray(onsets, dtype=float)
    start = segment["start"]
    inside = np.sort(onsets[onsets >= start])
    if inside.size >= 2:
        serve_end = float(inside[1]) + params.serve_pad_seconds
        resolved = True
    elif inside.size == 1:
        serve_end = float(inside[0]) + params.serve_pad_seconds
        resolved = True
    else:
        serve_end = start + params.serve_fallback_seconds
        resolved = False
    serve_end = min(serve_end, segment["end"])
    return {**segment, "serve_start": start, "serve_end": serve_end,
            "serve_resolved": resolved}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_serve.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Checkpoint**

Run: `pytest -q`
Expected: all pass.

---

### Task 8: Wire the pipeline

**Files:**
- Modify: `app/analyzer/pipeline.py:19-45`
- Test: `tests/test_pipeline.py` (extend), `tests/conftest.py:14-33` (extend)

**Interfaces:**
- Consumes: `onsets.detect_onsets` (Task 2), `workdir.save_signals/load_signals` 4-tuple (Task 3), `segment.combine/compute_threshold/segment/gate_by_onsets` (Tasks 4-6), `serve.derive_serve` (Task 7).
- Produces: `analyze()` caches onsets; `resegment()` returns segment dicts each carrying `serve_start`, `serve_end`, `serve_resolved`.

- [ ] **Step 1: Extend the sample-video fixture to contain paddle-like clicks**

```python
# tests/conftest.py  — replace the "moving segment" ffmpeg call (lines 26-28)
# Add high-frequency clicks (paddle-like) by mixing short noise bursts into the sine.
    _run(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc2=s=320x240:d=2:r=8",
          "-f", "lavfi",
          "-i", "sine=frequency=1000:duration=2,"
                "aeval=val(0)+0.6*sin(2*PI*3000*t)*lt(mod(t\\,0.6)\\,0.01)",
          "-t", "2", "-c:v", "libx264", "-c:a", "aac",
          "-pix_fmt", "yuv420p", str(moving)])
```

This injects ~3000 Hz bursts every 0.6s within the 2-4s active region so onset detection finds multiple hits there.

- [ ] **Step 2: Write the failing test**

```python
# tests/test_pipeline.py  (append)
from app.config import DetectionParams
from app.analyzer import pipeline
from app import workdir


@requires_ffmpeg
def test_pipeline_caches_onsets_and_derives_serves(sample_video, tmp_path, monkeypatch):
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)
    params = DetectionParams(min_onsets_per_rally=1)  # lenient for the synthetic clip
    rallies = pipeline.analyze("vid", sample_video, params)

    # onsets were cached
    _, _, _, onsets = workdir.load_signals("vid")
    assert onsets.size >= 1

    # at least one rally, each with a serve slice strictly inside it
    assert len(rallies) >= 1
    for r in rallies:
        assert r["serve_start"] == r["start"]
        assert r["start"] < r["serve_end"] <= r["end"]
        assert "serve_resolved" in r

    # resegment returns the same enriched shape without re-extraction
    again = pipeline.resegment("vid", params)
    assert again and "serve_end" in again[0]
```

Import note: `requires_ffmpeg` and `sample_video` come from `tests/conftest.py` (already importable in the test session).

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_pipeline.py -k onsets -v`
Expected: FAIL — `resegment` unpacks a 3-tuple / `combine` called with 2 args / no `serve_end`.

- [ ] **Step 4: Rewrite analyze() and resegment()**

```python
# app/analyzer/pipeline.py  (replace analyze and resegment; add imports)
from app.analyzer import onsets as onsets_mod
from app.analyzer import serve as serve_mod


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
    onsets = onsets_mod.detect_onsets(wav, params)

    workdir.save_signals(video_id, motion, audio, hop, onsets)
    result = resegment(video_id, params)
    if progress_callback is not None:
        progress_callback(1.0)
    return result


def resegment(video_id: str, params: DetectionParams) -> list[dict]:
    motion, audio, hop, onsets = workdir.load_signals(video_id)
    combined = seg.combine(motion, audio, params)
    window = max(1, int(round(0.5 / hop)))   # ~0.5s smoothing
    combined = seg.smooth(combined, window)
    thr = seg.compute_threshold(combined, params)
    rallies = seg.segment(combined, hop_seconds=hop, params=params, threshold=thr)
    rallies = seg.gate_by_onsets(rallies, onsets, params)
    return [serve_mod.derive_serve(r, onsets, params) for r in rallies]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_pipeline.py -v`
Expected: PASS (existing pipeline tests + the new one). If `ffmpeg` is absent, the new test skips via `requires_ffmpeg`.

- [ ] **Step 6: Checkpoint**

Run: `pytest -q`
Expected: full suite green.

---

### Task 9: Eval harness (metrics + CLI)

**Files:**
- Create: `app/eval/__init__.py`, `app/eval/metrics.py`, `scripts/eval.py`
- Create: `eval/labels/.gitkeep`
- Test: `tests/test_eval.py` (create)

**Interfaces:**
- Consumes: detected and labeled rally dicts with `start`/`end`.
- Produces: `iou(a, b) -> float`; `score(detected, labels, cutoff=0.5) -> dict` with keys `tp, fp, fn, precision, recall, f1, mean_iou`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_eval.py
from app.eval.metrics import iou, score


def test_iou_basic():
    assert iou({"start": 0, "end": 10}, {"start": 0, "end": 10}) == 1.0
    assert iou({"start": 0, "end": 10}, {"start": 20, "end": 30}) == 0.0
    assert abs(iou({"start": 0, "end": 10}, {"start": 5, "end": 15}) - (5 / 15)) < 1e-9


def test_score_perfect():
    labels = [{"start": 0, "end": 10}, {"start": 20, "end": 30}]
    detected = [{"start": 0, "end": 10}, {"start": 20, "end": 30}]
    s = score(detected, labels)
    assert s["precision"] == 1.0 and s["recall"] == 1.0 and s["f1"] == 1.0
    assert s["tp"] == 2 and s["fp"] == 0 and s["fn"] == 0


def test_score_with_fp_and_fn():
    labels = [{"start": 0, "end": 10}, {"start": 100, "end": 110}]
    detected = [{"start": 0, "end": 10}, {"start": 50, "end": 60}]
    s = score(detected, labels, cutoff=0.5)
    assert s["tp"] == 1 and s["fp"] == 1 and s["fn"] == 1
    assert s["precision"] == 0.5 and s["recall"] == 0.5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_eval.py -v`
Expected: FAIL — `ModuleNotFoundError: app.eval.metrics`.

- [ ] **Step 3: Implement metrics**

```python
# app/eval/__init__.py
```

```python
# app/eval/metrics.py
def iou(a: dict, b: dict) -> float:
    inter = max(0.0, min(a["end"], b["end"]) - max(a["start"], b["start"]))
    union = (a["end"] - a["start"]) + (b["end"] - b["start"]) - inter
    return inter / union if union > 0 else 0.0


def score(detected: list[dict], labels: list[dict], cutoff: float = 0.5) -> dict:
    matched = set()
    tp = 0
    matched_ious = []
    for d in detected:
        best_j, best_iou = -1, 0.0
        for j, l in enumerate(labels):
            if j in matched:
                continue
            v = iou(d, l)
            if v > best_iou:
                best_iou, best_j = v, j
        if best_j >= 0 and best_iou >= cutoff:
            tp += 1
            matched.add(best_j)
            matched_ious.append(best_iou)
    fp = len(detected) - tp
    fn = len(labels) - tp
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    mean_iou = sum(matched_ious) / len(matched_ious) if matched_ious else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision,
            "recall": recall, "f1": f1, "mean_iou": mean_iou}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_eval.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Add the CLI runner and labels dir**

```python
# scripts/eval.py
"""Run rally detection over labeled videos and report precision/recall/F1/IoU.

Usage:
  python scripts/eval.py --videos eval/videos --labels eval/labels [--cutoff 0.5]

Each label file is eval/labels/<video_id>.json = [{"start": s, "end": s}, ...].
The matching video is eval/videos/<video_id>.<ext>.
"""
import argparse
import json
import sys
from pathlib import Path

# allow running from repo root without install
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import DetectionParams           # noqa: E402
from app.analyzer import pipeline                 # noqa: E402
from app.eval.metrics import score                # noqa: E402


def _find_video(videos_dir: Path, video_id: str) -> Path | None:
    for p in videos_dir.glob(f"{video_id}.*"):
        if p.suffix.lower() in {".mp4", ".mov", ".mkv", ".avi"}:
            return p
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--videos", default="eval/videos")
    ap.add_argument("--labels", default="eval/labels")
    ap.add_argument("--cutoff", type=float, default=0.5)
    args = ap.parse_args()

    labels_dir = Path(args.labels)
    videos_dir = Path(args.videos)
    label_files = sorted(labels_dir.glob("*.json"))
    if not label_files:
        print(f"No label files in {labels_dir}")
        return 1

    params = DetectionParams()
    agg = {"tp": 0, "fp": 0, "fn": 0}
    for lf in label_files:
        video_id = lf.stem
        video = _find_video(videos_dir, video_id)
        if video is None:
            print(f"[skip] no video for {video_id}")
            continue
        labels = json.loads(lf.read_text())
        detected = pipeline.analyze(video_id, str(video), params)
        s = score(detected, labels, cutoff=args.cutoff)
        agg["tp"] += s["tp"]; agg["fp"] += s["fp"]; agg["fn"] += s["fn"]
        print(f"{video_id}: P={s['precision']:.2f} R={s['recall']:.2f} "
              f"F1={s['f1']:.2f} IoU={s['mean_iou']:.2f} "
              f"(tp={s['tp']} fp={s['fp']} fn={s['fn']})")

    tp, fp, fn = agg["tp"], agg["fp"], agg["fn"]
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    print(f"\nOVERALL: P={p:.3f} R={r:.3f} F1={f1:.3f} (tp={tp} fp={fp} fn={fn})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

```text
# eval/labels/.gitkeep  (empty file — placeholder so the labels dir exists)
```

- [ ] **Step 6: Smoke-test the CLI surfaces the no-labels path**

Run: `python scripts/eval.py --labels eval/labels`
Expected: prints `No label files in eval/labels` and exits non-zero (no labels yet — correct).

- [ ] **Step 7: Checkpoint**

Run: `pytest -q`
Expected: all pass.

---

### Task 10: Frontend — serve fields, filter chips, export

**Files:**
- Modify: `frontend/src/types.ts:1-6`
- Modify: the rally-list / export component(s) and `frontend/src/api.ts` (read them first to follow existing patterns).
- Test: manual (frontend has no test runner configured).

**Interfaces:**
- Consumes: backend segment dicts with `serve_start`, `serve_end`, `serve_resolved` (Task 8). NOTE: backend uses snake_case JSON keys; map to camelCase at the API boundary if the rest of the frontend uses camelCase.
- Produces: `Rally` type with serve fields; a Serve/Rally chip filter; export that emits the correct ranges.

- [ ] **Step 1: Read the current frontend to find the rally list + export call**

Run: read `frontend/src/api.ts`, `frontend/src/types.ts`, and the component that renders rallies and calls export (grep for `resegment`, `startDetect`, `ranges`, and `included`).
Expected: identify (a) where `Rally[]` is held in state, (b) where the include checkboxes render, (c) where export builds its `ranges` payload.

- [ ] **Step 2: Extend the `Rally` type**

```typescript
// frontend/src/types.ts
export interface Rally {
  start: number;
  end: number;
  confidence: number;
  serveStart: number;
  serveEnd: number;
  serveResolved: boolean;
  included: boolean;
}
```

- [ ] **Step 3: Map snake_case → camelCase where the detect/resegment response is parsed**

In `api.ts` (or wherever the response `rallies` are normalized), map each item:

```typescript
function toRally(r: any): Rally {
  return {
    start: r.start,
    end: r.end,
    confidence: r.confidence,
    serveStart: r.serve_start,
    serveEnd: r.serve_end,
    serveResolved: r.serve_resolved,
    included: true,
  };
}
```

Apply `toRally` to the `rallies` array returned by both `startDetect`'s job result and `resegment`.

- [ ] **Step 4: Add the Serve/Rally chip filter and per-variant rendering**

- Add component state: `const [view, setView] = useState<("serve" | "rally")[]>(["rally"]);`
- Render two toggle chips ("Serve", "Rally") that add/remove from `view` (follow existing Tailwind button styling in the component).
- When `view` includes `"rally"`, render a rally clip per rally using `start..end`. When it includes `"serve"`, render a serve clip per rally using `serveStart..serveEnd` (label fallback-derived serves, where `serveResolved === false`, e.g. a muted "≈" badge). Each rendered clip keeps its own include checkbox state.

- [ ] **Step 5: Build export ranges from visible + included clips**

When building the export payload (the `ranges` array sent to `/export`), emit one range per visible, included clip in time order:

```typescript
const ranges: { start: number; end: number }[] = [];
for (const r of rallies) {
  if (!r.included) continue;
  if (view.includes("serve")) ranges.push({ start: r.serveStart, end: r.serveEnd });
  if (view.includes("rally")) ranges.push({ start: r.start, end: r.end });
}
ranges.sort((a, b) => a.start - b.start);
```

(The backend `/export` already accepts arbitrary `ranges: list[dict]`, so no backend change is needed.)

- [ ] **Step 6: Manual verification**

Run the app (`npm run dev` in `frontend/` + the FastAPI server per README), detect on a real clip, toggle Serve/Rally chips, confirm:
- Rally view shows full-length clips; Serve view shows short opening clips.
- Fallback serves are visually flagged.
- Export with each chip selection produces the expected clip set.

- [ ] **Step 7: Checkpoint**

Run: `pytest -q` (backend unaffected, confirm still green) and confirm the frontend builds: `cd frontend && npm run build`.

---

## Self-Review

**Spec coverage:**
- §2 Onset detection → Task 2. ✅
- §3 Serve derivation (≥2/1/0 onsets, clamp) → Task 7. ✅
- §4 Config params → Task 1. ✅
- §8 Eval harness (labels + IoU + P/R/F1) → Task 9. ✅
- §9 Smarter combine (weighted + AND gate, max-fallback) → Task 4. ✅
- §10 Adaptive threshold (k·spread, fixed fallback) → Task 5. ✅
- §11 Onset gating (min_onsets_per_rally) → Task 6. ✅
- Caching onsets / instant resegment → Tasks 3 + 8. ✅
- API enriched segments → Task 8 (auto via pipeline return; `_params` auto-allows new fields). ✅
- Frontend chips + variants + export → Task 10. ✅
- Pipeline order (combine→threshold→segment→gate→serve) → Task 8. ✅
- Camera stabilization explicitly out of scope → not planned. ✅

**Placeholder scan:** No TBD/TODO; every code step shows full code. The only `.gitkeep` is an intentional empty placeholder file, not a plan gap. Task 10 directs reading existing components first because the frontend wasn't deeply explored — the type, mapping, and export logic are concrete; only DOM styling follows existing patterns.

**Type consistency:** `detect_onsets(wav_path, params)`, `combine(motion, audio, params)`, `compute_threshold(signal, params)`, `segment(signal, hop_seconds, params, threshold=None)`, `gate_by_onsets(segments, onsets, params)`, `derive_serve(segment, onsets, params)`, `score(detected, labels, cutoff)` — names and arities are used identically across Tasks 2–9. `load_signals` 4-tuple is produced in Task 3 and consumed in Task 8. Frontend `Rally` fields (`serveStart`/`serveEnd`/`serveResolved`) match the `toRally` mapping. Consistent.
