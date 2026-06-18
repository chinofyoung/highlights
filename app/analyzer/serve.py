import numpy as np
from app.config import DetectionParams


def derive_serve(segment: dict, onsets: np.ndarray,
                 params: DetectionParams) -> dict:
    """Derive a serve slice from a rally segment using paddle-hit onsets.

    Uses the first two onsets inside the segment to bound the serve window.
    Falls back to a fixed duration when fewer than one onset is present.
    serve_end is clamped to the segment end in all cases.
    """
    onsets = np.asarray(onsets, dtype=float)
    start = segment["start"]
    inside = np.sort(onsets[(onsets >= start) & (onsets <= segment["end"])])
    if inside.size >= 2:
        serve_end = float(inside[1]) + params.serve_pad_seconds
        resolved = True
    elif inside.size == 1:
        serve_end = float(inside[0]) + params.serve_pad_seconds
        resolved = True
    else:
        serve_end = start + params.serve_fallback_seconds
        resolved = False
    serve_end = min(serve_end, segment["end"])
    return {**segment, "serve_start": start, "serve_end": serve_end,
            "serve_resolved": resolved}
