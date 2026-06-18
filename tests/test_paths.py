import sys
from pathlib import Path
from app.paths import resource_dir


def test_resource_dir_dev_is_repo_root():
    d = resource_dir()
    assert (d / "app").is_dir()           # repo root contains app/
    assert (d / "frontend").exists()


def test_resource_dir_frozen_uses_meipass(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert resource_dir() == Path(str(tmp_path))
