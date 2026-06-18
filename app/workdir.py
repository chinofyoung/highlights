import os
import re
import uuid
from pathlib import Path
import numpy as np


def _base() -> Path:
    override = os.environ.get("HIGHLIGHTS_HOME")
    if override:
        return Path(override)
    return Path.home() / "Documents" / "Highlights"


WORKDIR = _base()


def _slugify(name: str) -> str:
    stem = Path(name).stem
    slug = re.sub(r"[^A-Za-z0-9_]+", "_", stem)
    slug = re.sub(r"_+", "_", slug).strip("_")
    slug = slug[:40].strip("_")
    return slug or "video"


def make_video_id(original_filename: str) -> str:
    return f"{_slugify(original_filename)}_{uuid.uuid4().hex[:6]}"


def unique_video_id(name: str, current: str | None = None) -> str:
    """A sanitized, collision-free folder id derived from a display name.
    Returns `current` unchanged if the sanitized base already equals it."""
    base = _slugify(name)
    candidate = base
    i = 2
    while candidate != current and (WORKDIR / candidate).exists():
        candidate = f"{base}_{i}"
        i += 1
    return candidate


def video_dir(video_id: str) -> Path:
    d = WORKDIR / video_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def uploads_dir(video_id: str) -> Path:
    d = video_dir(video_id) / "uploads"
    d.mkdir(parents=True, exist_ok=True)
    return d


def clips_dir(video_id: str) -> Path:
    d = video_dir(video_id) / "clips"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_signals(video_id: str, motion: np.ndarray, audio: np.ndarray,
                 hop_seconds: float, onsets: np.ndarray | None = None) -> None:
    onsets = np.zeros(0) if onsets is None else np.asarray(onsets, dtype=float)
    np.savez(uploads_dir(video_id) / "signals.npz",
             motion=motion, audio=audio, hop=np.array([hop_seconds]),
             onsets=onsets)


def load_signals(video_id: str):
    path = uploads_dir(video_id) / "signals.npz"
    if not path.exists():
        raise FileNotFoundError(f"No cached signals for {video_id}")
    data = np.load(path)
    onsets = data["onsets"] if "onsets" in data.files else np.zeros(0)
    return data["motion"], data["audio"], float(data["hop"][0]), onsets
