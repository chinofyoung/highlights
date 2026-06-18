# Task 3 Report: Persist onsets in cached signals

## Files Changed

- **Created:** `tests/test_workdir.py`
- **Modified:** `app/workdir.py` — `save_signals` and `load_signals`

## Changes Made

### `app/workdir.py`

`save_signals` gains an optional `onsets: np.ndarray | None = None` parameter (defaults to empty array). `load_signals` now returns a 4-tuple `(motion, audio, hop, onsets)`, loading `onsets` from the npz if present, else returning `np.zeros(0)` for backward compat with old cache files.

## Pytest Commands + Full Output

### Step 2: Verify failing tests

Command: `.venv/bin/python -m pytest tests/test_workdir.py -v`

```
FAILED tests/test_workdir.py::test_roundtrip_with_onsets - TypeError: save_signals() takes 4 positional arguments but 5 were given
FAILED tests/test_workdir.py::test_roundtrip_without_onsets - ValueError: not enough values to unpack (expected 4, got 3)
2 failed in 0.05s
```

### Step 4: Verify passing tests

Command: `.venv/bin/python -m pytest tests/test_workdir.py -v`

```
tests/test_workdir.py::test_roundtrip_with_onsets PASSED
tests/test_workdir.py::test_roundtrip_without_onsets PASSED
2 passed in 0.01s
```

### Step 5: Full suite checkpoint

Command: `.venv/bin/python -m pytest -q`

```
6 failed, 70 passed, 3 warnings in 7.21s
```

## Failing Tests (Post-Task-3)

All 6 failures are caused by `app/analyzer/pipeline.py:41` still unpacking `load_signals()` as a 3-tuple — exactly as predicted in the plan. None are caused by this task's changes.

| Test | File | Error | Cause |
|------|------|-------|-------|
| `test_full_flow_jobs` | `tests/test_api.py` | `'error' == 'done'` (job error: "too many values to unpack (expected 3)") | pipeline.py 3-tuple unpack |
| `test_open_rehydrates_state` | `tests/test_library.py` | `Detection job failed: too many values to unpack (expected 3)` | pipeline.py 3-tuple unpack |
| `test_save_and_load_signals_roundtrip` | `tests/test_pipeline.py` | `ValueError: too many values to unpack (expected 3)` | pre-existing pipeline test also unpacking 3-tuple |
| `test_analyze_detects_middle_rally` | `tests/test_pipeline.py` | `ValueError: too many values to unpack (expected 3)` at `pipeline.py:41` | pipeline.py 3-tuple unpack |
| `test_resegment_uses_cache` | `tests/test_pipeline.py` | `ValueError: too many values to unpack (expected 3)` at `pipeline.py:41` | pipeline.py 3-tuple unpack |
| `test_analyze_reports_progress_ending_at_one` | `tests/test_progress.py` | `ValueError: too many values to unpack (expected 3)` at `pipeline.py:41` | pipeline.py 3-tuple unpack |

## Self-Review

- `save_signals` uses `np.asarray(onsets, dtype=float)` to ensure the stored array is always float64, consistent with what `detect_onsets` returns.
- `load_signals` checks `data.files` (not `data.keys()`) to correctly detect the presence of the `onsets` key in the npz archive.
- Backward compat with old npz files (no `onsets` key) is handled: returns `np.zeros(0)`.
- The `|` union type syntax (`np.ndarray | None`) requires Python 3.10+; the project already targets 3.10+ per the plan.
- Both test cases (with and without onsets) pass cleanly.

## Concerns

None. All failures are the expected pipeline.py 3-tuple issue, to be resolved in Task 8.
