# Task 1 Report: Project Scaffold + ffmpeg Availability

## Status: DONE

## Files Created

| File | Notes |
|------|-------|
| `pyproject.toml` | Project config with all dependencies; added `[tool.setuptools.packages.find]` (see Deviations) |
| `app/__init__.py` | Empty package marker |
| `app/config.py` | `DetectionParams` dataclass with all defaults from brief |
| `app/deps.py` | `ffmpeg_available()`, `require_ffmpeg()`, `probe_duration()` |
| `app/main.py` | FastAPI app with startup ffmpeg check |
| `tests/__init__.py` | Package marker for `tests` (see Deviations) |
| `tests/conftest.py` | Shared fixtures: `HAVE_FFMPEG`, `requires_ffmpeg`, `sample_video` |
| `tests/test_deps.py` | Three tests per brief |
| `.venv/` | Virtualenv created via `python3 -m venv .venv` |

## Final pytest -v Output

Command: `.venv/bin/pytest -v`

```
============================= test session starts ==============================
platform darwin -- Python 3.10.8, pytest-9.1.0, pluggy-1.6.0 -- /Users/chinoyoung/Code/highlights/.venv/bin/python3.10
cachedir: .pytest_cache
rootdir: /Users/chinoyoung/Code/highlights
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.14.0
collecting ... collected 3 items

tests/test_deps.py::test_ffmpeg_available_returns_bool PASSED            [ 33%]
tests/test_deps.py::test_probe_duration_reads_length PASSED              [ 66%]
tests/test_deps.py::test_probe_duration_rejects_non_video PASSED         [100%]

============================== 3 passed in 0.20s ===============================
```

## Deviations from Brief

### 1. Added `[tool.setuptools.packages.find]` to pyproject.toml

**Why:** The project root contains a `workdir/` directory alongside `app/`. Setuptools flat-layout discovery picked up both as top-level packages and refused to build with:
> "Multiple top-level packages discovered in a flat-layout: ['app', 'workdir']"

**Fix:** Added `[tool.setuptools.packages.find] include = ["app*"]` to constrain discovery to `app` only. This is a strictly additive fix that doesn't alter any interfaces.

### 2. Added `tests/__init__.py`

**Why:** `test_deps.py` imports with `from tests.conftest import requires_ffmpeg`. Without an `__init__.py`, the `tests` directory isn't a Python package and the import fails with `ModuleNotFoundError: No module named 'tests'`.

**Fix:** Created empty `tests/__init__.py`. This is the standard fix for package-style imports within a test directory and is expected by later tasks that will also use `from tests.conftest import ...`.

### 3. ffmpeg was present (all 3 tests passed, not 1 passed + 2 skipped)

ffmpeg finished installing before the tests ran, so all three tests executed rather than the 2 ffmpeg-gated ones being skipped. This is expected and acceptable per the task brief ("3 passed if ffmpeg finished installing").

## Concerns

None. All interfaces match the brief exactly. Import check `python -c "import app.main"` succeeds.
