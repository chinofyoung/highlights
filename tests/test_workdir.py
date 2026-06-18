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
