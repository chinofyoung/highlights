# Task 2 Report: Segmentation (pure core)

## Files Created

- `app/analyzer/__init__.py` — empty package init
- `app/analyzer/segment.py` — implements `normalize`, `combine`, `smooth`, `segment`
- `tests/test_segment.py` — 8 tests per brief spec

## Final `pytest -v` Output

```
============================= test session starts ==============================
platform darwin -- Python 3.10.8, pytest-9.1.0, pluggy-1.6.0 -- /Users/chinoyoung/Code/highlights/.venv/bin/python3.10
cachedir: .pytest_cache
rootdir: /Users/chinoyoung/Code/highlights
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.14.0
collecting ... collected 11 items

tests/test_deps.py::test_ffmpeg_available_returns_bool PASSED            [  9%]
tests/test_deps.py::test_probe_duration_reads_length PASSED              [ 18%]
tests/test_deps.py::test_probe_duration_rejects_non_video PASSED         [ 27%]
tests/test_segment.py::test_normalize_constant_is_zeros PASSED           [ 36%]
tests/test_segment.py::test_normalize_scales_to_unit PASSED              [ 45%]
tests/test_segment.py::test_combine_takes_max PASSED                     [ 54%]
tests/test_segment.py::test_segment_finds_single_active_span PASSED      [ 63%]
tests/test_segment.py::test_segment_merges_short_gap PASSED              [ 72%]
tests/test_segment.py::test_segment_drops_short_span PASSED              [ 81%]
tests/test_segment.py::test_segment_applies_padding_and_clamps PASSED    [ 90%]
tests/test_segment.py::test_segment_empty_when_all_quiet PASSED          [100%]

============================== 11 passed in 0.23s ==============================
```

## Deviations

None. Brief followed verbatim — exact code, exact test cases.

## Concerns

None.
