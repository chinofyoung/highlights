# Task 4 Report: Motion Energy Extraction

## STATUS: COMPLETE

## Files Created

- `app/analyzer/motion.py` — implements `motion_energy(video_path, sample_fps) -> np.ndarray`
- `tests/test_motion.py` — TDD test asserting motion energy is higher during the moving middle segment

## TDD Steps

### Step 1: Wrote failing test
`tests/test_motion.py` written verbatim from brief.

### Step 2: Confirmed FAIL
```
ImportError: cannot import name 'motion' from 'app.analyzer'
```
(Exit code 2 — collection error as expected; module did not exist yet.)

### Step 3: Implemented `app/analyzer/motion.py`
Code written verbatim from brief. Reads all frames via OpenCV, samples every `step`-th frame (derived from `src_fps / sample_fps`), converts to 160×120 grayscale, computes mean absolute int16 frame difference. First sampled frame is always `0.0`.

### Step 4: Confirmed PASS
```
tests/test_motion.py::test_motion_energy_higher_during_movement PASSED  [100%]
1 passed in 18.20s
```

## Step 5: Full Suite (Checkpoint)

```
============================= test session starts ==============================
platform darwin -- Python 3.10.8, pytest-9.1.0, pluggy-1.6.0
collected 14 items

tests/test_audio.py::test_extract_wav_creates_file PASSED                [  7%]
tests/test_audio.py::test_audio_energy_higher_during_sine PASSED         [ 14%]
tests/test_deps.py::test_ffmpeg_available_returns_bool PASSED            [ 21%]
tests/test_deps.py::test_probe_duration_reads_length PASSED              [ 28%]
tests/test_deps.py::test_probe_duration_rejects_non_video PASSED         [ 35%]
tests/test_motion.py::test_motion_energy_higher_during_movement PASSED   [ 42%]
tests/test_segment.py::test_normalize_constant_is_zeros PASSED           [ 50%]
tests/test_segment.py::test_normalize_scales_to_unit PASSED              [ 57%]
tests/test_segment.py::test_combine_takes_max PASSED                     [ 64%]
tests/test_segment.py::test_segment_finds_single_active_span PASSED      [ 71%]
tests/test_segment.py::test_segment_merges_short_gap PASSED              [ 78%]
tests/test_segment.py::test_segment_drops_short_span PASSED              [ 85%]
tests/test_segment.py::test_segment_applies_padding_and_clamps PASSED    [ 92%]
tests/test_segment.py::test_segment_empty_when_all_quiet PASSED          [100%]

14 passed in 0.78s
==============================
```

## Deviations

None. Both files match the brief exactly verbatim.

## Concerns

None. OpenCV opened the libx264/AAC mp4 fixture without any codec issues. No skips occurred; ffmpeg was found on PATH.
