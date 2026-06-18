# Task 6: Onset Gating — Report

## Files Changed

- `app/analyzer/segment.py` — appended `gate_by_onsets(segments, onsets, params)` function
- `tests/test_segment.py` — added `gate_by_onsets` to the existing mid-file import (line 99); appended `test_gating_drops_low_onset_segments` and `test_gating_disabled_when_zero`

## Pytest Commands and Output

### Step 2: Failing test (before implementation)

```
.venv/bin/python -m pytest tests/test_segment.py -k gating -v
```

Result: `ImportError: cannot import name 'gate_by_onsets' from 'app.analyzer.segment'` — collected 0 items / 1 error. Confirmed failure.

### Step 4: Gating tests after implementation

```
.venv/bin/python -m pytest tests/test_segment.py -k gating -v
```

Result:
```
tests/test_segment.py::test_gating_drops_low_onset_segments PASSED
tests/test_segment.py::test_gating_disabled_when_zero PASSED
2 passed, 15 deselected in 0.01s
```

### Checkpoint: Full test_segment.py

```
.venv/bin/python -m pytest tests/test_segment.py -v
```

Result: `17 passed in 0.02s` — all 17 tests green.

### Full Suite

```
.venv/bin/python -m pytest -q
```

Result: `6 failed, 78 passed, 3 warnings in 7.17s`

## Failure List

All 6 failures are pre-existing, caused by `pipeline.py` unpacking `load_signals` as a 3-tuple (fixed in Task 8):

- `tests/test_pipeline.py::test_save_and_load_signals_roundtrip` — ValueError: too many values to unpack (expected 3)
- `tests/test_pipeline.py::test_analyze_detects_middle_rally` — same
- `tests/test_pipeline.py::test_resegment_uses_cache` — same
- `tests/test_progress.py::test_analyze_reports_progress_ending_at_one` — same
- `tests/test_library.py::test_open_rehydrates_state` — Detection job failed: too many values to unpack
- `tests/test_api.py::test_full_flow_jobs` — cascades from above

Zero new failures in `tests/test_segment.py` or any other unit test file.

## Self-Review

- `gate_by_onsets` correctly returns the full `segments` list unchanged when `min_onsets_per_rally <= 0` (disabled path).
- Onset counting uses `>=` on both bounds (`onsets >= s["start"]) & (onsets <= s["end"]`)` — inclusive, matching the plan verbatim.
- `np.asarray(onsets, dtype=float)` guards against any array-like input type.
- Import added to the existing mid-file import line (line 99) rather than adding yet another mid-file import, keeping consistent with the style note.
- No modifications to `pipeline.py` as required.
- No other files touched.

## Concerns

None. Implementation is a direct translation of the plan spec. The pre-existing pipeline failures are expected and scoped to Task 8.
