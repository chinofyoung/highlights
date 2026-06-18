# Task 1: Backend Library Endpoints + Tests

## Context
Pickleball highlights app. Backend is FastAPI in `/Users/chinoyoung/code/highlights/app/` (Python venv at `.venv`). Videos stored in `workdir/<video_id>/`. A project is **completed** iff `output/highlights.mp4` exists.

Key files (read them first):
- `/Users/chinoyoung/code/highlights/app/api/routes.py` — modify this file
- `/Users/chinoyoung/code/highlights/app/api/state.py` — `_REGISTRY`, `put(id,info)`, `get(id)`
- `/Users/chinoyoung/code/highlights/app/workdir.py` — `WORKDIR: Path`, `video_dir(id) -> Path`
- `/Users/chinoyoung/code/highlights/app/deps.py` — `probe_duration(path: str) -> float` (raises ValueError on failure)
- `/Users/chinoyoung/code/highlights/tests/conftest.py` — `sample_video` fixture + `requires_ffmpeg` marker
- `/Users/chinoyoung/code/highlights/tests/test_drafts.py` — reference patterns (monkeypatch WORKDIR, TestClient)

## Step 1: Refactor `_list_drafts` in routes.py

Extract a `_project_meta(d: Path) -> dict` helper returning:
```python
{
    "video_id": d.name,
    "original_filename": str,   # from meta.json["original_filename"] or fallback to source filename
    "uploaded_at": float,       # from float(meta.json["uploaded_at"]) or fallback to d.stat().st_mtime
    "size_bytes": int,          # sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
}
```
Fallback (when meta.json missing/broken): original_filename = first source.* filename, uploaded_at = d.stat().st_mtime.
Then simplify `_list_drafts` to call `_project_meta(d)` instead of duplicating that logic.

## Step 2: `GET /api/library`

Scan `workdir.WORKDIR` subdirs; include only completed projects (`(dir/"output"/"highlights.mp4").exists()`).
For each, return `_project_meta(dir)` dict PLUS `"clip_count": len(list((dir/"output").glob("clip_*.mp4")))`.
Sort by `uploaded_at` DESC. Return `[]` if WORKDIR missing.

Response shape per item:
```json
{"video_id": "...", "original_filename": "...", "uploaded_at": 200.0, "size_bytes": 12345, "clip_count": 2}
```

## Step 3: `POST /api/library/{video_id}/open`

```python
@router.post("/library/{video_id}/open")
def open_library_project(video_id: str):
    if not re.fullmatch(r'[A-Za-z0-9_]{1,40}', video_id):
        raise HTTPException(400, "Invalid video_id")
    dir = workdir.video_dir(video_id)
    if not dir.exists():
        raise HTTPException(404, "Not found")
    source = next(dir.glob("source.*"), None)
    if source is None:
        raise HTTPException(404, "Source not found")
    try:
        dur = probe_duration(str(source))
    except ValueError:
        raise HTTPException(400, "Cannot probe video duration")
    state.put(video_id, {"path": str(source), "duration": dur})
    return {"video_id": video_id, "duration": dur}
```

## Step 4: `DELETE /api/library/{video_id}`

```python
@router.delete("/library/{video_id}")
def delete_library_project(video_id: str):
    if not re.fullmatch(r'[A-Za-z0-9_]{1,40}', video_id):
        raise HTTPException(400, "Invalid video_id")
    dir = workdir.video_dir(video_id)
    if not dir.exists():
        raise HTTPException(404, "Not found")
    if dir.resolve().parent != workdir.WORKDIR.resolve():
        raise HTTPException(400, "Invalid video_id")
    shutil.rmtree(dir)
    state._REGISTRY.pop(video_id, None)
    return _list_library()   # the internal helper used by GET /api/library
```

(Factor a `_list_library()` internal helper reused by both GET and DELETE, analogous to `_list_drafts()`.)

## Step 5: New test file `tests/test_library.py`

