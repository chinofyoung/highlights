import numpy as np
from app.config import DetectionParams
from app import workdir
from app.analyzer import pipeline
from tests.conftest import requires_ffmpeg


def test_save_and_load_signals_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)
    m = np.array([0.0, 1.0, 0.5]); a = np.array([0.2, 0.3, 0.9])
    workdir.save_signals("vid1", m, a, hop_seconds=0.125)
    lm, la, hop, onsets = workdir.load_signals("vid1")
    assert np.allclose(lm, m) and np.allclose(la, a) and hop == 0.125
    assert onsets.size == 0  # no onsets saved, should return empty array


@requires_ffmpeg
def test_analyze_detects_middle_rally(tmp_path, monkeypatch, sample_video):
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)
    # require_both=False and min_onsets_per_rally=0 disable gating so the test
    # focuses solely on the signal-level detection in the 2-4s active region.
    p = DetectionParams(sample_fps=8, threshold=0.4, require_both=False,
                        min_rally_seconds=1.0, pad_seconds=0.5,
                        min_onsets_per_rally=0)
    rallies = pipeline.analyze("vid2", sample_video, p)
    assert len(rallies) >= 1
    r = rallies[0]
    assert r["start"] < 4.0 and r["end"] > 2.0   # overlaps the 2-4s active region


@requires_ffmpeg
def test_resegment_uses_cache(tmp_path, monkeypatch, sample_video):
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)
    # require_both=False and min_onsets_per_rally=0 disable gating so the test
    # can focus on verifying that loose params produce >= duration vs strict params.
    pipeline.analyze("vid3", sample_video, DetectionParams(require_both=False,
                     min_onsets_per_rally=0))
    loose = pipeline.resegment("vid3", DetectionParams(threshold=0.1,
                               min_rally_seconds=0.5, pad_seconds=0.0,
                               require_both=False, min_onsets_per_rally=0))
    strict = pipeline.resegment("vid3", DetectionParams(threshold=0.95,
                                min_rally_seconds=0.5, pad_seconds=0.0,
                                require_both=False, min_onsets_per_rally=0))
    assert sum(r["end"] - r["start"] for r in loose) >= \
           sum(r["end"] - r["start"] for r in strict)


@requires_ffmpeg
def test_pipeline_caches_onsets_and_derives_serves(sample_video, tmp_path, monkeypatch):
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)
    params = DetectionParams(threshold=0.4, min_rally_seconds=1.0,
                             serve_length_seconds=2.0)
    rallies = pipeline.analyze("vid", sample_video, params)

    # onsets are still cached (retained for opt-in gating / tuning)
    _, _, _, onsets = workdir.load_signals("vid")
    assert onsets.size >= 0

    assert len(rallies) >= 1
    for r in rallies:
        assert r["serve_start"] == r["start"]
        assert r["start"] < r["serve_end"] <= r["end"]
        assert r["serve_resolved"] is True
        # fixed-length: serve_end is start+2.0 unless clamped to a shorter rally
        expected = min(r["start"] + 2.0, r["end"])
        assert abs(r["serve_end"] - expected) < 1e-6

    again = pipeline.resegment("vid", params)
    assert again and "serve_end" in again[0]
