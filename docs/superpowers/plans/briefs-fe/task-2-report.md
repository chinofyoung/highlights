# Task 2 Report: Progress Callbacks — Motion + Pipeline

**Status:** COMPLETE — all 32 tests pass.

---

## Files Created / Modified

| Action   | Path                              |
|----------|-----------------------------------|
| Created  | `tests/test_progress.py`          |
| Modified | `app/analyzer/motion.py`          |
| Modified | `app/analyzer/pipeline.py`        |

---

## What Was Done

### Step 1 — Wrote failing tests (`tests/test_progress.py`)

Three tests added verbatim from the brief:
- `test_motion_reports_monotonic_progress` — verifies the callback is called with non-decreasing values in [0, 1].
- `test_motion_without_callback_unchanged` — verifies no-arg call still returns ≥40 frames of energy.
- `test_analyze_reports_progress_ending_at_one` — verifies pipeline ends with `progress_callback(1.0)` and values are monotonic in [0, 1].

### Step 2 — Confirmed FAIL

2 of 3 tests failed with `TypeError: unexpected keyword argument 'progress_callback'` (as expected). The third passed because `motion_energy` without a callback was already working.

### Step 3 — Modified `app/analyzer/motion.py`

Replaced the function body verbatim from the brief:
- Added `progress_callback=None` parameter.
- Added `total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)` to know total frames.
- Added `last_reported = -1.0` to track last fraction reported.
- Every 30 frames, if callback is set and `total > 0`, computes `frac = min(1.0, idx / total)` and calls the callback if `frac > last_reported` (strictly non-decreasing).
- After the loop, calls `progress_callback(1.0)` if it wasn't already reported.

### Step 4 — Modified `app/analyzer/pipeline.py`

Changed `analyze` signature to accept `progress_callback=None`. Implementation verbatim from the brief:
- Wraps the callback as `motion_cb = lambda f: progress_callback(min(0.9, f * 0.9))` to scale motion phase to [0, 0.9].
- Passes `motion_cb` to `motion_energy`.
- After `resegment`, calls `progress_callback(1.0)` to signal completion.
- `_resample` and `resegment` left completely untouched.

### Step 5 — Confirmed PASS (3/3 new tests)

```
tests/test_progress.py::test_motion_reports_monotonic_progress PASSED
tests/test_progress.py::test_motion_without_callback_unchanged PASSED
tests/test_progress.py::test_analyze_reports_progress_ending_at_one PASSED
3 passed in 0.54s
```

### Step 6 — Full Suite Green (32/32)

```
============================= test session starts ==============================
platform darwin -- Python 3.10.8, pytest-9.1.0, pluggy-1.6.0
...
tests/test_api.py::test_full_flow PASSED
tests/test_api.py::test_upload_rejects_non_video PASSED
tests/test_api.py::test_params_ignores_unknown_keys PASSED
tests/test_audio.py::test_extract_wav_creates_file PASSED
tests/test_audio.py::test_audio_energy_higher_during_sine PASSED
tests/test_deps.py::test_ffmpeg_available_returns_bool PASSED
tests/test_deps.py::test_probe_duration_reads_length PASSED
tests/test_deps.py::test_probe_duration_rejects_non_video PASSED
tests/test_exporter.py::test_cut_clip_has_expected_duration PASSED
tests/test_exporter.py::test_export_produces_clips_and_stitch PASSED
tests/test_exporter.py::test_export_empty_ranges PASSED
tests/test_jobs.py::test_create_returns_running_job PASSED
tests/test_jobs.py::test_update_sets_fields PASSED
tests/test_jobs.py::test_get_returns_copy_not_reference PASSED
tests/test_jobs.py::test_update_unknown_job_is_noop PASSED
tests/test_jobs.py::test_concurrent_updates_are_safe PASSED
tests/test_motion.py::test_motion_energy_higher_during_movement PASSED
tests/test_pipeline.py::test_save_and_load_signals_roundtrip PASSED
tests/test_pipeline.py::test_analyze_detects_middle_rally PASSED
tests/test_pipeline.py::test_resegment_uses_cache PASSED
tests/test_progress.py::test_motion_reports_monotonic_progress PASSED
tests/test_progress.py::test_motion_without_callback_unchanged PASSED
tests/test_progress.py::test_analyze_reports_progress_ending_at_one PASSED
tests/test_segment.py::test_normalize_constant_is_zeros PASSED
tests/test_segment.py::test_normalize_scales_to_unit PASSED
tests/test_segment.py::test_combine_takes_max PASSED
tests/test_segment.py::test_segment_finds_single_active_span PASSED
tests/test_segment.py::test_segment_merges_short_gap PASSED
tests/test_segment.py::test_segment_drops_short_span PASSED
tests/test_segment.py::test_segment_applies_padding_and_clamps PASSED
tests/test_segment.py::test_segment_empty_when_all_quiet PASSED
tests/test_combine_and_segment_handle_empty PASSED

======================== 32 passed, 3 warnings in 2.66s ========================
```

---

## Deviations

None. All code applied verbatim from the brief. No new dependencies introduced.

## Concerns

None. The `lambda` closure in `pipeline.py` for `motion_cb` captures `progress_callback` by reference at call time, which is correct and safe for single-threaded use. Thread-safety considerations (if the callback is called from a background thread in a future task) are left to the caller as the brief implies.
