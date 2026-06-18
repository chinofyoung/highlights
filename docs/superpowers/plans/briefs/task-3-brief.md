# Task 3: (brief)

## Global Constraints

- **Python version floor:** 3.10+ (3.10.8 is the available interpreter; code is 3.10-compatible).
- **System dependency:** `ffmpeg` and `ffprobe` must be on `PATH`.
- **No heavy audio libs:** audio energy is computed from an ffmpeg-extracted WAV using NumPy only — do NOT add `librosa` or similar.
- **No build step for frontend:** plain `index.html` + JS served as static files.
- **Git is disabled for this project** (user global instruction + not a git repo). Wherever a task would normally `git commit`, instead run the task's full test suite and confirm green as the checkpoint. Do not run any state-changing git command.
- **Frame-accurate cuts:** export must re-encode cut ranges, not stream-copy (stream-copy only cuts on keyframes).
- **Detection defaults:** `sample_fps=8`, `merge_gap_seconds=2.0`, `min_rally_seconds=2.5`, `pad_seconds=1.0`, `threshold=0.5` (normalized 0–1).



---

## Task 3: Audio energy extraction

**Files:**
- Create: `app/analyzer/audio.py`
- Test: `tests/test_audio.py`

**Interfaces:**
- Consumes: ffmpeg (system), `probe_duration` not needed here.
- Produces in `app/analyzer/audio.py`:
  - `def extract_wav(video_path: str, wav_path: str, sample_rate: int = 16000) -> str` — ffmpeg-extract mono WAV at `sample_rate`; returns `wav_path`.
  - `def audio_energy(wav_path: str, hop_seconds: float) -> np.ndarray` — RMS per `hop_seconds` window. One value per time step.

- [ ] **Step 1: Write failing tests `tests/test_audio.py`**

```python
import numpy as np
from app.analyzer import audio
from tests.conftest import requires_ffmpeg


@requires_ffmpeg
def test_extract_wav_creates_file(sample_video, tmp_path):
    wav = tmp_path / "a.wav"
    out = audio.extract_wav(sample_video, str(wav))
    assert wav.exists() and out == str(wav)


@requires_ffmpeg
def test_audio_energy_higher_during_sine(sample_video, tmp_path):
    wav = tmp_path / "a.wav"
    audio.extract_wav(sample_video, str(wav))
    energy = audio.audio_energy(str(wav), hop_seconds=0.5)
    # ~12 hops over 6s; sine is in the middle 2s (hops ~4..8)
    assert len(energy) >= 10
    middle = energy[4:8].mean()
    edges = np.concatenate([energy[:3], energy[-3:]]).mean()
    assert middle > edges
```

- [ ] **Step 2: Run, expect FAIL**

Run: `pytest tests/test_audio.py -v`
Expected: FAIL (module not defined).

- [ ] **Step 3: Implement `app/analyzer/audio.py`**

```python
import subprocess
import wave
import numpy as np


def extract_wav(video_path: str, wav_path: str, sample_rate: int = 16000) -> str:
    subprocess.run(
        ["ffmpeg", "-y", "-i", video_path, "-vn", "-ac", "1",
         "-ar", str(sample_rate), "-f", "wav", wav_path],
        check=True, capture_output=True,
    )
    return wav_path


def audio_energy(wav_path: str, hop_seconds: float) -> np.ndarray:
    with wave.open(wav_path, "rb") as w:
        rate = w.getframerate()
        frames = w.readframes(w.getnframes())
    samples = np.frombuffer(frames, dtype=np.int16).astype(np.float64)
    if samples.size == 0:
        return np.zeros(0)
    hop = max(1, int(rate * hop_seconds))
    n = samples.size // hop
    if n == 0:
        return np.array([np.sqrt(np.mean(samples ** 2))])
    trimmed = samples[: n * hop].reshape(n, hop)
    return np.sqrt(np.mean(trimmed ** 2, axis=1))
```

- [ ] **Step 4: Run, expect PASS**

Run: `pytest tests/test_audio.py -v`
Expected: PASS (skips without ffmpeg).

- [ ] **Step 5: Checkpoint** — Run `pytest -v`. Confirm green.

---

