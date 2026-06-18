# Task 3 Report: Audio Energy Extraction

## Files Created

- `app/analyzer/audio.py` — implements `extract_wav` and `audio_energy`
- `tests/test_audio.py` — two tests: WAV file creation and energy contrast

## TDD Steps

1. Wrote `tests/test_audio.py` verbatim from brief.
2. Ran `pytest tests/test_audio.py -v` → **FAIL** (ImportError: cannot import name 'audio').
3. Wrote `app/analyzer/audio.py` verbatim from brief.
4. Ran `pytest tests/test_audio.py -v` → **PASS** (2/2).
5. Ran `pytest -v` (full suite) → **PASS** (13/13).

## Final `pytest -v` Output

```
============================= test session starts ==============================
platform darwin -- Python 3.10.8, pytest-9.1.0, pluggy-1.6.0
rootdir: /Users/chinoyoung/Code/highlights
configfile: pyproject.toml

tests/test_audio.py::test_extract_wav_creates_file PASSED                [  7%]
tests/test_audio.py::test_audio_energy_higher_during_sine PASSED         [ 15%]
tests/test_deps.py::test_ffmpeg_available_returns_bool PASSED            [ 23%]
tests/test_deps.py::test_probe_duration_reads_length PASSED              [ 30%]
tests/test_deps.py::test_probe_duration_rejects_non_video PASSED         [ 38%]
tests/test_segment.py::test_normalize_constant_is_zeros PASSED           [ 46%]
tests/test_segment.py::test_normalize_scales_to_unit PASSED              [ 53%]
tests/test_segment.py::test_combine_takes_max PASSED                     [ 61%]
tests/test_segment.py::test_segment_finds_single_active_span PASSED      [ 69%]
tests/test_segment.py::test_segment_merges_short_gap PASSED              [ 76%]
tests/test_segment.py::test_segment_drops_short_span PASSED              [ 84%]
tests/test_segment.py::test_segment_applies_padding_and_clamps PASSED    [ 92%]
tests/test_segment.py::test_segment_empty_when_all_quiet PASSED          [100%]

============================== 13 passed in 0.52s ==============================
```

## Deviations

None. Code is verbatim from the brief.

## Concerns

None. Both ffmpeg-dependent tests ran (not skipped) because ffmpeg is installed, confirming the integration path works correctly. The `sample_video` fixture produces a 6s video with a 1kHz sine burst in seconds 2–4, and the energy contrast assertion (`middle > edges`) passes cleanly.
