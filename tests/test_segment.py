import numpy as np
from app.config import DetectionParams
from app.analyzer import segment as S


def test_normalize_constant_is_zeros():
    assert np.allclose(S.normalize(np.array([5.0, 5.0, 5.0])), 0.0)


def test_normalize_scales_to_unit():
    out = S.normalize(np.array([0.0, 5.0, 10.0]))
    assert out[0] == 0.0 and out[-1] == 1.0


def test_combine_weighted_average():
    # With equal weights and require_both=False, output is the weighted average.
    m = np.array([0.0, 1.0]); a = np.array([1.0, 0.0])
    p = DetectionParams(combine_mode="weighted", require_both=False, motion_weight=1.0, audio_weight=1.0)
    assert np.allclose(S.combine(m, a, p), [0.5, 0.5])


def test_segment_finds_single_active_span():
    # hop=0.5s, 20 steps = 10s. Active 2s..6s.
    sig = np.zeros(20); sig[4:12] = 1.0
    p = DetectionParams(threshold=0.5, merge_gap_seconds=0.0,
                        min_rally_seconds=1.0, pad_seconds=0.0)
    spans = S.segment(sig, hop_seconds=0.5, params=p)
    assert len(spans) == 1
    assert abs(spans[0]["start"] - 2.0) < 0.6
    assert abs(spans[0]["end"] - 6.0) < 0.6


def test_segment_merges_short_gap():
    sig = np.zeros(40)
    sig[4:12] = 1.0; sig[14:22] = 1.0   # 1s gap between spans (hop 0.5)
    p = DetectionParams(threshold=0.5, merge_gap_seconds=2.0,
                        min_rally_seconds=1.0, pad_seconds=0.0)
    spans = S.segment(sig, hop_seconds=0.5, params=p)
    assert len(spans) == 1


def test_segment_drops_short_span():
    sig = np.zeros(40); sig[4:6] = 1.0   # 1s span
    p = DetectionParams(threshold=0.5, merge_gap_seconds=0.0,
                        min_rally_seconds=2.5, pad_seconds=0.0)
    assert S.segment(sig, hop_seconds=0.5, params=p) == []


def test_segment_applies_padding_and_clamps():
    sig = np.zeros(20); sig[0:8] = 1.0   # span at very start
    p = DetectionParams(threshold=0.5, merge_gap_seconds=0.0,
                        min_rally_seconds=1.0, pad_seconds=1.0)
    spans = S.segment(sig, hop_seconds=0.5, params=p)
    assert spans[0]["start"] == 0.0       # clamped, not negative


def test_segment_empty_when_all_quiet():
    assert S.segment(np.zeros(20), hop_seconds=0.5,
                     params=DetectionParams()) == []


def test_combine_and_segment_handle_empty():
    empty = np.zeros(0)
    combined = S.combine(empty, empty, DetectionParams())
    assert combined.size == 0
    assert S.segment(S.smooth(combined, 4), hop_seconds=0.125,
                     params=DetectionParams()) == []


from app.analyzer.segment import combine


def test_combine_and_gate_suppresses_single_channel():
    # motion active, audio silent -> gated to ~0 when require_both
    motion = np.array([0.0, 1.0, 0.0])
    audio = np.array([0.0, 0.0, 0.0])
    p = DetectionParams(combine_mode="weighted", require_both=True, motion_floor=0.3, audio_floor=0.3)
    out = combine(motion, audio, p)
    assert np.all(out == 0.0)


def test_combine_passes_when_both_active():
    motion = np.array([0.0, 1.0, 0.0])
    audio = np.array([0.0, 1.0, 0.0])
    p = DetectionParams(combine_mode="weighted", require_both=True)
    out = combine(motion, audio, p)
    assert out[1] > out[0]
    assert out[1] > out[2]


def test_combine_require_both_false_is_max_like():
    motion = np.array([0.0, 1.0, 0.0])
    audio = np.array([0.0, 0.0, 0.0])
    p = DetectionParams(combine_mode="weighted", require_both=False, motion_weight=1.0, audio_weight=0.0)
    out = combine(motion, audio, p)
    assert out[1] > 0.0


from app.analyzer.segment import compute_threshold, gate_by_onsets, segment


def test_compute_threshold_fixed_when_disabled():
    sig = np.array([0.0, 0.5, 1.0])
    p = DetectionParams(adaptive_threshold=False, threshold=0.42)
    assert compute_threshold(sig, p) == 0.42


def test_compute_threshold_adaptive_scales_with_noise():
    quiet = np.concatenate([np.zeros(90), np.ones(10)])
    p = DetectionParams(adaptive_threshold=True, threshold_k=2.0)
    thr = compute_threshold(quiet, p)
    assert 0.0 < thr <= 1.0


def test_segment_accepts_explicit_threshold():
    # half active above 0.6
    sig = np.concatenate([np.zeros(40), np.full(40, 0.9), np.zeros(40)])
    p = DetectionParams(min_rally_seconds=0.0, pad_seconds=0.0, merge_gap_seconds=0.0)
    out = segment(sig, hop_seconds=0.1, params=p, threshold=0.6)
    assert len(out) == 1
    assert out[0]["start"] >= 4.0 - 1e-6


def test_gating_drops_low_onset_segments():
    segs = [
        {"start": 0.0, "end": 5.0, "confidence": 0.9},   # 3 onsets -> keep
        {"start": 10.0, "end": 15.0, "confidence": 0.9}, # 1 onset  -> drop
    ]
    onsets = np.array([0.5, 1.0, 1.5, 11.0])
    p = DetectionParams(min_onsets_per_rally=2)
    out = gate_by_onsets(segs, onsets, p)
    assert len(out) == 1
    assert out[0]["start"] == 0.0


def test_gating_disabled_when_zero():
    segs = [{"start": 0.0, "end": 5.0, "confidence": 0.9}]
    p = DetectionParams(min_onsets_per_rally=0)
    assert gate_by_onsets(segs, np.zeros(0), p) == segs


def test_adaptive_threshold_flat_signal_yields_no_rally():
    sig = np.full(100, 0.5)
    p = DetectionParams(adaptive_threshold=True, min_rally_seconds=0.0, pad_seconds=0.0, merge_gap_seconds=0.0)
    thr = compute_threshold(sig, p)
    assert thr > 0.5
    assert segment(sig, 0.1, p, threshold=thr) == []


def test_adaptive_threshold_all_zero_yields_no_rally():
    sig = np.zeros(100)
    p = DetectionParams(min_rally_seconds=0.0, pad_seconds=0.0, merge_gap_seconds=0.0)
    thr = compute_threshold(sig, p)
    assert segment(sig, 0.1, p, threshold=thr) == []


def test_combine_max_mode_is_default():
    motion = np.array([0.0, 1.0, 0.0])
    audio = np.array([0.0, 0.0, 0.0])
    p = DetectionParams()  # combine_mode="max" by default
    out = combine(motion, audio, p)
    # max-combine: motion spike survives even with silent audio
    assert out[1] == 1.0
    assert out[0] == 0.0


def test_combine_weighted_mode_still_available():
    motion = np.array([0.0, 1.0, 0.0])
    audio = np.array([0.0, 0.0, 0.0])
    p = DetectionParams(combine_mode="weighted", require_both=True,
                        motion_floor=0.3, audio_floor=0.3)
    out = combine(motion, audio, p)
    # AND-gate zeroes the motion-only spike
    assert np.all(out == 0.0)
