import io
import json
import time
from pathlib import Path
from fastapi.testclient import TestClient
from tests.conftest import requires_ffmpeg


def _client(tmp_path):
    from app import workdir
    from app.main import app
    return TestClient(app)


def _make_draft(tmp_path, video_id, *, analyzed=True, with_meta=True,
                filename="my match.mp4", uploaded_at=123.0):
    d = tmp_path / video_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "source.mp4").write_bytes(b"x")
    if analyzed:
        (d / "signals.npz").write_bytes(b"x")
    if with_meta:
        (d / "meta.json").write_text(json.dumps({
            "original_filename": filename,
            "uploaded_at": uploaded_at,
        }))
    return d


def _make_completed(tmp_path, video_id):
    d = tmp_path / video_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "source.mp4").write_bytes(b"x")
    (d / "output").mkdir(parents=True, exist_ok=True)
    (d / "output" / "highlights.mp4").write_bytes(b"x")
    return d


def test_list_drafts_returns_only_drafts(tmp_path, monkeypatch):
    from app import workdir
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)

    _make_draft(tmp_path, "vid_draft", analyzed=True, filename="my match.mp4", uploaded_at=123.0)
    _make_completed(tmp_path, "vid_done")

    from app.main import app
    client = TestClient(app)
    r = client.get("/api/drafts")
    assert r.status_code == 200
    data = r.json()
    ids = [d["video_id"] for d in data]
    assert "vid_draft" in ids
    assert "vid_done" not in ids

    draft = next(d for d in data if d["video_id"] == "vid_draft")
    assert draft["original_filename"] == "my match.mp4"
    assert draft["analyzed"] is True
    assert draft["uploaded_at"] == 123.0


def test_list_drafts_empty_when_workdir_missing(tmp_path, monkeypatch):
    from app import workdir
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path / "nonexistent")

    from app.main import app
    client = TestClient(app)
    r = client.get("/api/drafts")
    assert r.status_code == 200
    assert r.json() == []


def test_list_drafts_no_meta_uses_fallback(tmp_path, monkeypatch):
    from app import workdir
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)

    _make_draft(tmp_path, "vid_nometa", with_meta=False)

    from app.main import app
    client = TestClient(app)
    r = client.get("/api/drafts")
    assert r.status_code == 200
    data = r.json()
    draft = next((d for d in data if d["video_id"] == "vid_nometa"), None)
    assert draft is not None
    assert draft["original_filename"] == "source.mp4"
    assert isinstance(draft["uploaded_at"], float)


def test_delete_draft_removes_folder(tmp_path, monkeypatch):
    from app import workdir
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)

    _make_draft(tmp_path, "vid_draft", filename="my match.mp4", uploaded_at=123.0)

    from app.main import app
    client = TestClient(app)
    r = client.delete("/api/drafts/vid_draft")
    assert r.status_code == 200
    assert not (tmp_path / "vid_draft").exists()
    ids = [d["video_id"] for d in r.json()]
    assert "vid_draft" not in ids


def test_delete_draft_not_found(tmp_path, monkeypatch):
    from app import workdir
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)

    from app.main import app
    client = TestClient(app)
    r = client.delete("/api/drafts/doesnotexist")
    assert r.status_code == 404


def test_delete_draft_invalid_id(tmp_path, monkeypatch):
    from app import workdir
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)

    from app.main import app
    client = TestClient(app)
    # bad!id is invalid but won't cause routing issues (no slash)
    r = client.delete("/api/drafts/bad!id")
    assert r.status_code == 400


def test_delete_draft_invalid_id_dot(tmp_path, monkeypatch):
    from app import workdir
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)

    from app.main import app
    client = TestClient(app)
    r = client.delete("/api/drafts/bad.id")
    assert r.status_code == 400


def test_delete_completed_draft_returns_409(tmp_path, monkeypatch):
    from app import workdir
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)

    # Build a completed folder: has source.mp4 AND output/highlights.mp4
    completed_id = "vid_completed"
    d = _make_completed(tmp_path, completed_id)

    from app.main import app
    client = TestClient(app)
    r = client.delete(f"/api/drafts/{completed_id}")
    assert r.status_code == 409
    assert "already exported" in r.json()["detail"].lower()
    # The folder must still exist on disk — rmtree was NOT called
    assert d.exists()


@requires_ffmpeg
def test_upload_writes_meta_and_appears_in_drafts(sample_video, tmp_path, monkeypatch):
    from app import workdir
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)

    from app.main import app
    client = TestClient(app)

    with open(sample_video, "rb") as f:
        r = client.post("/api/upload", files={"file": ("match_clip.mp4", f, "video/mp4")})
    assert r.status_code == 200
    video_id = r.json()["video_id"]

    # Check meta.json was written with correct filename
    meta_path = tmp_path / video_id / "meta.json"
    assert meta_path.exists()
    meta = json.loads(meta_path.read_text())
    assert meta["original_filename"] == "match_clip.mp4"
    assert isinstance(meta["uploaded_at"], float)

    # Check it shows up in drafts (not exported yet)
    r2 = client.get("/api/drafts")
    assert r2.status_code == 200
    ids = [d["video_id"] for d in r2.json()]
    assert video_id in ids
