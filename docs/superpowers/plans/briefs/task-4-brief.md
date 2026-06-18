# Task 4: (brief)

## Global Constraints

- **Python version floor:** 3.10+ (3.10.8 is the available interpreter; code is 3.10-compatible).
- **System dependency:** `ffmpeg` and `ffprobe` must be on `PATH`.
- **No heavy audio libs:** audio energy is computed from an ffmpeg-extracted WAV using NumPy only — do NOT add `librosa` or similar.
- **No build step for frontend:** plain `index.html` + JS served as static files.
- **Git is disabled for this project** (user global instruction + not a git repo). Wherever a task would normally `git commit`, instead run the task's full test suite and confirm green as the checkpoint. Do not run any state-changing git command.
- **Frame-accurate cuts:** export must re-encode cut ranges, not stream-copy (stream-copy only cuts on keyframes).
- **Detection defaults:** `sample_fps=8`, `merge_gap_seconds=2.0`, `min_rally_seconds=2.5`, `pad_seconds=1.0`, `threshold=0.5` (normalized 0–1).



---

## Task 4: Motion energy extraction

**Files:**
- Create: `app/analyzer/motion.py`
- Test: `tests/test_motion.py`

**Interfaces:**
- Consumes: ffmpeg (system), OpenCV.
- Produces in `app/analyzer/motion.py`:
  - `def motion_energy(video_path: str, sample_fps: int) -> np.ndarray` — sample frames at `sample_fps`, return mean absolute grayscale frame-difference per step. First step is 0.0 (no previous frame). One value per sampled frame; the time hop equals `1/sample_fps`.

- [ ] **Step 1: Write failing tests `tests/test_motion.py`**

```python
import numpy as np
from app.analyzer import motion
from tests.conftest import requires_ffmpeg


@requires_ffmpeg
def test_motion_energy_higher_during_movement(sample_video):
    energy = motion.motion_energy(sample_video, sample_fps=8)
    # 6s @ 8fps ≈ 48 samples; motion segment is middle 2s (samples ~16..32)
    assert len(energy) >= 40
    middle = energy[18:30].mean()
    edges = np.concatenate([energy[2:12], energy[-12:-2]]).mean()
    assert middle > edges
```

- [ ] **Step 2: Run, expect FAIL**

Run: `pytest tests/test_motion.py -v`
Expected: FAIL (module not defined).

- [ ] **Step 3: Implement `app/analyzer/motion.py`**

```python
import cv2
import numpy as np


def motion_energy(video_path: str, sample_fps: int) -> np.ndarray:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")
    src_fps = cap.get(cv2.CAP_PROP_FPS) or sample_fps
    step = max(1, int(round(src_fps / sample_fps)))

    energies = []
    prev = None
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % step == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, (160, 120))
            if prev is None:
                energies.append(0.0)
            else:
                energies.append(float(np.mean(np.abs(gray.astype(np.int16) -
                                                      prev.astype(np.int16)))))
            prev = gray
        idx += 1
    cap.release()
    return np.asarray(energies, dtype=float)
```

- [ ] **Step 4: Run, expect PASS**

Run: `pytest tests/test_motion.py -v`
Expected: PASS (skips without ffmpeg/opencv codec; if codec issue, see note).

- [ ] **Step 5: Checkpoint** — Run `pytest -v`. Confirm green.

---

