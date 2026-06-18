# Serve Detection + Rally Accuracy — Design Spec

**Date:** 2026-06-18
**Status:** Approved for planning

## Summary

Add **serve** as a filterable clip category alongside **rally**, and improve
rally-detection accuracy. Both build on one new signal — paddle-hit **onset
detection** — plus an objective **evaluation harness** so accuracy changes are
measured, not guessed.

A serve is the *opening slice* of a rally (rally start through the second
paddle hit + padding), derived from rallies we already detect — not a separate
detector. Every rally therefore has a serve by construction. The frontend
exposes both a serve variant and a rally variant of each segment behind
filter chips, so the user can view/export serves only, rallies only, or both.

Rally accuracy is improved with three techniques that all leverage onsets or
self-calibration: onset gating, smarter motion/audio combination, and adaptive
thresholding. Camera-motion stabilization is explicitly out of scope.

## Goals

- Detect and export serve clips, filterable independently of full rallies.
- Measurably improve rally precision/recall via a ground-truth eval harness.
- Keep re-segmentation instant (no re-extraction) by caching all signals.
- Add no heavy dependencies (stay numpy + `wave` + OpenCV + ffmpeg).

## Non-Goals (YAGNI)

- No separate ML serve/rally classifier.
- No ball tracking or scoreboard OCR.
- No camera-motion stabilization (optical flow). Revisit only if real footage
  proves shaky once the harness exists.

## Current System (baseline)

Pipeline (`app/analyzer/`): sample frames at `sample_fps`, compute frame-diff
**motion energy** (`motion.py`) and **audio RMS** (`audio.py`); `segment.py`
normalizes each, takes `max(motion, audio)`, smooths ~0.5s, thresholds at
`0.5`, merges gaps < `merge_gap_seconds`, drops spans < `min_rally_seconds`,
pads by `pad_seconds`. Signals are cached as `.npz` (`workdir.py`) so
`resegment()` retunes params without re-extracting. Segments are dicts
`{start, end, confidence}`. Frontend `Rally` is `{start, end, confidence,
included}`. No onsets, no metrics, no serve concept today.

## Architecture

New modules:
- `app/analyzer/onsets.py` — band-passed paddle-hit onset detection (numpy).
- `app/analyzer/serve.py` — derive a serve slice from a rally + onsets.
- `app/eval/` + `scripts/eval.py` — ground-truth metrics harness.

Changed:
- `app/analyzer/pipeline.py` — compute & cache onsets in `analyze()`; new
  combine → adaptive-threshold → onset-gate → serve-derive order in
  `resegment()`.
- `app/analyzer/segment.py` — smarter combine, adaptive threshold, onset gating.
- `app/workdir.py` — persist onset times in the `.npz`.
- `app/config.py` — new params (below).
- `app/api/routes.py` — segments carry serve fields (no new endpoint).
- `frontend/` — `Rally` type + filter chips + per-variant clip list + export.

## Component Designs

### Onset detection — `app/analyzer/onsets.py`

Input: the already-extracted 16kHz mono WAV. Steps: band-pass to the paddle-pop
range (`onset_low_hz`..`onset_high_hz`, FFT-based) → rectify → short-window
energy envelope → adaptive-threshold peak-picking with `onset_min_separation_s`
between peaks. Output: a sorted numpy array of onset times in seconds. Pure
numpy — no new dependency. Cached so re-segmentation stays instant.

### Serve derivation — `app/analyzer/serve.py`

For each detected rally, find the first onsets at/after the rally's unpadded
start:
- **≥2 onsets:** `serve_end = second_onset + serve_pad_seconds`.
- **1 onset:** `serve_end = first_onset + serve_pad_seconds`.
- **0 onsets (fallback):** `serve_end = rally_start + serve_fallback_seconds`.

`serve_start` = the rally's padded start. Each segment dict gains `serve_start`,
`serve_end`, and `serve_resolved` (bool: true when real onsets were used, false
on fallback) so UI/metrics can flag low-confidence serves.

### Smarter channel combine — `app/analyzer/segment.py`

Replace `max(motion, audio)` with: a weighted-sum envelope
(`motion_weight`, `audio_weight`) **plus** an AND-style activity gate — when
`require_both` is true, a hop is "active" only where *both* normalized motion
and audio clear their floors (`motion_floor`, `audio_floor`). Kills
single-channel false triggers (silent pans, motionless crowd noise). Setting
`require_both=False` with equal weights recovers near-`max` behavior as a
fallback.

