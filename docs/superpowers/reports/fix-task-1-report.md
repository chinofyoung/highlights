# Fix Task 1 Report: Restore Simple Detector as Default

## Files Changed

- `app/config.py` — added `combine_mode: str = "max"`; flipped `require_both=False`, `adaptive_threshold=False`, `min_onsets_per_rally=0`; updated inline comments.
- `app/analyzer/segment.py` — added max branch to `combine()`: returns `np.maximum(normalize(motion), normalize(audio))` when `combine_mode == "max"`, else existing weighted+AND-gate path.
- `tests/test_segment.py` — added 2 new tests (`test_combine_max_mode_is_default`, `test_combine_weighted_mode_still_available`); added `combine_mode="weighted"` to 4 existing weighted-path tests (`test_combine_and_gate_suppresses_single_channel`, `test_combine_passes_when_both_active`, `test_combine_weighted_average`, `test_combine_require_both_false_is_max_like`); added `adaptive_threshold=True` to `test_adaptive_threshold_flat_signal_yields_no_rally` (opt-in, same logic as the weighted tests).
- `tests/test_config.py` — added `test_default_detector_is_simple`; updated `test_new_defaults_present` to reflect flipped defaults (`require_both=False`, `adaptive_threshold=False`, `min_onsets_per_rally=0`).

## Pytest Commands and Full Output

### Step 2: Verify new tests fail before implementation

```
.venv/bin/python -m pytest tests/test_config.py::test_default_detector_is_simple tests/test_segment.py -k "max_mode or weighted_mode_still" -v
```

Output:
```
FAILED tests/test_segment.py::test_combine_max_mode_is_default - assert np.float64(0.0) == 1.0
FAILED tests/test_segment.py::test_combine_weighted_mode_still_available - TypeError: DetectionParams.__init__() got an unexpected keyword argument 'combine_mode'
FAILED tests/test_config.py::test_default_detector_is_simple - AttributeError: 'DetectionParams' object has no attribute 'combine_mode'
```

All 3 failed as expected.

### Step 6: Verify segment + config tests after implementation

```
.venv/bin/python -m pytest tests/test_segment.py tests/test_config.py -v
```

Output: 24 passed in 0.04s.

### Step 7: Full suite checkpoint

```
.venv/bin/python -m pytest -q
```

Output:
```
103 passed, 3 warnings in 8.51s
```

## Failing Tests

**None.** The full suite is 103 passed, 0 failed.

The plan warned that `tests/test_pipeline.py` tests might fail due to the default detector change. In practice, the pipeline tests continued to pass. This is consistent: the pipeline tests that exercise `analyze()` use `sample_fps` and signal parameters tuned to a synthetic video fixture, and those signals still produce detectable rallies under max-combine + fixed threshold 0.5.

## Self-Review

- `combine_mode: str = "max"` added at the top of the combine block in config — correct position, matches plan verbatim.
- `getattr(params, "combine_mode", "max")` defensive read in `combine()` means any caller that passes a params object missing the field (e.g., old pickled params) defaults safely to max. This matches the plan exactly.
- Four weighted-path tests updated with `combine_mode="weighted"` — assertions unchanged, they continue to exercise the weighted code path.
- `test_adaptive_threshold_flat_signal_yields_no_rally` was NOT in the plan's Step 5 list, but it implicitly relied on `adaptive_threshold=True` being the default. Fixed with the same pattern: opt-in via `adaptive_threshold=True` in params. Assertion unchanged.
- `test_new_defaults_present` reflected old "new defaults" (require_both=True, adaptive_threshold=True, min_onsets_per_rally=2). Updated to match the new defaults — this is the correct reconciliation.

## Concerns

- The `test_adaptive_threshold_flat_signal_yields_no_rally` fix was not explicitly called out in the plan's Step 5 (which only named 4 weighted-combine tests). However, the fix is identical in character — it opts in to a non-default feature path — and is required for the test suite to be green. No concern about correctness.
- Pipeline tests passed without any changes, which is good. Task 2 may still need to reconcile serve-assertion tests if/when serve logic changes, but that is out of scope here.
