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


def _setup_two_clips(client, sample_video, tmp_path, monkeypatch):
    from app import workdir
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)

    with open(sample_video, "rb") as f:
        up = client.post("/api/upload", files={"file": ("m.mp4", f, "video/mp4")})
    assert up.status_code == 200
    video_id = up.json()["video_id"]

    det = client.post("/api/detect", json={
        "video_id": video_id,
        "params": {"threshold": 0.4, "min_rally_seconds": 1.0},
    })
    assert det.status_code == 200
    _poll(client, det.json()["job_id"])

    exp = client.post("/api/export", json={
        "video_id": video_id,
        "ranges": [{"start": 0.5, "end": 2.0}, {"start": 2.5, "end": 4.0}],
    })
    assert exp.status_code == 200
    _poll(client, exp.json()["job_id"])

    return video_id


@requires_ffmpeg
def test_list_output(sample_video, tmp_path, monkeypatch):
    client = _client()
    vid = _setup_two_clips(client, sample_video, tmp_path, monkeypatch)
    r = client.get(f"/api/output/{vid}")
    assert r.status_code == 200
    body = r.json()
    assert len(body["clips"]) == 2
    assert body["stitched"] == "highlights.mp4"


@requires_ffmpeg
def test_get_clip_file(sample_video, tmp_path, monkeypatch):
    client = _client()
    vid = _setup_two_clips(client, sample_video, tmp_path, monkeypatch)
    r = client.get(f"/api/output/{vid}/clip_001.mp4")
    assert r.status_code == 200


def test_get_bad_filename_400():
    from app import workdir as wd
    from app.api import state
    # Register a fake video_id so _require passes
    fake_id = "fakevideo123"
    state.put(fake_id, {"path": "/fake/path.mp4", "duration": 10.0})

    client = _client()
    # Invalid pattern → 400
    r = client.get(f"/api/output/{fake_id}/nope.mp4")
    assert r.status_code == 400

    # Path traversal is also blocked by regex → 400
    r2 = client.get(f"/api/output/{fake_id}/../secrets.mp4")
    assert r2.status_code in (400, 404)  # FastAPI may normalize the path

    # Valid pattern but file doesn't exist → 404
    r3 = client.get(f"/api/output/{fake_id}/clip_999.mp4")
    assert r3.status_code == 404


@requires_ffmpeg
def test_delete_clip_restitches(sample_video, tmp_path, monkeypatch):
    client = _client()
    vid = _setup_two_clips(client, sample_video, tmp_path, monkeypatch)
    r = client.delete(f"/api/output/{vid}/clip_001.mp4")
    assert r.status_code == 200
    body = r.json()
    assert body["clips"] == ["clip_002.mp4"]
    assert body["stitched"] == "highlights.mp4"


@requires_ffmpeg
def test_delete_last_clip_removes_reel(sample_video, tmp_path, monkeypatch):
    client = _client()
    vid = _setup_two_clips(client, sample_video, tmp_path, monkeypatch)
    r1 = client.delete(f"/api/output/{vid}/clip_001.mp4")
    assert r1.status_code == 200
    r2 = client.delete(f"/api/output/{vid}/clip_002.mp4")
    assert r2.status_code == 200
    body = r2.json()
    assert body["clips"] == []
    assert body["stitched"] is None


@requires_ffmpeg
def test_delete_all(sample_video, tmp_path, monkeypatch):
    client = _client()
    vid = _setup_two_clips(client, sample_video, tmp_path, monkeypatch)
    r = client.delete(f"/api/output/{vid}")
    assert r.status_code == 200
    assert r.json() == {"clips": [], "stitched": None}


def test_unknown_video_404():
    client = _client()
    r = client.get("/api/output/doesnotexist")
    assert r.status_code == 404