### Adaptive thresholding — `app/analyzer/segment.py`

Per-video relative threshold `threshold = noise_floor + threshold_k * spread`
(noise_floor/spread from the combined signal's robust statistics) when
`adaptive_threshold` is true; the fixed absolute `threshold` is retained as
fallback. Self-calibrates across gyms, mic levels, camera distances. The
harness picks the best `threshold_k`.

### Onset gating — `app/analyzer/segment.py` (post-filter)

After merge + min-duration, count cached onsets inside each segment and drop any
rally with fewer than `min_onsets_per_rally` paddle hits (default 2). Strongest
single false-positive filter; also guarantees survivors have the onsets serve
derivation needs.

### Eval harness — `app/eval/` + `scripts/eval.py`

- **Ground truth:** JSON sidecar `eval/labels/<video_id>.json` =
  `[{ "start": s, "end": s }, ...]` of true rallies, hand-edited.
- **Metrics:** `scripts/eval.py` runs detection over each labeled video and
  matches detected vs. labeled rallies by temporal **IoU** (true positive when
  IoU ≥ cutoff, default 0.5). Reports **precision, recall, F1, mean IoU**,
  overall and per video.
- This is the scoreboard every accuracy change is tuned and justified against.

## Data Flow

`analyze(video_id, video_path, params)`: extract motion (`motion.py`) and audio
(`audio.py`) as today, **plus** onsets (`onsets.py`); cache motion/audio/hop +
onset times in the `.npz` (`workdir.py`); call `resegment()`.

`resegment(video_id, params)`: load motion/audio/onsets →
combine (weighted + AND gate) → smooth (~0.5s) → adaptive threshold →
runs/merge/min-duration → **onset gating** → **serve derivation** → return
enriched segment dicts. All from cached signals → instant retuning.

`/detect` and `/resegment` return the enriched segments. No new endpoint.

## API / Data Model

Segment dict (server):
`{ start, end, confidence, serve_start, serve_end, serve_resolved }`

Frontend `Rally`:
`{ start, end, confidence, serveStart, serveEnd, serveResolved, included }`

## Frontend (chips + variants)

A multi-select chip bar — **Serve** / **Rally** — controls which variants
render. A segment can appear as a serve clip and/or a rally clip depending on
active chips; each rendered clip has its own include checkbox. Export
concatenates included, currently-visible clips in time order, cutting serve
clips to `serveStart..serveEnd` and rally clips to `start..end`.

## Config — `DetectionParams` additions

```python
# onsets
onset_low_hz: float = 1500.0
onset_high_hz: float = 8000.0
onset_min_separation_s: float = 0.20
onset_sensitivity: float = 3.0       # adaptive peak threshold over noise floor

# serve derivation
serve_pad_seconds: float = 1.0       # tail after the 2nd hit
serve_fallback_seconds: float = 3.0  # used when onsets don't resolve

# combine
motion_weight: float = 1.0
audio_weight: float = 1.0
motion_floor: float = 0.3            # AND-gate floors (normalized)
audio_floor: float = 0.3
require_both: bool = True

# adaptive threshold
adaptive_threshold: bool = True
threshold_k: float = 2.0             # noise_floor + k*spread
# fixed `threshold` retained as fallback when adaptive_threshold = False

# onset gating
min_onsets_per_rally: int = 2
```

Existing params (`sample_fps`, `threshold`, `merge_gap_seconds`,
`min_rally_seconds`, `pad_seconds`) are unchanged.

## Testing

- `onsets.py`: synthetic audio with known click positions → onsets at the right
  times; silence → none.
- `serve.py`: rally + synthetic onsets → correct boundary for the ≥2 / 1 /
  0-onset (fallback) cases.
- `segment.py`: combine AND-gate suppresses single-channel activity; adaptive
  threshold self-scales; onset gating drops a segment with too few onsets.
- Pipeline: extend `conftest.py` so the moving segment contains a couple of
  clicks; assert each surviving rally gets a serve slice strictly inside it.
- Eval harness: `scripts/eval.py` runs against a tiny fixture label set and
  computes the expected precision/recall on a known case.

## Rollout / Tuning

1. Land onset detection + caching + serve derivation + frontend chips.
2. Land combine/adaptive-threshold/onset-gating behind their params (defaults
   chosen to be safe; old behavior reachable).
3. Hand-label a handful of real videos; run `scripts/eval.py`; tune
   `threshold_k`, weights/floors, `min_onsets_per_rally`, onset band against
   F1/IoU.
