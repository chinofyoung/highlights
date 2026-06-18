# Task 2 Report: Onset Detection Module

## Files Changed

- **Created:** `app/analyzer/onsets.py`
- **Created:** `tests/test_onsets.py`

## Pytest Commands and Output

### Step 2: Verify failing test

```
.venv/bin/python -m pytest tests/test_onsets.py -v
```

```
collected 0 items / 1 error

ERROR tests/test_onsets.py
ImportError while importing test module ...
tests/test_onsets.py:4: in <module>
    from app.analyzer.onsets import detect_onsets
E   ModuleNotFoundError: No module named 'app.analyzer.onsets'
Interrupted: 1 error during collection
```

Expected failure confirmed.

### Step 4: Verify passing tests

```
.venv/bin/python -m pytest tests/test_onsets.py -v
```

```
collected 3 items

tests/test_onsets.py::test_detects_clicks_at_expected_times PASSED       [ 33%]
tests/test_onsets.py::test_silence_yields_no_onsets PASSED               [ 66%]
tests/test_onsets.py::test_empty_audio_returns_empty PASSED              [100%]

3 passed in 0.53s
```

### Step 5: Checkpoint (full suite)

```
.venv/bin/python -m pytest -q
```

```
74 passed, 3 warnings in 7.39s
```

Baseline was 71 passed. 3 new tests added, 0 regressions.

## Self-Review Notes

- Implementation matches the spec verbatim (no deviations).
- `_bandpass` uses numpy FFT — O(n log n), fine for audio buffers up to several minutes.
- `_pick_peaks` iterates linearly through the envelope; for typical 16kHz audio over a few minutes this is fast (a few hundred thousand iterations at most).
- The `mad < 1e-9` guard correctly short-circuits on silence (floor == MAD == 0).
- `np.frombuffer` returns a read-only buffer; `.astype(np.float64)` copies it so downstream mutation is safe.
- `wave` module opens and reads the whole file in one pass; for large files (>10min) this could be a memory concern, but that is consistent with the rest of the codebase.
- The `_click` helper in tests uses `freq=3000` which is well within `onset_low_hz=1500` to `onset_high_hz=8000`, so bandpass passes it cleanly.

## Concerns

None. The synthetic-signal test (`test_detects_clicks_at_expected_times`) passed deterministically on first run with clicks at 0.5s, 1.5s, 2.5s detected within ±0.05s. The 1-second separation between clicks far exceeds `onset_min_separation_s=0.20`, so no tolerance tightness concerns.
