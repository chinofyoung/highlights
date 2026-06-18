import subprocess
import shutil
import numpy as np
import pytest

HAVE_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
requires_ffmpeg = pytest.mark.skipif(not HAVE_FFMPEG, reason="ffmpeg not installed")


def _run(cmd):
    subprocess.run(cmd, check=True, capture_output=True)


@pytest.fixture
def sample_video(tmp_path):
    """6s video: 0-2s static color (no motion), 2-4s moving testsrc (motion),
    4-6s static. Audio: loud sine 2-4s, silence elsewhere."""
    out = tmp_path / "sample.mp4"
    still = tmp_path / "still.mp4"
    moving = tmp_path / "moving.mp4"
    # still segment (black, silent)
    _run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=320x240:d=2:r=8",
          "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "2",
          "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p", str(still)])
    # moving segment (testsrc2 = lots of motion, sine + 3kHz clicks for onset detection)
    _run(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc2=s=320x240:d=2:r=8",
          "-f", "lavfi",
          "-i", "sine=frequency=1000:duration=2,"
                "aeval=val(0)+0.6*sin(2*PI*3000*t)*lt(mod(t\\,0.6)\\,0.01)",
          "-t", "2", "-c:v", "libx264", "-c:a", "aac",
          "-pix_fmt", "yuv420p", str(moving)])
    listf = tmp_path / "list.txt"
    listf.write_text(f"file '{still}'\nfile '{moving}'\nfile '{still}'\n")
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listf),
          "-c", "copy", str(out)])
    return str(out)
