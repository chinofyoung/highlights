import io
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


def test_upload_rejects_non_video(tmp_path, monkeypatch):
    from app import workdir
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)
    client = _client()
    bad = io.BytesIO(b"not a video")
    r = client.post("/api/upload", files={"file": ("x.txt", bad, "text/plain")})
    assert r.status_code == 400


def test_params_ignores_unknown_keys():
    from app.api.routes import _params
    p = _params({"threshold": 0.3, "bogus_key": 99})
    assert p.threshold == 0.3


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
