# Task 6 Report: Export (cut + stitch)

## Files Created

- `app/exporter/__init__.py` — empty package marker
- `app/exporter/ffmpeg.py` — implements `cut_clip`, `concat_clips`, `export`
- `tests/test_exporter.py` — 3 tests per brief spec

## TDD Flow

1. Wrote `tests/test_exporter.py` verbatim from brief.
2. Ran `pytest tests/test_exporter.py -v` — confirmed FAIL (ImportError: No module named 'app.exporter').
3. Created `app/exporter/__init__.py` (empty) and `app/exporter/ffmpeg.py` with exact code from brief.
4. Ran `pytest tests/test_exporter.py -v` — 3 passed in 0.69s.
5. Ran `pytest -v` (full suite) — 20 passed in 1.78s.

## Final `pytest -v` Output

```
============================= test session starts ==============================
platform darwin -- Python 3.10.8, pytest-9.1.0, pluggy-1.6.0 -- /Users/chinoyoung/Code/highlights/.venv/bin/python3.10
cachedir: .pytest_cache
rootdir: /Users/chinoyoung/Code/highlights
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.9.0
collecting ... collected 20 items

tests/test_audio.py::test_extract_wav_creates_file PASSED                [  5%]
tests/test_audio.py::test_audio_energy_higher_during_sine PASSED         [ 10%]
tests/test_deps.py::test_ffmpeg_available_returns_bool PASSED            [ 15%]
tests/test_deps.py::test_probe_duration_reads_length PASSED              [ 20%]
tests/test_deps.py::test_probe_duration_rejects_non_video PASSED         [ 25%]
tests/test_exporter.py::test_cut_clip_has_expected_duration PASSED       [ 30%]
tests/test_exporter.py::test_export_produces_clips_and_stitch PASSED     [ 35%]
tests/test_exporter.py::test_export_empty_ranges PASSED                  [ 40%]
tests/test_motion.py::test_motion_energy_higher_during_movement PASSED   [ 45%]
tests/test_pipeline.py::test_save_and_load_signals_roundtrip PASSED      [ 50%]
tests/test_pipeline.py::test_analyze_detects_middle_rally PASSED         [ 55%]
tests/test_pipeline.py::test_resegment_uses_cache PASSED                 [ 60%]
tests/test_segment.py::test_normalize_constant_is_zeros PASSED           [ 65%]
tests/test_segment.py::test_normalize_scales_to_unit PASSED              [ 70%]
tests/test_segment.py::test_combine_takes_max PASSED                     [ 75%]
tests/test_segment.py::test_segment_finds_single_active_span PASSED      [ 80%]
tests/test_segment.py::test_segment_merges_short_gap PASSED              [ 85%]
tests/test_segment.py::test_segment_drops_short_span PASSED              [ 90%]
tests/test_segment.py::test_segment_applies_padding_and_clamps PASSED    [ 95%]
tests/test_segment.py::test_segment_empty_when_all_quiet PASSED          [100%]

============================== 20 passed in 1.78s ==============================
```

## Deviations

None. Code matches brief verbatim. Tests match brief verbatim.

## Concerns

None. All tests pass including ffmpeg-dependent ones (actual re-encode ran successfully). The full suite remains green with no regressions.
