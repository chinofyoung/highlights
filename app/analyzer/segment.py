import numpy as np
from app.config import DetectionParams


def normalize(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    if x.size == 0:
        return x
    lo, hi = float(x.min()), float(x.max())
    if hi - lo < 1e-12:
        return np.zeros_like(x)
    return (x - lo) / (hi - lo)


def combine(motion: np.ndarray, audio: np.ndarray,
            params: DetectionParams) -> np.ndarray:
    m = normalize(motion)
    a = normalize(audio)
    if getattr(params, "combine_mode", "max") == "max":
        return np.maximum(m, a)
    denom = params.motion_weight + params.audio_weight
    env = params.motion_weight * m + params.audio_weight * a
    if denom > 0:
        env = env / denom
    if params.require_both:
        gate = (m >= params.motion_floor) & (a >= params.audio_floor)
        env = env * gate
    return env


def smooth(x: np.ndarray, window: int) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    if x.size == 0 or window <= 1:
        return x
    kernel = np.ones(window) / window
    return np.convolve(x, kernel, mode="same")


def compute_threshold(signal: np.ndarray, params: DetectionParams) -> float:
    if not params.adaptive_threshold:
        return params.threshold
    s = np.asarray(signal, dtype=float)
    if s.size == 0:
        return params.threshold
    floor = float(np.median(s))
    spread = float(np.median(np.abs(s - floor))) * 1.4826  # robust std (MAD)
    if spread < 1e-9:
        spread = float(np.std(s))  # fallback when MAD collapses (bimodal / step signal)
    if spread < 1e-9:
        # Signal is genuinely constant — no contrast to threshold against.
        # Return strictly above the floor so signal >= threshold is all False
        # and no bogus rally is produced.
        return floor + 1e-6
    return float(floor + params.threshold_k * spread)


def segment(signal: np.ndarray, hop_seconds: float,
            params: DetectionParams, threshold: float | None = None) -> list[dict]:
    signal = np.asarray(signal, dtype=float)
    thr = params.threshold if threshold is None else threshold
    active = signal >= thr

    # contiguous runs of True -> (start_idx, end_idx_exclusive)
    runs = []
    i, n = 0, len(active)
    while i < n:
        if active[i]:
            j = i
            while j < n and active[j]:
                j += 1
            runs.append((i, j))
            i = j
        else:
            i += 1

    # merge runs separated by short gaps
    merged = []
    for run in runs:
        if merged and (run[0] - merged[-1][1]) * hop_seconds <= params.merge_gap_seconds:
            merged[-1] = (merged[-1][0], run[1])
        else:
            merged.append(list(run))

    out = []
    total = n * hop_seconds
    for start_idx, end_idx in merged:
        start = start_idx * hop_seconds
        end = end_idx * hop_seconds
        if end - start < params.min_rally_seconds:
            continue
        conf = float(signal[start_idx:end_idx].mean()) if end_idx > start_idx else 0.0
        out.append({
            "start": max(0.0, start - params.pad_seconds),
            "end": min(total, end + params.pad_seconds),
            "confidence": conf,
        })
    return out


def gate_by_onsets(segments: list[dict], onsets: np.ndarray,
                   params: DetectionParams) -> list[dict]:
    if params.min_onsets_per_rally <= 0:
        return segments
    onsets = np.asarray(onsets, dtype=float)
    out = []
    for s in segments:
        count = int(np.sum((onsets >= s["start"]) & (onsets <= s["end"])))
        if count >= params.min_onsets_per_rally:
            out.append(s)
    return out
