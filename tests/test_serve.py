import numpy as np
from app.config import DetectionParams
from app.analyzer.serve import derive_serve

SEG = {"start": 10.0, "end": 20.0, "confidence": 0.8}


def test_serve_is_fixed_length_from_start():
    p = DetectionParams(serve_length_seconds=6.0)
    out = derive_serve(SEG, p)
    assert out["serve_start"] == 10.0
    assert out["serve_end"] == 16.0          # 10 + 6
    assert out["serve_resolved"] is True
    assert out["start"] == 10.0 and out["end"] == 20.0  # original fields preserved


def test_serve_clamped_to_short_rally():
    short = {"start": 10.0, "end": 13.0, "confidence": 0.5}
    p = DetectionParams(serve_length_seconds=6.0)
    out = derive_serve(short, p)
    assert out["serve_end"] == 13.0          # clamped to rally end


def test_serve_length_is_configurable():
    p = DetectionParams(serve_length_seconds=4.0)
    out = derive_serve(SEG, p)
    assert out["serve_end"] == 14.0          # 10 + 4
