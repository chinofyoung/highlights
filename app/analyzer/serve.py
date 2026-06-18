from app.config import DetectionParams


def derive_serve(segment: dict, params: DetectionParams) -> dict:
    start = segment["start"]
    serve_end = min(start + params.serve_length_seconds, segment["end"])
    return {**segment, "serve_start": start, "serve_end": serve_end,
            "serve_resolved": True}
