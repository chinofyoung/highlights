# Storage Relocation Task 1 Report

## Files Changed

- `app/workdir.py` — entire file replaced per plan Step 3
- `tests/test_workdir.py` — added `import re` and appended 5 new tests per plan Step 1

## Pytest Commands and Output

### Step 2 — Failing tests (baseline verification)

```
.venv/bin/python -m pytest tests/test_workdir.py -v
```

```
collected 7 items

tests/test_workdir.py::test_roundtrip_with_onsets PASSED
tests/test_workdir.py::test_roundtrip_without_onsets PASSED
tests/test_workdir.py::test_make_video_id_sanitizes_and_suffixes FAILED
tests/test_workdir.py::test_make_video_id_unique_for_same_name FAILED
tests/test_workdir.py::test_make_video_id_empty_or_symbols_falls_back_to_video FAILED
tests/test_workdir.py::test_signals_saved_under_uploads FAILED
tests/test_workdir.py::test_uploads_and_clips_dirs_created FAILED

5 failed, 2 passed in 0.08s
```

Failures were exactly as expected: `make_video_id`/`uploads_dir`/`clips_dir` not defined; signals landed at root `vid/signals.npz` instead of `vid/uploads/signals.npz`.

### Step 4 — Post-implementation workdir tests

```
.venv/bin/python -m pytest tests/test_workdir.py -v
```

```
collected 7 items

tests/test_workdir.py::test_roundtrip_with_onsets PASSED
tests/test_workdir.py::test_roundtrip_without_onsets PASSED
tests/test_workdir.py::test_make_video_id_sanitizes_and_suffixes PASSED
tests/test_workdir.py::test_make_video_id_unique_for_same_name PASSED
tests/test_workdir.py::test_make_video_id_empty_or_symbols_falls_back_to_video PASSED
tests/test_workdir.py::test_signals_saved_under_uploads PASSED
tests/test_workdir.py::test_uploads_and_clips_dirs_created PASSED

7 passed in 0.05s
```

### Step 5 — Full suite checkpoint

```
.venv/bin/python -m pytest -q
```

```
100 passed, 3 warnings in 8.27s
```

Warnings are pre-existing FastAPI/httpx deprecation notices, unrelated to this task.

## Self-Review

- `app/workdir.py` replaced verbatim with the Step 3 code from the plan. No deviations.
- `tests/test_workdir.py`: `import re` added at top; 5 tests appended verbatim; 2 existing tests untouched.
- `video_dir` uses module-level `WORKDIR` (not `_base()`), so monkeypatching `workdir.WORKDIR` in tests correctly redirects all helpers (`uploads_dir`, `clips_dir`, `save_signals`, `load_signals`).
- No writes to real `~/Documents` during tests — all path operations in tests go through `tmp_path` via monkeypatch.
- Routes.py and pipeline.py unchanged in this task; existing tests (`test_library.py`, `test_api.py`) still build old layout and pass because routes still uses old paths. This is correct per the plan.

## Concerns

None. Suite went from 95 to 100 passed with no regressions.
