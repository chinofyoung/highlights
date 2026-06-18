import json
import shutil
import time
import numpy as np
from pathlib import Path
from fastapi.testclient import TestClient
import pytest
from tests.conftest import requires_ffmpeg


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


def test_list_library_returns_only_completed(tmp_path, monkeypatch):
    from app import workdir
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)

    _make_completed(tmp_path, "vid_done", filename="game.mp4", uploaded_at=200.0, clip_count=2)
    _make_draft(tmp_path, "vid_draft")

    from app.main import app
    client = TestClient(app)
    r = client.get("/api/library")
    assert r.status_code == 200
    data = r.json()
    ids = [d["video_id"] for d in data]
    assert "vid_done" in ids
    assert "vid_draft" not in ids

    item = next(d for d in data if d["video_id"] == "vid_done")
    assert item["clip_count"] == 2
    assert item["original_filename"] == "game.mp4"
    assert item["uploaded_at"] == 200.0


def test_list_library_empty_when_workdir_missing(tmp_path, monkeypatch):
    from app import workdir
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path / "nonexistent")

    from app.main import app
    client = TestClient(app)
    r = client.get("/api/library")
    assert r.status_code == 200
    assert r.json() == []


def test_delete_library_removes_folder(tmp_path, monkeypatch):
    from app import workdir
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)

    _make_completed(tmp_path, "vid_done")

    from app.main import app
    client = TestClient(app)
    r = client.delete("/api/library/vid_done")
    assert r.status_code == 200
    assert not (tmp_path / "vid_done").exists()
    assert r.json() == []


def test_delete_library_not_found(tmp_path, monkeypatch):
    from app import workdir
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)

    from app.main import app
    client = TestClient(app)
    r = client.delete("/api/library/missing")
    assert r.status_code == 404


def test_delete_library_invalid_id(tmp_path, monkeypatch):
    from app import workdir
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)

    from app.main import app
    client = TestClient(app)
    r = client.delete("/api/library/bad!id")
    assert r.status_code == 400


@requires_ffmpeg
def test_open_rehydrates_state(sample_video, tmp_path, monkeypatch):
    from app import workdir
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)

    from app.main import app
    client = TestClient(app)

    # Upload sample video
    with open(sample_video, "rb") as f:
        r = client.post("/api/upload", files={"file": ("sample.mp4", f, "video/mp4")})
    assert r.status_code == 200
    video_id = r.json()["video_id"]

    # Run detection
    r = client.post("/api/detect", json={"video_id": video_id, "params": {}})
    assert r.status_code == 200
    job_id = r.json()["job_id"]

    # Poll until detection done (up to 30s)
    deadline = time.time() + 30
    while time.time() < deadline:
        r = client.get(f"/api/jobs/{job_id}")
        assert r.status_code == 200
        rec = r.json()
        if rec["status"] == "done":
            break
        if rec["status"] == "error":
            pytest.fail(f"Detection job failed: {rec.get('error')}")
        time.sleep(0.2)
    else:
        pytest.fail("Detection job timed out")

    rallies = rec["result"]["rallies"]

    # Export (may be empty list if no rallies detected)
    r = client.post("/api/export", json={"video_id": video_id, "ranges": rallies})
    assert r.status_code == 200
    export_job_id = r.json()["job_id"]

    # Poll until export done
    deadline = time.time() + 30
    while time.time() < deadline:
        r = client.get(f"/api/jobs/{export_job_id}")
        assert r.status_code == 200
        rec = r.json()
        if rec["status"] == "done":
            break
        if rec["status"] == "error":
            pytest.fail(f"Export job failed: {rec.get('error')}")
        time.sleep(0.2)
    else:
        pytest.fail("Export job timed out")

    # Simulate restart: remove from registry
    from app.api import state
    state._REGISTRY.pop(video_id, None)

    # open_library_project should rehydrate state
    r = client.post(f"/api/library/{video_id}/open")
    assert r.status_code == 200
    response = r.json()
    assert response["duration"] > 0

    # GET /api/video/{video_id} should now work
    r = client.get(f"/api/video/{video_id}")
    assert r.status_code == 200

    # POST /api/resegment should work
    r = client.post("/api/resegment", json={"video_id": video_id, "params": {}})
    assert r.status_code == 200
    response = r.json()
    assert "rallies" in response
    assert isinstance(response["rallies"], list)