Follow the EXACT same import/monkeypatch pattern as `test_drafts.py`:
- monkeypatch WORKDIR BEFORE creating TestClient
- import `from app.main import app` AFTER patching
- Each test patches its own client

```python
import json
import shutil
import numpy as np
from pathlib import Path
from fastapi.testclient import TestClient
import pytest
from tests.conftest import requires_ffmpeg
```

### Helper functions (module-level):

```python
def _make_completed(tmp_path, video_id, *, filename="game.mp4", uploaded_at=200.0, clip_count=2):
    d = tmp_path / video_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "source.mp4").write_bytes(b"fakevideo")
    (d / "signals.npz").write_bytes(b"x")
    (d / "meta.json").write_text(json.dumps({"original_filename": filename, "uploaded_at": uploaded_at}))
    (d / "output").mkdir(parents=True, exist_ok=True)
    (d / "output" / "highlights.mp4").write_bytes(b"x")
    for i in range(1, clip_count + 1):
        (d / "output" / f"clip_{i:03d}.mp4").write_bytes(b"x")
    return d

def _make_draft(tmp_path, video_id):
    d = tmp_path / video_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "source.mp4").write_bytes(b"fakevideo")
    (d / "signals.npz").write_bytes(b"x")
    return d
```

### Tests to write:

1. `test_list_library_returns_only_completed(tmp_path, monkeypatch)` — create completed "vid_done" (filename="game.mp4", uploaded_at=200.0, clip_count=2) and draft "vid_draft"; GET /api/library → 200; only vid_done in result; `clip_count==2`, `original_filename=="game.mp4"`, `uploaded_at==200.0`. vid_draft excluded.

2. `test_list_library_empty_when_workdir_missing(tmp_path, monkeypatch)` — WORKDIR = nonexistent; GET → 200, `[]`.

3. `test_delete_library_removes_folder(tmp_path, monkeypatch)` — create completed; DELETE /api/library/<id> → 200; folder gone; returned list is `[]`.

4. `test_delete_library_not_found(tmp_path, monkeypatch)` — DELETE /api/library/missing → 404.

5. `test_delete_library_invalid_id(tmp_path, monkeypatch)` — DELETE /api/library/bad!id → 400.

6. `@requires_ffmpeg` test `test_open_rehydrates_state(sample_video, tmp_path, monkeypatch)`:
   - Import sample_video fixture from conftest (it's already defined)
   - monkeypatch WORKDIR = tmp_path
   - client = TestClient(app)
   - Upload sample_video via multipart POST /api/upload
   - POST /api/detect with the video_id and empty params, poll GET /api/jobs/{job_id} until status=="done" (poll up to 30s)
   - Use result.rallies (may be empty list if video has no motion; that's OK — proceed with whatever rallies come back)
   - POST /api/export with the ranges (or empty list if no rallies), poll until done
   - Capture video_id
   - Simulate restart: `from app.api import state; state._REGISTRY.pop(video_id, None)`
   - POST /api/library/{video_id}/open → 200, `response["duration"] > 0`
   - GET /api/video/{video_id} → 200
   - POST /api/resegment `{"video_id": video_id, "params": {}}` → 200, `"rallies" in response` and `isinstance(response["rallies"], list)`

## Verification

```bash
cd /Users/chinoyoung/code/highlights && source .venv/bin/activate && pytest tests/test_library.py -v
```
Then also run the full suite to confirm nothing is broken:
```bash
pytest -v 2>&1 | tail -30
```
All tests must pass (skips for no-ffmpeg are OK).

## Report file
Write your full report to: `/Users/chinoyoung/code/highlights/docs/superpowers/plans/briefs-fe/lib-task-1-report.md`

Include: what you changed in routes.py (briefly), the pytest output for test_library.py, and the full suite pass/fail summary.

Return as your final message: STATUS (DONE/DONE_WITH_CONCERNS/NEEDS_CONTEXT/BLOCKED), one line on changes, one line on test results.
