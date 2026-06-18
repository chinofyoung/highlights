# Task 1 Report: Detection Params

## Files Changed

- `app/config.py` — added 14 new fields to `DetectionParams` (onset, serve derivation, combine, adaptive threshold, onset gating groups)
- `tests/test_config.py` — created (2 tests: `test_new_defaults_present`, `test_existing_defaults_unchanged`)

## TDD Steps Executed

### Step 1: Wrote failing test
Created `tests/test_config.py` with both test functions exactly as specified in the plan.

### Step 2: Verified test fails
```
$ .venv/bin/python -m pytest tests/test_config.py -v
FAILED tests/test_config.py::test_new_defaults_present - AttributeError: 'DetectionParams' object has no attribute 'onset_low_hz'
PASSED tests/test_config.py::test_existing_defaults_unchanged
1 failed, 1 passed
```

### Step 3: Added fields to app/config.py
Rewrote `app/config.py` with all 14 new fields in the exact order and with the exact default values specified in the plan.

### Step 4: Verified tests pass
```
$ .venv/bin/python -m pytest tests/test_config.py -v
PASSED tests/test_config.py::test_new_defaults_present
PASSED tests/test_config.py::test_existing_defaults_unchanged
2 passed in 0.01s
```

### Step 5: Checkpoint — full suite
```
$ .venv/bin/python -m pytest -q
.......................................................................  [100%]
71 passed, 3 warnings in 7.38s
```

## Self-Review Notes

- All 14 new fields match the plan's specified names and default values exactly (verbatim).
- Existing 5 fields (`sample_fps`, `threshold`, `merge_gap_seconds`, `min_rally_seconds`, `pad_seconds`) are unchanged.
- The dataclass is purely additive — no existing callers are broken.
- The plan notes that `_params()` in `app/api/routes.py` auto-allows the new fields via `dataclasses.fields(DetectionParams)`, so no API-layer change is needed.
- 71 passed = 69 original baseline + 2 new tests. No regressions.

## Concerns

None. Task is clean and self-contained.
