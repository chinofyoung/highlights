from pathlib import Path
import numpy as np

WORKDIR = Path(__file__).parent.parent / "workdir"


def video_dir(video_id: str) -> Path:
    d = WORKDIR / video_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_signals(video_id: str, motion: np.ndarray, audio: np.ndarray,
                 hop_seconds: float, onsets: np.ndarray | None = None) -> None:
    onsets = np.zeros(0) if onsets is None else np.asarray(onsets, dtype=float)
    np.savez(video_dir(video_id) / "signals.npz",
             motion=motion, audio=audio, hop=np.array([hop_seconds]),
             onsets=onsets)


def load_signals(video_id: str):
    path = video_dir(video_id) / "signals.npz"
    if not path.exists():
        raise FileNotFoundError(f"No cached signals for {video_id}")
    data = np.load(path)
    onsets = data["onsets"] if "onsets" in data.files else np.zeros(0)
    return data["motion"], data["audio"], float(data["hop"][0]), onsets
