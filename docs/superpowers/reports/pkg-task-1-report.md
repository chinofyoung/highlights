# Task 1 Report: `resource_dir()` helper + wire `main.py`

## Files Changed

| File | Action |
|------|--------|
| `tests/test_paths.py` | Created — 2 tests per plan spec (verbatim) |
| `app/paths.py` | Created — `resource_dir()` helper |
| `app/main.py` | Modified — WEB_DIR now uses `resource_dir()`; `from pathlib import Path` removed |

## Pytest Output

### Step 2 (failing test — before `app/paths.py` existed)
```
ModuleNotFoundError: No module named 'app.paths'
1 error during collection
```
Confirmed expected failure.

### Step 5 (new tests only)
```
tests/test_paths.py::test_resource_dir_dev_is_repo_root PASSED
tests/test_paths.py::test_resource_dir_frozen_uses_meipass PASSED
2 passed in 0.05s
```

### Step 6 (full suite checkpoint)
```
106 passed, 3 warnings in 8.51s
```
Baseline was 104; net +2. All existing tests green.

## Path Import Removal

`from pathlib import Path` was removed from `app/main.py`.

**Why:** After replacing `WEB_DIR = Path(__file__).parent.parent / "frontend" / "dist"` with `WEB_DIR = resource_dir() / "frontend" / "dist"`, the `Path` name no longer appeared anywhere in `main.py`. Keeping an unused import would be dead code. The plan explicitly instructs: "remove it only if nothing else uses it" — confirmed nothing else did.

`resource_dir()` returns a `Path` object internally, so `WEB_DIR` remains a `Path` and the `WEB_DIR.exists()` / `str(WEB_DIR)` calls on lines 18–19 continue to work correctly.

## Self-Review

- **Correctness:** `resource_dir()` uses `getattr(sys, "frozen", False)` (safe when attribute absent in dev) and `hasattr(sys, "_MEIPASS")` guard before accessing it — matches plan verbatim.
- **Dev unchanged:** In dev, `Path(__file__).resolve().parent.parent` (i.e. `app/paths.py`'s parent's parent) resolves to the repo root — identical to what the old `Path(__file__).parent.parent` in `main.py` produced. The `WEB_DIR` value is byte-for-byte equivalent.
- **Frozen path:** `monkeypatch` test injects both `sys.frozen=True` and `sys._MEIPASS=str(tmp_path)`; `resource_dir()` correctly returns `Path(tmp_path)`.
- **No scope creep:** Only the three specified files were touched. Tasks 2–5 are untouched.
- **Full suite green:** 106 passed, 0 failures, 0 errors.

## Concerns

None. The implementation is a direct transcription of the plan spec. The dev fallback is semantically equivalent to the old `WEB_DIR` computation, and the frozen path is validated by the monkeypatch test.
