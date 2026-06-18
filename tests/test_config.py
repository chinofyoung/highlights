from app.config import DetectionParams


def test_new_defaults_present():
    p = DetectionParams()
    assert p.onset_low_hz == 1500.0
    assert p.onset_high_hz == 8000.0
    assert p.onset_min_separation_s == 0.20
    assert p.onset_sensitivity == 3.0
    assert p.serve_pad_seconds == 1.0
    assert p.serve_fallback_seconds == 3.0
    assert p.motion_weight == 1.0
    assert p.audio_weight == 1.0
    assert p.motion_floor == 0.3
    assert p.audio_floor == 0.3
    assert p.require_both is False
    assert p.adaptive_threshold is False
    assert p.threshold_k == 2.0
    assert p.min_onsets_per_rally == 0


def test_existing_defaults_unchanged():
    p = DetectionParams()
    assert p.sample_fps == 8
    assert p.threshold == 0.5
    assert p.merge_gap_seconds == 2.0
    assert p.min_rally_seconds == 2.5
    assert p.pad_seconds == 1.0


def test_default_detector_is_simple():
    p = DetectionParams()
    assert p.combine_mode == "max"
    assert p.adaptive_threshold is False
    assert p.require_both is False
    assert p.min_onsets_per_rally == 0
    assert p.threshold == 0.5
