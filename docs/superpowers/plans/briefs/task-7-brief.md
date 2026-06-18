# Task 7: (brief)

## Global Constraints

- **Python version floor:** 3.10+ (3.10.8 is the available interpreter; code is 3.10-compatible).
- **System dependency:** `ffmpeg` and `ffprobe` must be on `PATH`.
- **No heavy audio libs:** audio energy is computed from an ffmpeg-extracted WAV using NumPy only — do NOT add `librosa` or similar.
- **No build step for frontend:** plain `index.html` + JS served as static files.
- **Git is disabled for this project** (user global instruction + not a git repo). Wherever a task would normally `git commit`, instead run the task's full test suite and confirm green as the checkpoint. Do not run any state-changing git command.
- **Frame-accurate cuts:** export must re-encode cut ranges, not stream-copy (stream-copy only cuts on keyframes).
- **Detection defaults:** `sample_fps=8`, `merge_gap_seconds=2.0`, `min_rally_seconds=2.5`, `pad_seconds=1.0`, `threshold=0.5` (normalized 0–1).



---

## Task 7: API routes + job state

**Files:**
- Create: `app/api/__init__.py`, `app/api/state.py`, `app/api/routes.py`
- Modify: `app/main.py` (include router before static mount)
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: `pipeline.analyze/resegment`, `exporter.export`, `probe_duration`, `DetectionParams`, `workdir.video_dir`.
- Produces (REST, all JSON unless noted):
  - `POST /api/upload` (multipart `file`) → `{"video_id": str, "duration": float}`. Saves to `workdir/<id>/source.<ext>`, validates via `probe_duration`.
  - `POST /api/detect` `{"video_id", "params"?}` → `{"rallies": [...]}`. Runs `analyze`.
  - `POST /api/resegment` `{"video_id", "params"}` → `{"rallies": [...]}`. Cheap; cached signals.
  - `POST /api/export` `{"video_id", "ranges": [{"start","end"}, ...]}` → `{"clips": [...], "stitched": path}`.
  - `GET /api/video/{video_id}` → streams the source file (for the player).
  - `params` keys map onto `DetectionParams` fields; missing keys use defaults.

- [ ] **Step 1: Write failing tests `tests/test_api.py`**

```python
import io
from fastapi.testclient import TestClient
from tests.conftest import requires_ffmpeg


def _client():
    from app.main import app
    return TestClient(app)


@requires_ffmpeg
def test_full_flow(sample_video, tmp_path, monkeypatch):
    from app import workdir
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)
    client = _client()

    with open(sample_video, "rb") as f:
        up = client.post("/api/upload",
                         files={"file": ("m.mp4", f, "video/mp4")})
    assert up.status_code == 200
    vid = up.json()["video_id"]
    assert up.json()["duration"] > 5.0

    det = client.post("/api/detect", json={"video_id": vid,
                      "params": {"threshold": 0.4, "min_rally_seconds": 1.0}})
    assert det.status_code == 200
    rallies = det.json()["rallies"]
    assert isinstance(rallies, list)

    exp = client.post("/api/export", json={"video_id": vid,
                      "ranges": [{"start": 0.5, "end": 2.0}]})
    assert exp.status_code == 200
    assert exp.json()["stitched"] is not None


def test_upload_rejects_non_video(tmp_path, monkeypatch):
    from app import workdir
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)
    client = _client()
    bad = io.BytesIO(b"not a video")
    r = client.post("/api/upload", files={"file": ("x.txt", bad, "text/plain")})
    assert r.status_code == 400
```

- [ ] **Step 2: Run, expect FAIL**

Run: `pytest tests/test_api.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `app/api/__init__.py`** (empty) and `app/api/state.py`

```python
# Simple in-memory registry: video_id -> {"path": str, "duration": float}
_REGISTRY: dict[str, dict] = {}


def put(video_id: str, info: dict) -> None:
    _REGISTRY[video_id] = info


def get(video_id: str) -> dict | None:
    return _REGISTRY.get(video_id)
```

- [ ] **Step 4: Implement `app/api/routes.py`**

```python
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.config import DetectionParams
from app.deps import probe_duration
from app import workdir
from app.api import state
from app.analyzer import pipeline
from app.exporter import ffmpeg as exporter

router = APIRouter(prefix="/api")


class DetectBody(BaseModel):
    video_id: str
    params: dict | None = None


class ExportBody(BaseModel):
    video_id: str
    ranges: list[dict]


def _params(d: dict | None) -> DetectionParams:
    return DetectionParams(**(d or {}))


def _require(video_id: str) -> dict:
    info = state.get(video_id)
    if not info:
        raise HTTPException(404, "Unknown video_id")
    return info


@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    video_id = uuid.uuid4().hex[:12]
    ext = Path(file.filename or "video.mp4").suffix or ".mp4"
    dest = workdir.video_dir(video_id) / f"source{ext}"
    dest.write_bytes(await file.read())
    try:
        duration = probe_duration(str(dest))
    except ValueError:
        raise HTTPException(400, "Uploaded file is not a decodable video")
    state.put(video_id, {"path": str(dest), "duration": duration})
    return {"video_id": video_id, "duration": duration}


@router.post("/detect")
def detect(body: DetectBody):
    info = _require(body.video_id)
    rallies = pipeline.analyze(body.video_id, info["path"], _params(body.params))
    return {"rallies": rallies}


@router.post("/resegment")
def resegment(body: DetectBody):
    _require(body.video_id)
    return {"rallies": pipeline.resegment(body.video_id, _params(body.params))}


@router.post("/export")
def export(body: ExportBody):
    info = _require(body.video_id)
    out_dir = str(workdir.video_dir(body.video_id) / "output")
    return exporter.export(info["path"], body.ranges, out_dir)


@router.get("/video/{video_id}")
def get_video(video_id: str):
    info = _require(video_id)
    return FileResponse(info["path"])
```

- [ ] **Step 5: Modify `app/main.py`** — include router BEFORE the static mount (static `/` mount is greedy). Replace the file contents:

```python
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.deps import require_ffmpeg
from app.api.routes import router

app = FastAPI(title="Pickleball Highlights")


@app.on_event("startup")
def _check_ffmpeg() -> None:
    require_ffmpeg()


app.include_router(router)

WEB_DIR = Path(__file__).parent / "web"
if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
```

- [ ] **Step 6: Run, expect PASS**

Run: `pytest tests/test_api.py -v`
Expected: PASS.

- [ ] **Step 7: Checkpoint** — Run `pytest -v`. Confirm green.

---

