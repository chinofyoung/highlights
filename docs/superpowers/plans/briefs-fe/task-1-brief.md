# Task 1 (modern-frontend)

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

## Task 1: Job registry (backend)

**Files:**
- Create: `app/api/jobs.py`
- Test: `tests/test_jobs.py`

**Interfaces:**
- Produces in `app/api/jobs.py`:
  - `def create() -> str` — returns a new `job_id` (uuid hex, 12 chars); initial record `{"status":"running","progress":0.0,"result":None,"error":None}`.
  - `def update(job_id: str, *, progress: float | None = None, status: str | None = None, result: dict | None = None, error: str | None = None) -> None` — mutates only provided fields; no-op if job_id unknown.
  - `def get(job_id: str) -> dict | None` — returns a copy of the record, or None.
  - Thread-safe via a module-level `threading.Lock`.

- [ ] **Step 1: Write failing tests `tests/test_jobs.py`**

```python
from app.api import jobs


def test_create_returns_running_job():
    jid = jobs.create()
    rec = jobs.get(jid)
    assert rec["status"] == "running"
    assert rec["progress"] == 0.0
    assert rec["result"] is None and rec["error"] is None


def test_update_sets_fields():
    jid = jobs.create()
    jobs.update(jid, progress=0.5)
    assert jobs.get(jid)["progress"] == 0.5
    jobs.update(jid, status="done", result={"rallies": []}, progress=1.0)
    rec = jobs.get(jid)
    assert rec["status"] == "done" and rec["result"] == {"rallies": []}


def test_get_returns_copy_not_reference():
    jid = jobs.create()
    rec = jobs.get(jid)
    rec["progress"] = 9.9
    assert jobs.get(jid)["progress"] == 0.0


def test_update_unknown_job_is_noop():
    jobs.update("nope", progress=1.0)  # must not raise
    assert jobs.get("nope") is None


def test_concurrent_updates_are_safe():
    import threading
    jid = jobs.create()
    def bump():
        for _ in range(100):
            cur = jobs.get(jid)["progress"]
            jobs.update(jid, progress=cur)
    threads = [threading.Thread(target=bump) for _ in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert jobs.get(jid)["status"] == "running"  # no crash / corruption
```

- [ ] **Step 2: Run, expect FAIL**

Run: `source .venv/bin/activate && pytest tests/test_jobs.py -v`
Expected: FAIL (module not defined).

- [ ] **Step 3: Implement `app/api/jobs.py`**

```python
import threading
import uuid

_LOCK = threading.Lock()
_JOBS: dict[str, dict] = {}


def create() -> str:
    job_id = uuid.uuid4().hex[:12]
    with _LOCK:
        _JOBS[job_id] = {"status": "running", "progress": 0.0,
                         "result": None, "error": None}
    return job_id


def update(job_id: str, *, progress: float | None = None,
           status: str | None = None, result: dict | None = None,
           error: str | None = None) -> None:
    with _LOCK:
        rec = _JOBS.get(job_id)
        if rec is None:
            return
        if progress is not None:
            rec["progress"] = progress
        if status is not None:
            rec["status"] = status
        if result is not None:
            rec["result"] = result
        if error is not None:
            rec["error"] = error


def get(job_id: str) -> dict | None:
    with _LOCK:
        rec = _JOBS.get(job_id)
        return dict(rec) if rec is not None else None
```

- [ ] **Step 4: Run, expect PASS**

Run: `source .venv/bin/activate && pytest tests/test_jobs.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Checkpoint** — `source .venv/bin/activate && pytest -v`. Confirm green (29 passed).

---

