from dataclasses import dataclass


@dataclass
class DetectionParams:
    sample_fps: int = 8
    threshold: float = 0.5          # normalized 0..1 (fixed-threshold fallback)
    merge_gap_seconds: float = 2.0
    min_rally_seconds: float = 2.5
    pad_seconds: float = 1.0

    # onsets
    onset_low_hz: float = 1500.0
    onset_high_hz: float = 8000.0
    onset_min_separation_s: float = 0.20
    onset_sensitivity: float = 3.0      # adaptive peak threshold over noise floor

    # serve derivation
    serve_pad_seconds: float = 1.0      # tail after the 2nd hit
    serve_fallback_seconds: float = 3.0 # used when onsets don't resolve

    # combine
    motion_weight: float = 1.0
    audio_weight: float = 1.0
    motion_floor: float = 0.3           # AND-gate floors (normalized)
    audio_floor: float = 0.3
    require_both: bool = True

    # adaptive threshold
    adaptive_threshold: bool = True
    threshold_k: float = 2.0            # noise_floor + k*spread

    # onset gating
    min_onsets_per_rally: int = 2
