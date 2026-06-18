# Task 2 Report: Bundled-ffmpeg resolution in `deps.py`

## Files Changed

- **Created:** `tests/test_deps_ffmpeg.py`
- **Modified:** `app/deps.py`

## Changes

### `app/deps.py`
- Added `import os` (was missing from original).
- Added `from app.paths import resource_dir` (imports the Task 1 helper).
- Added `ensure_ffmpeg_on_path() -> None`: checks for `resource_dir()/bin/ffmpeg` and `resource_dir()/bin/ffprobe`; if both exist, prepends `bin_dir` to `os.environ["PATH"]` only when not already present (idempotent). No-op in dev (no `bin/` under the repo root).
- `ffmpeg_available()` now calls `ensure_ffmpeg_on_path()` first, then delegates to `shutil.which` as before.
- `require_ffmpeg()` and `probe_duration()` are unchanged.

### `tests/test_deps_ffmpeg.py`
- `test_ensure_ffmpeg_prepends_bundled_dir`: creates fake executable ffmpeg/ffprobe in a tmp dir, monkeypatches `deps.resource_dir` to point there, sets PATH to `/usr/bin`, asserts bin_dir is prepended, then asserts a second call does not double-prepend.
- `test_ensure_ffmpeg_noop_without_bundle`: monkeypatches resource_dir to a bare tmp dir (no `bin/`), asserts PATH is untouched.

## Pytest Output

```
.venv/bin/python -m pytest tests/test_deps_ffmpeg.py -v
2 passed in 0.01s

.venv/bin/python -m pytest -q
108 passed, 3 warnings in 8.58s
```

## Self-Review

**PATH not leaked across tests:** Both tests use `monkeypatch.setenv("PATH", ...)`. pytest's monkeypatch fixture automatically restores the original environment after each test, so mutations inside `ensure_ffmpeg_on_path()` are fully isolated.

**Dev fallback intact:** In dev (and CI), `resource_dir()` returns the repo root, which has no `bin/` directory. The existence check fails immediately, PATH is untouched, and `shutil.which("ffmpeg")` continues finding system ffmpeg as before. All 106 pre-existing tests still pass.

**Idempotency verified:** The test calls `ensure_ffmpeg_on_path()` twice and asserts `bin_dir` appears exactly once in the PATH string — confirmed by the split/count assertion.

**`resource_dir` monkeypatching:** Tests patch `deps.resource_dir` (the name in `deps.py`'s module namespace) rather than `paths.resource_dir`, which is the correct pattern for ensuring the patched reference is the one actually called inside `ensure_ffmpeg_on_path()`.

## Concerns

None. The implementation is a straight no-op in dev and the test isolation via monkeypatch is clean.
