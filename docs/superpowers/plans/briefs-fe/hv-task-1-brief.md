# HV Task 1 Brief: Backend Output Endpoints + Tests

## Goal
Add 4 new endpoints to `app/api/routes.py` for managing per-rally clips and the stitched reel,
plus a comprehensive test suite in `tests/test_output.py`. No changes to existing routes.

## Working directory
/Users/chinoyoung/Code/highlights
Activate venv before any python/pytest: `source .venv/bin/activate`

## Files to touch
- `app/api/routes.py` — add imports and 4 new endpoints (keep all existing routes intact)
- `tests/test_output.py` — new file, full test suite

## Path-safety helper (REQUIRED — exact implementation)
Add at the module level in routes.py:

```python
import re

def _validate_filename(filename: str) -> str:
    """Allow only clip_NNN.mp4 or highlights.mp4; raise 400 otherwise."""
    if not re.fullmatch(r'^(clip_\d+\.mp4|highlights\.mp4)$', filename):
        raise HTTPException(400, "Invalid filename")
    return filename
```

## Output dir helper
```python
def _output_dir(video_id: str) -> Path:
    _require(video_id)          # raises 404 if unknown (already defined in routes.py)
    return workdir.video_dir(video_id) / "output"
```

## New imports needed in routes.py
- Add `import re` at the top (with the other stdlib imports)
- Add `from app.exporter.ffmpeg import concat_clips` (ffmpeg module is at app/exporter/ffmpeg.py)

## Endpoint 1: GET /api/output/{video_id}
Return:
```json
{"clips": ["clip_001.mp4", "clip_002.mp4"], "stitched": "highlights.mp4"}
```
- `clips` = sorted([p.name for p in dir.glob("clip_*.mp4")])
- `stitched` = "highlights.mp4" if (dir/"highlights.mp4").exists() else None
- If the output dir doesn't exist → return {"clips": [], "stitched": None}
  (still 404 if video_id is unknown — _output_dir handles that)

## Endpoint 2: GET /api/output/{video_id}/{filename}
- Call _validate_filename(filename) → 400 if invalid pattern
- If file exists at output_dir/filename → FileResponse(path)
- Else → HTTPException(404)

## Endpoint 3: DELETE /api/output/{video_id}/{filename}
- Call _validate_filename(filename) → 400 if invalid
- 404 if file doesn't exist in output dir
- If clip_*.mp4:
  - Delete that file
  - Gather remaining = sorted(dir.glob("clip_*.mp4"))
  - If remaining: concat_clips([str(p) for p in remaining], str(dir/"highlights.mp4"))
  - If not remaining: (dir/"highlights.mp4").unlink(missing_ok=True)
- If highlights.mp4: just delete it (leave clips intact)
- Return updated listing: {"clips": sorted([p.name for p in dir.glob("clip_*.mp4")]), "stitched": "highlights.mp4" if (dir/"highlights.mp4").exists() else None}

## Endpoint 4: DELETE /api/output/{video_id}
- Delete all clip_*.mp4 and highlights.mp4 in the output dir (leave the dir itself)
- Return {"clips": [], "stitched": None}

## Test file: tests/test_output.py

Use the EXACT same TestClient/poll pattern as tests/test_api.py:

```python
import time
from fastapi.testclient import TestClient
from tests.conftest import requires_ffmpeg


def _client():
    from app.main import app
    return TestClient(app)


def _poll(client, job_id, timeout=60.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        rec = client.get(f"/api/jobs/{job_id}").json()
        if rec["status"] in ("done", "error"):
            return rec
        time.sleep(0.2)
    raise AssertionError("job did not finish in time")
```

### Helper for setup (upload → detect → export with 2 ranges)
Create a helper `_setup_two_clips(client, sample_video, tmp_path, monkeypatch)` that:
1. `monkeypatch.setattr(workdir, "WORKDIR", tmp_path)` (import workdir from app)
2. Upload sample_video
3. POST /api/detect with params={"threshold": 0.4, "min_rally_seconds": 1.0}, poll to done
4. POST /api/export with ranges=[{"start": 0.5, "end": 2.0}, {"start": 2.5, "end": 4.0}], poll to done
5. Return video_id

### Required tests

**@requires_ffmpeg def test_list_output(sample_video, tmp_path, monkeypatch):**
- Use _setup_two_clips
- GET /api/output/{vid} → assert status 200, clips has 2 items, stitched == "highlights.mp4"

**@requires_ffmpeg def test_get_clip_file(sample_video, tmp_path, monkeypatch):**
- Use _setup_two_clips
- GET /api/output/{vid}/clip_001.mp4 → assert status 200

**def test_get_bad_filename_400():**
- Does NOT need ffmpeg — just needs a registered video_id
- Register a fake video_id in state, then test filename validation:
  - GET /api/output/{vid}/nope.mp4 → 400
  - GET /api/output/{vid}/clip_999.mp4 → 404 (valid pattern, absent file)
- NOTE: path traversal filenames like "../secrets.mp4" don't match the regex so they return 400

**@requires_ffmpeg def test_delete_clip_restitches(sample_video, tmp_path, monkeypatch):**
- Use _setup_two_clips
- DELETE /api/output/{vid}/clip_001.mp4 → assert status 200
- Assert response: clips == ["clip_002.mp4"], stitched == "highlights.mp4"

**@requires_ffmpeg def test_delete_last_clip_removes_reel(sample_video, tmp_path, monkeypatch):**
- Use _setup_two_clips
- DELETE clip_001.mp4 first
- DELETE clip_002.mp4 → assert clips == [], stitched is None

**@requires_ffmpeg def test_delete_all(sample_video, tmp_path, monkeypatch):**
- Use _setup_two_clips
- DELETE /api/output/{vid} → assert status 200, response == {"clips": [], "stitched": None}

**def test_unknown_video_404():**
- No ffmpeg needed
- GET /api/output/doesnotexist → 404

### Test isolation
Each test sets up its own state (monkeypatch + full upload flow). No cross-test state sharing.

## Verification commands
```bash
source /Users/chinoyoung/Code/highlights/.venv/bin/activate && pytest -v /Users/chinoyoung/Code/highlights/tests/test_output.py
source /Users/chinoyoung/Code/highlights/.venv/bin/activate && pytest -v --tb=short
```
