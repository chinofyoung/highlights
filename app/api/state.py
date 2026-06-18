# Simple in-memory registry: video_id -> {"path": str, "duration": float}
_REGISTRY: dict[str, dict] = {}


def put(video_id: str, info: dict) -> None:
    _REGISTRY[video_id] = info


def get(video_id: str) -> dict | None:
    return _REGISTRY.get(video_id)
