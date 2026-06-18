import numpy as np
from app.config import DetectionParams
from app.analyzer.serve import derive_serve

SEG = {"start": 10.0, "end": 20.0, "confidence": 0.8}


def test_two_onsets_use_second_hit():
    p = DetectionParams(serve_pad_seconds=1.0)
    out = derive_serve(SEG, np.array([10.5, 11.5, 14.0]), p)
    assert out["serve_start"] == 10.0
    assert out["serve_end"] == 12.5      # 11.5 + 1.0
    assert out["serve_resolved"] is True
    assert out["start"] == 10.0 and out["end"] == 20.0


def test_one_onset_uses_first_hit():
    p = DetectionParams(serve_pad_seconds=1.0)
    out = derive_serve(SEG, np.array([10.5]), p)
    assert out["serve_end"] == 11.5
    assert out["serve_resolved"] is True


def test_no_onsets_falls_back_to_fixed():
    p = DetectionParams(serve_fallback_seconds=3.0)
    out = derive_serve(SEG, np.zeros(0), p)
    assert out["serve_end"] == 13.0      # 10.0 + 3.0
    assert out["serve_resolved"] is False


def test_serve_end_clamped_to_segment_end():
    p = DetectionParams(serve_fallback_seconds=999.0)
    out = derive_serve(SEG, np.zeros(0), p)
    assert out["serve_end"] == 20.0


def test_onsets_after_segment_end_are_ignored():
    # onset at 25.0 is outside [10, 20] and must be dropped;
    # only the 10.5 onset is inside the segment → 1-onset path
    p = DetectionParams(serve_pad_seconds=1.0)
    out = derive_serve(SEG, np.array([10.5, 25.0]), p)
    assert out["serve_end"] == 11.5
    assert out["serve_resolved"] is True
