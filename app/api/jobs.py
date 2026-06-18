import threading
import uuid

_LOCK = threading.Lock()
_JOBS: dict[str, dict] = {}


def create() -> str:
    job_id = uuid.uuid4().hex[:12]
    with _LOCK:
        _JOBS[job_id] = {"status": "running", "progress": 0.0,
                         "result": None, "error": None, "cancelled": False}
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


def cancel(job_id: str) -> None:
    with _LOCK:
        rec = _JOBS.get(job_id)
        if rec is None:
            return
        rec["cancelled"] = True
        rec["status"] = "cancelled"


def get(job_id: str) -> dict | None:
    with _LOCK:
        rec = _JOBS.get(job_id)
        return dict(rec) if rec is not None else None
