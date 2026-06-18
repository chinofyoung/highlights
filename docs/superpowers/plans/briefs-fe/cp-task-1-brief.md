# Cancel+Play Task 1 — Backend cancel support

## Context
Pickleball highlights app. You're adding cancel capability to the job tracking system.
Working directory: `/Users/chinoyoung/Code/highlights`
Backend: FastAPI in `app/` — activate venv: `source /Users/chinoyoung/Code/highlights/.venv/bin/activate`

## Files to change
- `app/api/jobs.py`
- `app/api/routes.py`
- `app/analyzer/motion.py`
- `tests/test_jobs.py`
- `tests/test_api.py`

## jobs.py changes
1. Add `"cancelled": False` to the record dict in `create()`
2. Add a `cancel(job_id: str) -> None` function that sets `cancelled=True` AND `status="cancelled"` under `_LOCK` (no-op if unknown id)

## routes.py changes
1. Add module-level `class _Cancelled(Exception): pass`
2. In BOTH the `detect` and `export` background `run()` closures, replace the inline lambda `progress_callback=lambda f: jobs.update(job_id, progress=f)` with a named local function:
   ```python
   def _cb(f):
       rec = jobs.get(job_id)
       if rec and rec["cancelled"]:
           raise _Cancelled()
       jobs.update(job_id, progress=f)
   ```
   Then pass `progress_callback=_cb` to the pipeline/exporter call.
3. In BOTH run() closures, catch `_Cancelled` BEFORE the broad `except Exception`:
   ```python
   except _Cancelled:
       jobs.update(job_id, status="cancelled")
   except Exception as e:
       jobs.update(job_id, status="error", error=str(e))
   ```
4. Add new endpoint `POST /api/jobs/{job_id}/cancel`:
   ```python
   @router.post("/jobs/{job_id}/cancel")
   def cancel_job(job_id: str):
       rec = jobs.get(job_id)
       if rec is None:
           raise HTTPException(404, "Unknown job_id")
       jobs.cancel(job_id)
       return jobs.get(job_id)
   ```

## motion.py changes
Wrap the frame-reading loop so `cap.release()` runs in a `finally` block. Currently it is called only at normal loop end — a callback raising mid-loop would leak the VideoCapture.

The loop currently looks like:
```python
    energies = []
    prev = None
    idx = 0
    last_reported = -1.0
    while True:
        ok, frame = cap.read()
        ...
        idx += 1
        if progress_callback is not None and total > 0 and idx % 30 == 0:
            ...
            progress_callback(frac)
    cap.release()
    if progress_callback is not None and total > 0 and last_reported < 1.0:
        progress_callback(1.0)
    return np.asarray(energies, dtype=float)
```

Wrap the `while True:` loop in `try:` and put `cap.release()` in `finally:`. The post-loop `progress_callback(1.0)` and the `return` stay OUTSIDE the try/finally (after it). Do NOT change the function signature or return type.

## tests/test_jobs.py — add these 3 tests (append to existing file)
```python
def test_create_has_cancelled_false():
    jid = jobs.create()
    assert jobs.get(jid)["cancelled"] == False


def test_cancel_sets_cancelled_true():
    jid = jobs.create()
    jobs.cancel(jid)
    rec = jobs.get(jid)
    assert rec["cancelled"] == True
    assert rec["status"] == "cancelled"


def test_cancel_unknown_is_noop():
    jobs.cancel("nope")  # must not raise
    assert jobs.get("nope") is None
```

## tests/test_api.py — add these 2 tests (append to existing file)
```python
def test_cancel_unknown_job_404():
    client = _client()
    assert client.post("/api/jobs/doesnotexist/cancel").status_code == 404


@requires_ffmpeg
def test_cancel_sets_status(sample_video, tmp_path, monkeypatch):
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

    # Cancel immediately — assert the endpoint's own response, not thread timing
    r = client.post(f"/api/jobs/{job_id}/cancel")
    assert r.status_code == 200
    rec = r.json()
    assert rec["cancelled"] == True
    assert rec["status"] == "cancelled"
```

## Verification
Run: `source /Users/chinoyoung/Code/highlights/.venv/bin/activate && cd /Users/chinoyoung/Code/highlights && pytest -v`
All tests must pass (both existing 35 and new 5 = 40 total).

## Report
Write your full implementation report to:
`/Users/chinoyoung/Code/highlights/docs/superpowers/plans/briefs-fe/cp-task-1-report.md`

Return to caller: STATUS (DONE/BLOCKED/NEEDS_CONTEXT), one-line test summary, concerns.
