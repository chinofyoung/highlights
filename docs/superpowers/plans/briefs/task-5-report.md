# Task 5 Report: Workdir, Signal Caching, and the Analysis Pipeline

## Files Created

- `app/workdir.py` — module-level `WORKDIR` constant, `video_dir()`, `save_signals()`, `load_signals()`
- `app/analyzer/pipeline.py` — `_resample()`, `analyze()`, `resegment()`
- `tests/test_pipeline.py` — 3 tests as specified verbatim in the brief

## TDD Steps

1. Wrote `tests/test_pipeline.py` verbatim from brief.
2. Ran `pytest tests/test_pipeline.py -v` → **FAIL** (ImportError: `app.workdir` not found).
3. Implemented `app/workdir.py` verbatim from brief.
4. Implemented `app/analyzer/pipeline.py` verbatim from brief.
5. Ran `pytest tests/test_pipeline.py -v` → **3 PASSED**.
6. Ran `pytest -v` (full suite) → **17 PASSED**.

## Final `pytest -v` Output

```
============================= test session starts ==============================
platform darwin -- Python 3.10.8, pytest-9.1.0, pluggy-1.6.0
rootdir: /Users/chinoyoung/Code/highlights
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.14.0
collected 17 items

tests/test_audio.py::test_extract_wav_creates_file PASSED                [  5%]
tests/test_audio.py::test_audio_energy_higher_during_sine PASSED         [ 11%]
tests/test_deps.py::test_ffmpeg_available_returns_bool PASSED            [ 17%]
tests/test_deps.py::test_probe_duration_reads_length PASSED              [ 23%]
tests/test_deps.py::test_probe_duration_rejects_non_video PASSED         [ 29%]
tests/test_motion.py::test_motion_energy_higher_during_movement PASSED   [ 35%]
tests/test_pipeline.py::test_save_and_load_signals_roundtrip PASSED      [ 41%]
tests/test_pipeline.py::test_analyze_detects_middle_rally PASSED         [ 47%]
tests/test_pipeline.py::test_resegment_uses_cache PASSED                 [ 52%]
tests/test_segment.py::test_normalize_constant_is_zeros PASSED           [ 58%]
tests/test_segment.py::test_normalize_scales_to_unit PASSED              [ 64%]
tests/test_segment.py::test_combine_takes_max PASSED                     [ 70%]
tests/test_segment.py::test_segment_finds_single_active_span PASSED      [ 76%]
tests/test_segment.py::test_segment_merges_short_gap PASSED              [ 82%]
tests/test_segment.py::test_segment_drops_short_span PASSED              [ 88%]
tests/test_segment.py::test_segment_applies_padding_and_clamps PASSED    [ 94%]
tests/test_segment.py::test_segment_empty_when_all_quiet PASSED          [100%]

============================== 17 passed in 1.07s ==============================
```

## Deviations

None. All code implemented verbatim from the brief.

## Concerns

None. The `monkeypatch.setattr(workdir, "WORKDIR", tmp_path)` pattern works correctly because `WORKDIR` is a module-level attribute and `video_dir()` reads it at call time (not at import time).
