# Detection + Serve Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Fix two real-footage bugs found via systematic debugging: (1) the new accuracy defaults detect 0 rallies on real video; (2) serve clips are too short (~1.4s).

**Root cause (evidence from two real cached DJI videos):** The adaptive threshold formula `median + 2·MAD` sits above the broadly-active signal of real footage (threshold 0.689 → 0 rallies on the 4.5-min clip); the `require_both` AND-gate zeroes 97% of frames on quiet-audio footage. Serve = `2nd onset + 1s` ≈ 1.4s because onsets are dense.

**Fix (user-chosen):** Restore the original simple detector — `max`-combine + a single fixed threshold — with adaptive/require_both/onset-gating OFF by default (kept as opt-in params). Serve becomes a fixed N seconds from rally start (default 6s), independent of onsets.

**Tech Stack:** Python 3.10+, numpy, FastAPI, pytest. Test command: `.venv/bin/python -m pytest`.

## Global Constraints

- Restore the ORIGINAL detector behavior as the default: `combine = max(normalize(motion), normalize(audio))`, fixed `threshold=0.5`, existing merge/min-duration/pad. This is the proven pre-feature behavior.
- New accuracy features (weighted+AND combine, adaptive threshold, onset gating) must remain reachable via params but be OFF by default.
- Serve clip = `min(rally_start + serve_length_seconds, rally_end)`; default `serve_length_seconds = 6.0`; no onset dependency.
- Onset detection/caching in `analyze()` is RETAINED (cheap; supports opt-in gating and future eval-harness tuning) — do not remove it.
- Git disabled (not a repo): each task ends with a Checkpoint running the suite, no commit.
- Baseline before this plan: 100 passed.

---

### Task 1: Restore simple detector as the default

**Files:**
- Modify: `app/config.py` (defaults + new `combine_mode`)
- Modify: `app/analyzer/segment.py` (`combine` gains a `max` mode)
- Test: `tests/test_segment.py`, `tests/test_config.py`

**Interfaces:**
- Produces: `DetectionParams` with `combine_mode: str = "max"`, and flipped defaults `require_both=False`, `adaptive_threshold=False`, `min_onsets_per_rally=0`. `combine(motion, audio, params)` returns `np.maximum(normalize(motion), normalize(audio))` when `combine_mode == "max"`, else the existing weighted+AND-gate path.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_config.py`:

```python
def test_default_detector_is_simple():
    p = DetectionParams()
    assert p.combine_mode == "max"
    assert p.adaptive_threshold is False
    assert p.require_both is False
    assert p.min_onsets_per_rally == 0
    assert p.threshold == 0.5
```

Append to `tests/test_segment.py`:

```python
def test_combine_max_mode_is_default():
    motion = np.array([0.0, 1.0, 0.0])
    audio = np.array([0.0, 0.0, 0.0])
    p = DetectionParams()  # combine_mode="max" by default
    out = combine(motion, audio, p)
    # max-combine: motion spike survives even with silent audio
    assert out[1] == 1.0
    assert out[0] == 0.0


