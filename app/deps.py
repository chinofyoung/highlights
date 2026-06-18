import json
import os
import shutil
import subprocess
from app.paths import resource_dir


def ensure_ffmpeg_on_path() -> None:
    """If bundled ffmpeg/ffprobe exist (packaged app), prepend their dir to PATH.
    No-op in dev, where they aren't present and shutil.which finds system ffmpeg."""
    bin_dir = resource_dir() / "bin"
    if (bin_dir / "ffmpeg").exists() and (bin_dir / "ffprobe").exists():
        parts = os.environ.get("PATH", "").split(os.pathsep)
        if str(bin_dir) not in parts:
            os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")


def ffmpeg_available() -> bool:
    ensure_ffmpeg_on_path()
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def require_ffmpeg() -> None:
    if not ffmpeg_available():
        raise RuntimeError(
            "ffmpeg and ffprobe must be installed and on PATH. "
            "Install with e.g. `brew install ffmpeg`."
        )


def probe_duration(path: str) -> float:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "json", path],
            check=True, capture_output=True, text=True,
        ).stdout
        return float(json.loads(out)["format"]["duration"])
    except (subprocess.CalledProcessError, KeyError, ValueError) as e:
        raise ValueError(f"Not a decodable video: {path}") from e
