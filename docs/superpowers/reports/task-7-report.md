# Task 7 Report: Serve Derivation

## Files Changed

- **Created:** `app/analyzer/serve.py`
- **Created:** `tests/test_serve.py`

No other files modified.

---

## Pytest Commands and Output

### Step 2: Confirm failing test

```
.venv/bin/python -m pytest tests/test_serve.py -v
```

```
ERROR collecting tests/test_serve.py
  ImportError: No module named 'app.analyzer.serve'
```

Exit code: 2 (collection error — confirmed failing as expected).

---

### Step 4: Confirm passing test (after implementation)

```
.venv/bin/python -m pytest tests/test_serve.py -v
```

```
tests/test_serve.py::test_two_onsets_use_second_hit PASSED               [ 25%]
tests/test_serve.py::test_one_onset_uses_first_hit PASSED                [ 50%]
tests/test_serve.py::test_no_onsets_falls_back_to_fixed PASSED           [ 75%]
tests/test_serve.py::test_serve_end_clamped_to_segment_end PASSED        [100%]

4 passed in 0.01s
```

---

### Step 5: Checkpoint — full suite

```
.venv/bin/python -m pytest -q
```

```
6 failed, 82 passed, 3 warnings in 7.17s
```

---

## Failure List

All 6 failures are pre-existing and documented as expected in the task instructions. They all stem from `pipeline.py` still unpacking `load_signals()` as a 3-tuple while Task 3 already updated it to return a 4-tuple. These will be fixed in Task 8.

| Test | Root cause |
|------|-----------|
| `tests/test_pipeline.py::test_save_and_load_signals_roundtrip` | `load_signals` returns 4-tuple; test still unpacks 3 |
| `tests/test_pipeline.py::test_analyze_detects_middle_rally` | `pipeline.py:41` unpacks 3-tuple |
| `tests/test_pipeline.py::test_resegment_uses_cache` | `pipeline.py:41` unpacks 3-tuple |
| `tests/test_progress.py::test_analyze_reports_progress_ending_at_one` | `pipeline.py:41` unpacks 3-tuple |
| `tests/test_library.py::test_open_rehydrates_state` | Detection job fails due to same pipeline unpack error |
| `tests/test_api.py::test_full_flow_jobs` | Detection job fails due to same pipeline unpack error |

No new failures were introduced by Task 7.

---

## Self-Review

**Correctness:**
- `derive_serve` correctly handles all three onset cases (>=2, ==1, ==0).
- `serve_end` is clamped to `segment["end"]` in all paths.
- The returned dict is a shallow copy via `{**segment, ...}` so the original segment dict is not mutated.
- Onsets are filtered to `onsets >= start` (inside the segment, from the start forward) and sorted before indexing, matching the spec's intent of using the first two paddle hits.
- `serve_start` is always set to `segment["start"]` as specified.

**Edge cases covered by tests:**
- Two or more onsets: uses second hit + pad
- Exactly one onset: uses that hit + pad
- No onsets: falls back to `serve_fallback_seconds`
- Clamp: `serve_fallback_seconds=999.0` clamps to segment end

**Security:** No external input — all data is internal numpy arrays and dicts.

**Performance:** O(n log n) for sort on onset array; entirely acceptable for rally-scale data (typically <50 onsets per video).

---

## Concerns

None. Implementation exactly matches the plan spec verbatim. All 4 task-7 tests pass; the 6 pre-existing failures are confined to pipeline/api/library/progress tests and are expected to be resolved in Task 8.
