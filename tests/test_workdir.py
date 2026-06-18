import re
import numpy as np
from app import workdir


def test_roundtrip_with_onsets(tmp_path, monkeypatch):
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)
    motion = np.array([0.1, 0.2, 0.3])
    audio = np.array([0.4, 0.5, 0.6])
    onsets = np.array([0.5, 1.5])
    workdir.save_signals("vid", motion, audio, 0.125, onsets)
    m, a, hop, o = workdir.load_signals("vid")
    assert np.allclose(m, motion)
    assert np.allclose(a, audio)
    assert hop == 0.125
    assert np.allclose(o, onsets)


def test_roundtrip_without_onsets(tmp_path, monkeypatch):
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)
    workdir.save_signals("vid", np.array([0.1]), np.array([0.2]), 0.1)
    _, _, _, o = workdir.load_signals("vid")
    assert o.size == 0


def test_make_video_id_sanitizes_and_suffixes():
    vid = workdir.make_video_id("My Match!.mov")
    assert re.fullmatch(r"My_Match_[0-9a-f]{6}", vid)


def test_make_video_id_unique_for_same_name():
    a = workdir.make_video_id("game.mp4")
    b = workdir.make_video_id("game.mp4")
    assert a != b
    assert a.startswith("game_") and b.startswith("game_")


def test_make_video_id_empty_or_symbols_falls_back_to_video():
    assert workdir.make_video_id("!!!.mp4").startswith("video_")
    assert workdir.make_video_id("").startswith("video_")


def test_signals_saved_under_uploads(tmp_path, monkeypatch):
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)
    workdir.save_signals("vid", np.array([0.1]), np.array([0.2]), 0.1)
    assert (tmp_path / "vid" / "uploads" / "signals.npz").exists()
    m, a, hop, o = workdir.load_signals("vid")
    assert np.allclose(m, [0.1]) and hop == 0.1


def test_uploads_and_clips_dirs_created(tmp_path, monkeypatch):
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)
    assert workdir.uploads_dir("v").name == "uploads"
    assert workdir.clips_dir("v").name == "clips"
    assert (tmp_path / "v" / "uploads").is_dir()
    assert (tmp_path / "v" / "clips").is_dir()
