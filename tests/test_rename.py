import json
from fastapi.testclient import TestClient


def _make_draft(tmp_path, video_id, filename="orig.mp4", uploaded_at=100.0):
    d = tmp_path / video_id
    uploads = d / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    (uploads / "source.mp4").write_bytes(b"x")
    (uploads / "signals.npz").write_bytes(b"x")
    (uploads / "meta.json").write_text(json.dumps({
        "original_filename": filename,
        "uploaded_at": uploaded_at,
    }))
    return d


def test_rename_success(tmp_path, monkeypatch):
    from app import workdir
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)

    _make_draft(tmp_path, "vid_abc")

    from app.main import app
    client = TestClient(app)
    r = client.patch("/api/projects/vid_abc/name", json={"name": "My Final Cut"})
    assert r.status_code == 200
    data = r.json()
    assert data["original_filename"] == "My Final Cut"
    assert "video_id" in data


def test_rename_reflects_in_drafts(tmp_path, monkeypatch):
    from app import workdir
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)

    _make_draft(tmp_path, "vid_abc")

    from app.main import app
    client = TestClient(app)
    r_rename = client.patch("/api/projects/vid_abc/name", json={"name": "My Final Cut"})
    new_id = r_rename.json()["video_id"]  # folder moved to sanitized name

    r = client.get("/api/drafts")
    assert r.status_code == 200
    data = r.json()
    item = next((d for d in data if d["video_id"] == new_id), None)
    assert item is not None
    assert item["original_filename"] == "My Final Cut"


def test_rename_empty_name_400(tmp_path, monkeypatch):
    from app import workdir
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)

    _make_draft(tmp_path, "vid_abc")

    from app.main import app
    client = TestClient(app)
    r = client.patch("/api/projects/vid_abc/name", json={"name": "   "})
    assert r.status_code == 400


def test_rename_missing_404(tmp_path, monkeypatch):
    from app import workdir
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)

    from app.main import app
    client = TestClient(app)
    r = client.patch("/api/projects/missing/name", json={"name": "Something"})
    assert r.status_code == 404


def test_rename_bad_id_400(tmp_path, monkeypatch):
    from app import workdir
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)

    from app.main import app
    client = TestClient(app)
    r = client.patch("/api/projects/bad!id/name", json={"name": "Something"})
    assert r.status_code == 400


def test_rename_truncates_200(tmp_path, monkeypatch):
    from app import workdir
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)

    _make_draft(tmp_path, "vid_abc")

    from app.main import app
    client = TestClient(app)
    long_name = "A" * 210
    r = client.patch("/api/projects/vid_abc/name", json={"name": long_name})
    assert r.status_code == 200
    assert len(r.json()["original_filename"]) == 200


def test_rename_no_existing_meta(tmp_path, monkeypatch):
    from app import workdir
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)

    # Create dir with source but NO meta.json
    d = tmp_path / "vid_nometa"
    uploads = d / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    (uploads / "source.mp4").write_bytes(b"x")

    from app.main import app
    client = TestClient(app)
    r = client.patch("/api/projects/vid_nometa/name", json={"name": "No Meta Name"})
    assert r.status_code == 200
    data = r.json()
    assert data["original_filename"] == "No Meta Name"

    # folder was moved to the sanitized name — use the returned video_id
    new_id = data["video_id"]
    meta_path = tmp_path / new_id / "uploads" / "meta.json"
    assert meta_path.exists()
    meta = json.loads(meta_path.read_text())
    assert meta["original_filename"] == "No Meta Name"
    assert isinstance(meta["uploaded_at"], float)


def test_rename_moves_folder_and_rekeys_state(tmp_path, monkeypatch):
    from app import workdir
    from app.api import state
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)
    _make_draft(tmp_path, "game_abc123")
    state.put("game_abc123", {"path": str(tmp_path / "game_abc123" / "uploads" / "source.mp4"),
                              "duration": 1.0})
    from app.main import app
    client = TestClient(app)

    r = client.patch("/api/projects/game_abc123/name", json={"name": "My Match"})
    assert r.status_code == 200
    body = r.json()
    assert body["video_id"] == "My_Match"
    assert body["original_filename"] == "My Match"
    assert (tmp_path / "My_Match" / "uploads" / "source.mp4").exists()
    assert not (tmp_path / "game_abc123").exists()
    # state re-keyed: old gone, new present with path inside the moved folder
    assert state.get("game_abc123") is None
    assert state.get("My_Match") is not None
    assert "My_Match" in state.get("My_Match")["path"]


def test_rename_collision_appends_suffix(tmp_path, monkeypatch):
    from app import workdir
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)
    _make_draft(tmp_path, "existing_one")
    # pre-create a folder that the sanitized target would collide with
    (tmp_path / "My_Match").mkdir(parents=True, exist_ok=True)
    from app.main import app
    client = TestClient(app)
    r = client.patch("/api/projects/existing_one/name", json={"name": "My Match"})
    assert r.status_code == 200
    assert r.json()["video_id"] == "My_Match_2"
    assert (tmp_path / "My_Match_2").exists()


def test_rename_same_sanitized_name_no_move(tmp_path, monkeypatch):
    from app import workdir
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)
    _make_draft(tmp_path, "My_Match")
    from app.main import app
    client = TestClient(app)
    r = client.patch("/api/projects/My_Match/name", json={"name": "My Match"})
    assert r.status_code == 200
    assert r.json()["video_id"] == "My_Match"   # unchanged, no _2
    assert (tmp_path / "My_Match" / "uploads").exists()