def test_combine_weighted_mode_still_available():
    motion = np.array([0.0, 1.0, 0.0])
    audio = np.array([0.0, 0.0, 0.0])
    p = DetectionParams(combine_mode="weighted", require_both=True,
                        motion_floor=0.3, audio_floor=0.3)
    out = combine(motion, audio, p)
    # AND-gate zeroes the motion-only spike
    assert np.all(out == 0.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_config.py::test_default_detector_is_simple tests/test_segment.py -k "max_mode or weighted_mode_still" -v`
Expected: FAIL — `combine_mode` missing; defaults not flipped; `combine` has no max branch.

- [ ] **Step 3: Update config defaults**

In `app/config.py`, change the existing lines and add `combine_mode`:

```python
    # combine
    combine_mode: str = "max"           # "max" (default, simple) or "weighted"
    motion_weight: float = 1.0
    audio_weight: float = 1.0
    motion_floor: float = 0.3           # AND-gate floors (weighted mode only)
    audio_floor: float = 0.3
    require_both: bool = False           # opt-in (weighted mode only)

    # adaptive threshold
    adaptive_threshold: bool = False     # opt-in; default uses fixed `threshold`
    threshold_k: float = 2.0

    # onset gating
    min_onsets_per_rally: int = 0        # opt-in; 0 disables gating
```

(`threshold` stays `0.5`, and `serve_pad_seconds`/`serve_fallback_seconds` stay as-is — Task 2 supersedes their use.)

- [ ] **Step 4: Add the max branch to combine**

In `app/analyzer/segment.py`, replace `combine`:

```python
def combine(motion: np.ndarray, audio: np.ndarray,
            params: DetectionParams) -> np.ndarray:
    m = normalize(motion)
    a = normalize(audio)
    if getattr(params, "combine_mode", "max") == "max":
        return np.maximum(m, a)
    denom = params.motion_weight + params.audio_weight
    env = params.motion_weight * m + params.audio_weight * a
    if denom > 0:
        env = env / denom
    if params.require_both:
        gate = (m >= params.motion_floor) & (a >= params.audio_floor)
        env = env * gate
    return env
```

- [ ] **Step 5: Update existing weighted-combine tests to opt in**

Earlier tests assumed the weighted path was the default. In `tests/test_segment.py`, the existing tests `test_combine_and_gate_suppresses_single_channel`, `test_combine_passes_when_both_active`, `test_combine_weighted_average`, and `test_combine_require_both_false_is_max_like` must pass `combine_mode="weighted"` in their `DetectionParams(...)` so they exercise the weighted path. Add `combine_mode="weighted"` to each of those tests' params (do not change their assertions).

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_segment.py tests/test_config.py -v`
Expected: PASS (new tests + updated weighted tests).

- [ ] **Step 7: Checkpoint**

Run: `.venv/bin/python -m pytest -q`
Expected: NOTE — `tests/test_pipeline.py::test_pipeline_caches_onsets_and_derives_serves` and the two `test_analyze_*`/`test_resegment_*` tests may change rally counts because the default detector changed. If any pipeline test now fails due to the new defaults, that is expected and is fixed/reconciled in Task 2 (which also revisits the pipeline serve assertions). Report exactly which tests fail and why; do NOT loosen assertions here.

---

### Task 2: Fixed-length serve clips

**Files:**
- Modify: `app/config.py` (add `serve_length_seconds`)
- Modify: `app/analyzer/serve.py` (`derive_serve` → fixed length, drop onset dependency)
- Modify: `app/analyzer/pipeline.py` (update `derive_serve` call)
- Test: `tests/test_serve.py` (rewrite for fixed-length), `tests/test_pipeline.py` (serve assertions)

**Interfaces:**
- Consumes: `DetectionParams.serve_length_seconds` (new, default 6.0).
- Produces: `derive_serve(segment: dict, params: DetectionParams) -> dict` (NO onsets arg) returning the segment plus `serve_start = segment["start"]`, `serve_end = min(start + serve_length_seconds, segment["end"])`, `serve_resolved = True`.

- [ ] **Step 1: Add the config field**

In `app/config.py`, under serve derivation:

```python
    # serve derivation
    serve_length_seconds: float = 6.0   # serve clip = first N seconds of the rally
    serve_pad_seconds: float = 1.0      # (unused by default fixed-length serve; opt-in remnant)
    serve_fallback_seconds: float = 3.0 # (unused by default fixed-length serve; opt-in remnant)
```

- [ ] **Step 2: Write the failing tests (rewrite test_serve.py)**

Replace the body of `tests/test_serve.py` with:

```python
import numpy as np
from app.config import DetectionParams
from app.analyzer.serve import derive_serve

SEG = {"start": 10.0, "end": 20.0, "confidence": 0.8}


def test_serve_is_fixed_length_from_start():
    p = DetectionParams(serve_length_seconds=6.0)
    out = derive_serve(SEG, p)
    assert out["serve_start"] == 10.0
    assert out["serve_end"] == 16.0          # 10 + 6
    assert out["serve_resolved"] is True
    assert out["start"] == 10.0 and out["end"] == 20.0  # original fields preserved


def test_serve_clamped_to_short_rally():
    short = {"start": 10.0, "end": 13.0, "confidence": 0.5}
    p = DetectionParams(serve_length_seconds=6.0)
    out = derive_serve(short, p)
    assert out["serve_end"] == 13.0          # clamped to rally end


def test_serve_length_is_configurable():
    p = DetectionParams(serve_length_seconds=4.0)
    out = derive_serve(SEG, p)
    assert out["serve_end"] == 14.0          # 10 + 4
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_serve.py -v`
Expected: FAIL — `derive_serve` still takes an `onsets` arg / uses onset logic.

- [ ] **Step 4: Rewrite derive_serve**

Replace `app/analyzer/serve.py`:

```python
from app.config import DetectionParams


def derive_serve(segment: dict, params: DetectionParams) -> dict:
    start = segment["start"]
    serve_end = min(start + params.serve_length_seconds, segment["end"])
    return {**segment, "serve_start": start, "serve_end": serve_end,
            "serve_resolved": True}
```

- [ ] **Step 5: Update the pipeline call**

In `app/analyzer/pipeline.py`, `resegment()`, change the final line from
`return [serve_mod.derive_serve(r, onsets, params) for r in rallies]` to:

```python
    return [serve_mod.derive_serve(r, params) for r in rallies]
```

(Onset computation/caching in `analyze()` stays; `gate_by_onsets` still runs but is a no-op when `min_onsets_per_rally == 0`.)

- [ ] **Step 6: Update the pipeline serve test**

In `tests/test_pipeline.py::test_pipeline_caches_onsets_and_derives_serves`, the serve assertions must reflect fixed-length serves under the new defaults. Replace that test's body with params that exercise the default simple detector and assert fixed-length serves:

```python
@requires_ffmpeg
def test_pipeline_caches_onsets_and_derives_serves(sample_video, tmp_path, monkeypatch):
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)
    params = DetectionParams(threshold=0.4, min_rally_seconds=1.0,
                             serve_length_seconds=2.0)
    rallies = pipeline.analyze("vid", sample_video, params)

    # onsets are still cached (retained for opt-in gating / tuning)
    _, _, _, onsets = workdir.load_signals("vid")
    assert onsets.size >= 0

    assert len(rallies) >= 1
    for r in rallies:
        assert r["serve_start"] == r["start"]
        assert r["start"] < r["serve_end"] <= r["end"]
        assert r["serve_resolved"] is True
        # fixed-length: serve_end is start+2.0 unless clamped to a shorter rally
        expected = min(r["start"] + 2.0, r["end"])
        assert abs(r["serve_end"] - expected) < 1e-6

    again = pipeline.resegment("vid", params)
    assert again and "serve_end" in again[0]
```

If `test_analyze_detects_middle_rally` or `test_resegment_uses_cache` now fail under the simple defaults (they previously set `require_both=False, min_onsets_per_rally=0` which remains valid), reconcile only by adjusting params to the new defaults WITHOUT weakening their core assertion (middle-rally overlap / loose≥strict duration). Report any such change.

- [ ] **Step 7: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_serve.py tests/test_pipeline.py -v`
Expected: PASS.

- [ ] **Step 8: Checkpoint**

Run: `.venv/bin/python -m pytest -q`
Expected: fully green. Report the final pass count.

---

## Self-Review

**Spec coverage:**
- Restore max-combine default → Task 1 (`combine_mode="max"` + max branch). ✅
- Fixed threshold default (adaptive off) → Task 1 (`adaptive_threshold=False`). ✅
- Gating off by default → Task 1 (`min_onsets_per_rally=0`). ✅
- Features remain opt-in → Task 1 (params retained, weighted tests opt in). ✅
- Fixed-length serve, configurable, clamped, onset-independent → Task 2. ✅
- Onset caching retained → Task 2 Step 5 note. ✅

**Placeholder scan:** None — all steps show complete code.

**Type consistency:** `derive_serve(segment, params)` (Task 2) matches the updated pipeline call (Task 2 Step 5); `combine_mode` introduced in Task 1 is read in `combine` and `DetectionParams`. `serve_length_seconds` defined in Task 2 Step 1 and used in Step 4.
