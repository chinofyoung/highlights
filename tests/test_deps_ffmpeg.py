import os
import stat
from pathlib import Path
from app import deps, paths


def _make_exec(p: Path):
    p.write_text("#!/bin/sh\n")
    p.chmod(p.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def test_ensure_ffmpeg_prepends_bundled_dir(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _make_exec(bin_dir / "ffmpeg")
    _make_exec(bin_dir / "ffprobe")
    monkeypatch.setattr(paths, "resource_dir", lambda: tmp_path)
    monkeypatch.setattr(deps, "resource_dir", lambda: tmp_path)
    monkeypatch.setenv("PATH", "/usr/bin")
    deps.ensure_ffmpeg_on_path()
    assert os.environ["PATH"].split(os.pathsep)[0] == str(bin_dir)
    # idempotent: calling again doesn't double-prepend
    deps.ensure_ffmpeg_on_path()
    assert os.environ["PATH"].split(os.pathsep).count(str(bin_dir)) == 1


def test_ensure_ffmpeg_noop_without_bundle(tmp_path, monkeypatch):
    monkeypatch.setattr(deps, "resource_dir", lambda: tmp_path)  # no bin/ here
    monkeypatch.setenv("PATH", "/usr/bin")
    deps.ensure_ffmpeg_on_path()
    assert os.environ["PATH"] == "/usr/bin"   # unchanged → dev falls back to which()
