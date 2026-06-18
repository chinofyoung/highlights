# Task 6: (brief)

## Global Constraints

- **Python version floor:** 3.10+ (3.10.8 is the available interpreter; code is 3.10-compatible).
- **System dependency:** `ffmpeg` and `ffprobe` must be on `PATH`.
- **No heavy audio libs:** audio energy is computed from an ffmpeg-extracted WAV using NumPy only — do NOT add `librosa` or similar.
- **No build step for frontend:** plain `index.html` + JS served as static files.
- **Git is disabled for this project** (user global instruction + not a git repo). Wherever a task would normally `git commit`, instead run the task's full test suite and confirm green as the checkpoint. Do not run any state-changing git command.
- **Frame-accurate cuts:** export must re-encode cut ranges, not stream-copy (stream-copy only cuts on keyframes).
- **Detection defaults:** `sample_fps=8`, `merge_gap_seconds=2.0`, `min_rally_seconds=2.5`, `pad_seconds=1.0`, `threshold=0.5` (normalized 0–1).



---

## Task 6: Export (cut + stitch)

**Files:**
- Create: `app/exporter/__init__.py`, `app/exporter/ffmpeg.py`
- Test: `tests/test_exporter.py`

**Interfaces:**
- Consumes: ffmpeg, `probe_duration` from `app/deps.py`.
- Produces in `app/exporter/ffmpeg.py`:
  - `def cut_clip(src: str, start: float, end: float, out_path: str) -> str` — frame-accurate re-encode of `[start,end]`.
  - `def concat_clips(clip_paths: list[str], out_path: str) -> str` — re-encode concat into one file.
  - `def export(src: str, ranges: list[dict], out_dir: str) -> dict` — writes `clip_001.mp4 …` and `highlights.mp4`; returns `{"clips": [...paths], "stitched": path}`. Empty `ranges` → `{"clips": [], "stitched": None}`.

- [ ] **Step 1: Write failing tests `tests/test_exporter.py`**

```python
from app.exporter import ffmpeg as ex
from app.deps import probe_duration
from tests.conftest import requires_ffmpeg


@requires_ffmpeg
def test_cut_clip_has_expected_duration(sample_video, tmp_path):
    out = tmp_path / "clip.mp4"
    ex.cut_clip(sample_video, 2.0, 4.0, str(out))
    assert out.exists()
    assert abs(probe_duration(str(out)) - 2.0) < 0.5


@requires_ffmpeg
def test_export_produces_clips_and_stitch(sample_video, tmp_path):
    ranges = [{"start": 0.5, "end": 2.0}, {"start": 3.0, "end": 5.0}]
    result = ex.export(sample_video, ranges, str(tmp_path))
    assert len(result["clips"]) == 2
    total = sum(r["end"] - r["start"] for r in ranges)
    assert abs(probe_duration(result["stitched"]) - total) < 0.8


@requires_ffmpeg
def test_export_empty_ranges(sample_video, tmp_path):
    result = ex.export(sample_video, [], str(tmp_path))
    assert result == {"clips": [], "stitched": None}
```

- [ ] **Step 2: Run, expect FAIL**

Run: `pytest tests/test_exporter.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `app/exporter/__init__.py`** (empty file) and `app/exporter/ffmpeg.py`

```python
import subprocess
from pathlib import Path


def cut_clip(src: str, start: float, end: float, out_path: str) -> str:
    duration = max(0.0, end - start)
    subprocess.run(
        ["ffmpeg", "-y", "-ss", f"{start:.3f}", "-i", src,
         "-t", f"{duration:.3f}",
         "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac",
         "-pix_fmt", "yuv420p", out_path],
        check=True, capture_output=True,
    )
    return out_path


def concat_clips(clip_paths: list[str], out_path: str) -> str:
    listfile = Path(out_path).with_suffix(".txt")
    listfile.write_text("".join(f"file '{p}'\n" for p in clip_paths))
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listfile),
         "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac",
         "-pix_fmt", "yuv420p", out_path],
        check=True, capture_output=True,
    )
    listfile.unlink(missing_ok=True)
    return out_path


def export(src: str, ranges: list[dict], out_dir: str) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    if not ranges:
        return {"clips": [], "stitched": None}
    clips = []
    for i, r in enumerate(ranges, start=1):
        clip_path = str(out / f"clip_{i:03d}.mp4")
        cut_clip(src, float(r["start"]), float(r["end"]), clip_path)
        clips.append(clip_path)
    stitched = str(out / "highlights.mp4")
    concat_clips(clips, stitched)
    return {"clips": clips, "stitched": stitched}
```

- [ ] **Step 4: Run, expect PASS**

Run: `pytest tests/test_exporter.py -v`
Expected: PASS.

- [ ] **Step 5: Checkpoint** — Run `pytest -v`. Confirm green.

---

