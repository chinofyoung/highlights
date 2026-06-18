# Task 9: (brief)

## Global Constraints

- **Python version floor:** 3.10+ (3.10.8 is the available interpreter; code is 3.10-compatible).
- **System dependency:** `ffmpeg` and `ffprobe` must be on `PATH`.
- **No heavy audio libs:** audio energy is computed from an ffmpeg-extracted WAV using NumPy only — do NOT add `librosa` or similar.
- **No build step for frontend:** plain `index.html` + JS served as static files.
- **Git is disabled for this project** (user global instruction + not a git repo). Wherever a task would normally `git commit`, instead run the task's full test suite and confirm green as the checkpoint. Do not run any state-changing git command.
- **Frame-accurate cuts:** export must re-encode cut ranges, not stream-copy (stream-copy only cuts on keyframes).
- **Detection defaults:** `sample_fps=8`, `merge_gap_seconds=2.0`, `min_rally_seconds=2.5`, `pad_seconds=1.0`, `threshold=0.5` (normalized 0–1).



---

## Task 9: README / run instructions

**Files:**
- Create: `README.md`

**Interfaces:** none (documentation).

- [ ] **Step 1: Create `README.md`**

````markdown
# Pickleball Highlights

Local tool that detects rallies in fixed-camera pickleball videos, lets you
review/trim them in the browser, and exports per-rally clips plus one stitched
highlight video.

## Requirements
- Python 3.11+
- ffmpeg + ffprobe on your PATH (`brew install ffmpeg`)

## Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Run
```bash
uvicorn app.main:app --reload
```
Open http://localhost:8000, upload a match video, review the detected rallies,
adjust sensitivity, then Export. Outputs land in `workdir/<video_id>/output/`.

## Test
```bash
pytest -v
```
(Tests that need ffmpeg auto-skip if it isn't installed.)

## Tuning detection
Defaults live in `app/config.py` (`DetectionParams`): `sample_fps`, `threshold`,
`merge_gap_seconds`, `min_rally_seconds`, `pad_seconds`.
````

- [ ] **Step 2: Checkpoint** — Run `pytest -v`. Confirm green. Confirm README commands match actual file paths.

---

