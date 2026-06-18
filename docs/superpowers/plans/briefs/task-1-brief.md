# Task 1: (brief)

## Global Constraints

- **Python version floor:** 3.10+ (3.10.8 is the available interpreter; code is 3.10-compatible).
- **System dependency:** `ffmpeg` and `ffprobe` must be on `PATH`.
- **No heavy audio libs:** audio energy is computed from an ffmpeg-extracted WAV using NumPy only — do NOT add `librosa` or similar.
- **No build step for frontend:** plain `index.html` + JS served as static files.
- **Git is disabled for this project** (user global instruction + not a git repo). Wherever a task would normally `git commit`, instead run the task's full test suite and confirm green as the checkpoint. Do not run any state-changing git command.
- **Frame-accurate cuts:** export must re-encode cut ranges, not stream-copy (stream-copy only cuts on keyframes).
- **Detection defaults:** `sample_fps=8`, `merge_gap_seconds=2.0`, `min_rally_seconds=2.5`, `pad_seconds=1.0`, `threshold=0.5` (normalized 0–1).



---

## Task 1: Project scaffold + ffmpeg availability

**Files:**
- Create: `pyproject.toml`, `app/__init__.py`, `app/config.py`, `app/deps.py`, `app/main.py`
- Test: `tests/test_deps.py`, `tests/conftest.py`

**Interfaces:**
- Produces:
  - `app/config.py`: `@dataclass DetectionParams(sample_fps:int=8, threshold:float=0.5, merge_gap_seconds:float=2.0, min_rally_seconds:float=2.5, pad_seconds:float=1.0)`
  - `app/deps.py`: `def ffmpeg_available() -> bool`, `def require_ffmpeg() -> None` (raises `RuntimeError` with a clear message if missing), `def probe_duration(path: str) -> float` (seconds, via ffprobe; raises `ValueError` if not decodable).
  - `app/main.py`: `app` (FastAPI instance) that calls `require_ffmpeg()` on startup.

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "pickleball-highlights"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.29",
    "python-multipart>=0.0.9",
    "opencv-python-headless>=4.9",
    "numpy>=1.26",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "httpx>=0.27"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Create `app/__init__.py`** (empty file).

- [ ] **Step 3: Create `app/config.py`**

```python
from dataclasses import dataclass


@dataclass
class DetectionParams:
    sample_fps: int = 8
    threshold: float = 0.5          # normalized 0..1
    merge_gap_seconds: float = 2.0
    min_rally_seconds: float = 2.5
    pad_seconds: float = 1.0
```

- [ ] **Step 4: Create `tests/conftest.py`** (shared ffmpeg-generated fixtures used across tasks)

```python
import subprocess
import shutil
import numpy as np
import pytest

HAVE_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
requires_ffmpeg = pytest.mark.skipif(not HAVE_FFMPEG, reason="ffmpeg not installed")


def _run(cmd):
    subprocess.run(cmd, check=True, capture_output=True)


@pytest.fixture
def sample_video(tmp_path):
    """6s video: 0-2s static color (no motion), 2-4s moving testsrc (motion),
    4-6s static. Audio: loud sine 2-4s, silence elsewhere."""
    out = tmp_path / "sample.mp4"
    still = tmp_path / "still.mp4"
    moving = tmp_path / "moving.mp4"
    # still segment (black, silent)
    _run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=320x240:d=2:r=8",
          "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "2",
          "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p", str(still)])
    # moving segment (testsrc2 = lots of motion, loud sine audio)
    _run(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc2=s=320x240:d=2:r=8",
          "-f", "lavfi", "-i", "sine=frequency=1000:duration=2", "-t", "2",
          "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p", str(moving)])
    listf = tmp_path / "list.txt"
    listf.write_text(f"file '{still}'\nfile '{moving}'\nfile '{still}'\n")
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listf),
          "-c", "copy", str(out)])
    return str(out)
```

- [ ] **Step 5: Create `app/deps.py`**

```python
import json
import shutil
import subprocess


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def require_ffmpeg() -> None:
    if not ffmpeg_available():
        raise RuntimeError(
            "ffmpeg and ffprobe must be installed and on PATH. "
            "Install with e.g. `brew install ffmpeg`."
        )


def probe_duration(path: str) -> float:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "json", path],
            check=True, capture_output=True, text=True,
        ).stdout
        return float(json.loads(out)["format"]["duration"])
    except (subprocess.CalledProcessError, KeyError, ValueError) as e:
        raise ValueError(f"Not a decodable video: {path}") from e
```

- [ ] **Step 6: Write `tests/test_deps.py`**

```python
from app.deps import ffmpeg_available, probe_duration
from tests.conftest import requires_ffmpeg


def test_ffmpeg_available_returns_bool():
    assert isinstance(ffmpeg_available(), bool)


@requires_ffmpeg
def test_probe_duration_reads_length(sample_video):
    dur = probe_duration(sample_video)
    assert 5.0 < dur < 7.0


@requires_ffmpeg
def test_probe_duration_rejects_non_video(tmp_path):
    bad = tmp_path / "x.txt"
    bad.write_text("not a video")
    import pytest
    with pytest.raises(ValueError):
        probe_duration(str(bad))
```

- [ ] **Step 7: Run tests, expect PASS**

Run: `pytest tests/test_deps.py -v`
Expected: PASS (the two ffmpeg tests skip if ffmpeg absent).

- [ ] **Step 8: Create `app/main.py`**

```python
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.deps import require_ffmpeg

app = FastAPI(title="Pickleball Highlights")


@app.on_event("startup")
def _check_ffmpeg() -> None:
    require_ffmpeg()


WEB_DIR = Path(__file__).parent / "web"
if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
```

- [ ] **Step 9: Checkpoint** — Run `pytest -v`. Confirm green (skips allowed). Verify `python -c "import app.main"` imports without error.

---

