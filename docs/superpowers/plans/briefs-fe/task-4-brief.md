# Task 4 (modern-frontend)

## Global Constraints

- **Backend Python floor:** 3.10+ (interpreter is 3.10.8). Activate `.venv` before any pytest.
- **No new backend dependencies** — background work uses stdlib `threading`.
- **Backward-compatible analyzer/exporter signatures:** new `progress_callback` params MUST default to `None` so existing callers/tests keep working.
- **Existing backend suite (24 tests) must stay green** except the two `/api/detect` & `/api/export` tests in `tests/test_api.py`, which are intentionally updated in Task 4 to the new job flow.
- **Git is disabled** (not a git repo; user policy forbids state-changing git). Wherever a step says "Commit", instead run the task's tests (and build, where relevant) and confirm green. Never run a state-changing git command.
- **Node 22 / npm 10** are installed. Frontend commands run from `frontend/`.
- **Sensitivity semantics:** higher slider = more sensitive = more rallies; the client sends `threshold = 1 - sliderValue`.
- **Job record shape (canonical, used across backend + frontend):** `{ "status": "running"|"done"|"error", "progress": float 0.0–1.0, "result": object|null, "error": string|null }`.
- **Detect job result shape:** `{ "rallies": [{start, end, confidence}] }`. **Export job result shape:** `{ "clips": [string], "stitched": string|null }`.
- **If a pinned npm version fails to resolve,** install the latest compatible version and note it in the task report.



---

## Task 4: Async job endpoints (backend)

**Files:**
- Modify: `app/api/routes.py`
- Test: `tests/test_api.py` (rewrite the detect/export flow tests)

**Interfaces:**
- Consumes: `jobs.create/update/get`, `pipeline.analyze(..., progress_callback=)`, `exporter.export(..., progress_callback=)`, existing `_require`, `_params`, `state`.
- Produces:
  - `POST /api/detect` `{video_id, params?}` → `{"job_id": str}` (runs `analyze` in a background thread).
  - `POST /api/export` `{video_id, ranges}` → `{"job_id": str}` (runs `export` in a background thread).
  - `GET /api/jobs/{job_id}` → job record; 404 if unknown.
  - `POST /api/resegment`, `POST /api/upload`, `GET /api/video/{id}` unchanged.

- [ ] **Step 1: Rewrite the flow tests in `tests/test_api.py`** — replace `test_full_flow` with the job-based version below; keep `test_upload_rejects_non_video` and `test_params_ignores_unknown_keys` unchanged. Add a polling helper.

```python
import time

def _poll(client, job_id, timeout=60.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        rec = client.get(f"/api/jobs/{job_id}").json()
        if rec["status"] in ("done", "error"):
            return rec
        time.sleep(0.2)
    raise AssertionError("job did not finish in time")


@requires_ffmpeg
def test_full_flow_jobs(sample_video, tmp_path, monkeypatch):
    from app import workdir
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)
    client = _client()

    with open(sample_video, "rb") as f:
        up = client.post("/api/upload", files={"file": ("m.mp4", f, "video/mp4")})
    assert up.status_code == 200
    vid = up.json()["video_id"]

    det = client.post("/api/detect", json={"video_id": vid,
                      "params": {"threshold": 0.4, "min_rally_seconds": 1.0}})
    assert det.status_code == 200
    job_id = det.json()["job_id"]
    rec = _poll(client, job_id)
    assert rec["status"] == "done"
    assert isinstance(rec["result"]["rallies"], list)
    assert rec["progress"] == 1.0

    exp = client.post("/api/export", json={"video_id": vid,
                      "ranges": [{"start": 0.5, "end": 2.0}]})
    assert exp.status_code == 200
    erec = _poll(client, exp.json()["job_id"])
    assert erec["status"] == "done"
    assert erec["result"]["stitched"] is not None


def test_unknown_job_404():
    client = _client()
    assert client.get("/api/jobs/doesnotexist").status_code == 404
```

- [ ] **Step 2: Run, expect FAIL**

Run: `source .venv/bin/activate && pytest tests/test_api.py -v`
Expected: FAIL (detect returns rallies/no job_id; `/api/jobs` route missing).

- [ ] **Step 3: Modify `app/api/routes.py`** — add the import, the job endpoints, and convert detect/export to background threads. Add near the existing imports:

```python
import threading
from fastapi import BackgroundTasks  # (optional import; threads used directly below)
from app.api import jobs
```

Replace the existing `detect` and `export` handlers with:

```python
@router.post("/detect")
def detect(body: DetectBody):
    info = _require(body.video_id)
    params = _params(body.params)
    job_id = jobs.create()

    def run():
        try:
            rallies = pipeline.analyze(
                body.video_id, info["path"], params,
                progress_callback=lambda f: jobs.update(job_id, progress=f),
            )
            jobs.update(job_id, status="done", progress=1.0,
                        result={"rallies": rallies})
        except Exception as e:  # noqa: BLE001 - surface to client as job error
            jobs.update(job_id, status="error", error=str(e))

    threading.Thread(target=run, daemon=True).start()
    return {"job_id": job_id}


@router.post("/export")
def export(body: ExportBody):
    info = _require(body.video_id)
    out_dir = str(workdir.video_dir(body.video_id) / "output")
    job_id = jobs.create()

    def run():
        try:
            result = exporter.export(
                info["path"], body.ranges, out_dir,
                progress_callback=lambda f: jobs.update(job_id, progress=f),
            )
            jobs.update(job_id, status="done", progress=1.0, result=result)
        except Exception as e:  # noqa: BLE001
            jobs.update(job_id, status="error", error=str(e))

    threading.Thread(target=run, daemon=True).start()
    return {"job_id": job_id}


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    rec = jobs.get(job_id)
    if rec is None:
        raise HTTPException(404, "Unknown job_id")
    return rec
```

- [ ] **Step 4: Run, expect PASS**

Run: `source .venv/bin/activate && pytest tests/test_api.py -v`
Expected: PASS (full-flow-jobs, unknown-job-404, upload-reject, params-ignore).

- [ ] **Step 5: Checkpoint** — `source .venv/bin/activate && pytest -v`. Confirm green (whole backend suite). Backend is now job-based.

---

