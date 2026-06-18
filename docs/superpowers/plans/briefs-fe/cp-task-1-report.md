# Cancel+Play Task 1 — Implementation Report

## Summary

All 5 new tests pass alongside all 35 existing tests (40 total, 0 failures).

---

## Changes per file

### `app/api/jobs.py`
- Added `"cancelled": False` to the record dict in `create()`.
- Added `cancel(job_id: str) -> None` function that acquires `_LOCK`, sets `rec["cancelled"] = True` and `rec["status"] = "cancelled"`, no-ops if job_id is unknown.

### `app/api/routes.py`
- Added module-level `class _Cancelled(Exception): pass` immediately after the `router = APIRouter(...)` line.
- In the `detect` endpoint's `run()` closure: replaced the inline lambda with a named `_cb(f)` function that checks `rec["cancelled"]` before calling `jobs.update`, raises `_Cancelled` if cancelled. Added `except _Cancelled: jobs.update(job_id, status="cancelled")` before the broad `except Exception` block.
- In the `export` endpoint's `run()` closure: same pattern — named `_cb`, `except _Cancelled` before `except Exception`.
- Added new endpoint `POST /api/jobs/{job_id}/cancel` that returns 404 for unknown jobs, calls `jobs.cancel(job_id)`, and returns the updated record.

### `app/analyzer/motion.py`
- Wrapped the `while True:` frame loop in `try:` / `finally: cap.release()`. The post-loop `progress_callback(1.0)` call and the `return` remain outside the try/finally block, so they still execute only on a clean (non-exception) exit from the loop. If a callback raises mid-loop (e.g., `_Cancelled`), `cap.release()` is guaranteed to run before the exception propagates.

### `tests/test_jobs.py`
- Appended 3 tests: `test_create_has_cancelled_false`, `test_cancel_sets_cancelled_true`, `test_cancel_unknown_is_noop`.

### `tests/test_api.py`
- Appended 2 tests: `test_cancel_unknown_job_404`, `test_cancel_sets_status`.

---

## Pytest output

```
============================= test session starts ==============================
platform darwin -- Python 3.10.8, pytest-9.1.0, pluggy-1.6.0
collected 40 items

tests/test_api.py::test_full_flow_jobs PASSED
tests/test_api.py::test_unknown_job_404 PASSED
tests/test_api.py::test_upload_rejects_non_video PASSED
tests/test_api.py::test_params_ignores_unknown_keys PASSED
tests/test_api.py::test_cancel_unknown_job_404 PASSED
tests/test_api.py::test_cancel_sets_status PASSED
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
tests/test_jobs.py::test_create_has_cancelled_false PASSED
tests/test_jobs.py::test_cancel_sets_cancelled_true PASSED
tests/test_jobs.py::test_cancel_unknown_is_noop PASSED
tests/test_motion.py::test_motion_energy_higher_during_movement PASSED
tests/test_pipeline.py::test_save_and_load_signals_roundtrip PASSED
tests/test_pipeline.py::test_analyze_detects_middle_rally PASSED
tests/test_pipeline.py::test_resegment_uses_cache PASSED
tests/test_progress.py::test_motion_reports_monotonic_progress PASSED
tests/test_progress.py::test_motion_without_callback_unchanged PASSED
tests/test_progress.py::test_analyze_reports_progress_ending_at_one PASSED
tests/test_progress.py::test_export_reports_progress PASSED
tests/test_progress.py::test_export_empty_ranges_no_progress_crash PASSED
tests/test_segment.py::test_normalize_constant_is_zeros PASSED
tests/test_segment.py::test_normalize_scales_to_unit PASSED
tests/test_segment.py::test_combine_takes_max PASSED
tests/test_segment.py::test_segment_finds_single_active_span PASSED
tests/test_segment.py::test_segment_merges_short_gap PASSED
tests/test_segment.py::test_segment_drops_short_span PASSED
tests/test_segment.py::test_segment_applies_padding_and_clamps PASSED
tests/test_segment.py::test_segment_empty_when_all_quiet PASSED
tests/test_segment.py::test_combine_and_segment_handle_empty PASSED

======================== 40 passed, 3 warnings in 3.69s ========================
```

Warnings are pre-existing deprecations (`on_event` in FastAPI, `httpx` starlette testclient) — not introduced by this task.

---

## Concerns

None. The `test_cancel_sets_status` test cancels a job immediately after dispatch and checks only the endpoint's own synchronous response (i.e., the record as set by `jobs.cancel()`), so the test does not rely on thread timing. The thread may or may not have started by the time cancel is called, but the status field is set by `jobs.cancel()` unconditionally and returned by the endpoint — this is reliable.

The `progress_callback(1.0)` call in `motion.py` after the try/finally block will not execute if `_Cancelled` is raised mid-loop (the exception propagates past it), which is the correct behavior — no final progress ping should fire after a cancellation.
