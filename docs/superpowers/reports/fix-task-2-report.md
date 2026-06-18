# Fix Task 2 Report: Fixed-length serve clips

## Files Changed

- `app/config.py` — added `serve_length_seconds: float = 6.0` under serve derivation; marked `serve_pad_seconds` and `serve_fallback_seconds` as opt-in remnants
- `app/analyzer/serve.py` — rewrote `derive_serve(segment, params)` (dropped `onsets` arg); now returns `serve_start=start`, `serve_end=min(start+serve_length_seconds, end)`, `serve_resolved=True`
- `app/analyzer/pipeline.py` — updated `resegment()` to call `serve_mod.derive_serve(r, params)` (dropped onsets arg); onset computation/caching in `analyze()` retained unchanged
- `tests/test_serve.py` — replaced onset-based tests with 3 fixed-length tests per plan Step 2
- `tests/test_pipeline.py` — replaced `test_pipeline_caches_onsets_and_derives_serves` body per plan Step 6

## Pytest Commands and Final Output

### Step 2 — serve tests after rewrite (verify pass)
```
.venv/bin/python -m pytest tests/test_serve.py -v
```
```
tests/test_serve.py::test_serve_is_fixed_length_from_start PASSED
tests/test_serve.py::test_serve_clamped_to_short_rally PASSED
tests/test_serve.py::test_serve_length_is_configurable PASSED
3 passed in 0.01s
```

### Step 7 — serve + pipeline tests
```
.venv/bin/python -m pytest tests/test_serve.py tests/test_pipeline.py -v
```
```
tests/test_serve.py::test_serve_is_fixed_length_from_start PASSED
tests/test_serve.py::test_serve_clamped_to_short_rally PASSED
tests/test_serve.py::test_serve_length_is_configurable PASSED
tests/test_pipeline.py::test_save_and_load_signals_roundtrip PASSED
tests/test_pipeline.py::test_analyze_detects_middle_rally PASSED
tests/test_pipeline.py::test_resegment_uses_cache PASSED
tests/test_pipeline.py::test_pipeline_caches_onsets_and_derives_serves PASSED
7 passed in 0.81s
```

### Step 8 — full suite checkpoint
```
.venv/bin/python -m pytest -q
```
```
101 passed, 3 warnings in 8.12s
```

## Pipeline-Test Reconciliations

`test_analyze_detects_middle_rally` and `test_resegment_uses_cache` required **no changes** — both already used `require_both=False, min_onsets_per_rally=0` which remains valid under the new defaults. Their core assertions (middle-rally overlap and loose>=strict total duration) are unchanged and passed without modification.

`test_pipeline_caches_onsets_and_derives_serves` was replaced per the plan. The old test used `min_onsets_per_rally=1` and asserted `serve_resolved` from onset data. The new test uses `serve_length_seconds=2.0` and asserts fixed-length serve arithmetic. The `onsets.size >= 0` assertion (vs old `>= 1`) is correct: the plan specifies onset caching is retained but no longer needs to be non-empty for serves to resolve.

## Self-Review

- `serve_length_seconds` default is 6.0 as specified; clamping to `segment["end"]` handles short rallies correctly.
- `serve_resolved` is always `True` in the new implementation (every serve resolves by definition of fixed-length). This is correct per spec — there is no fallback path anymore.
- Onset computation/caching in `analyze()` is fully retained; `gate_by_onsets` still runs as a no-op when `min_onsets_per_rally==0`.
- `serve_pad_seconds` and `serve_fallback_seconds` remain in `DetectionParams` as opt-in remnants and do not affect the default path.
- The `numpy` import in the old `serve.py` was removed — it is no longer needed since there is no array manipulation.

## Concerns

None. All 101 tests pass. The implementation is exactly as specified in the plan.
