# Task 3 (modern-frontend)

## Global Constraints

- **Backend Python floor:** 3.10+ (interpreter is 3.10.8). Activate `.venv` before any pytest.
- **No new backend dependencies** — background work uses stdlib `threading`.
- **Backward-compatible analyzer/exporter signatures:** new `progress_callback` params MUST default to `None` so existing callers/tests keep working.
- **Existing backend suite (24 tests) must stay green** except the two `/api/detect` & `/api/export` tests in `tests/test_api.py`, which are intentionally updated in Task 4 to the new job flow.
- **Git is disabled** (not a git repo; user policy forbids state-changing git). Wherever a step says "Commit", instead run the task's tests (and build, where relevant) and confirm green. Never run a state-changing git command.
- **Node 22 / npm 10** are installed. Frontend commands run from `frontend/`.
- **Sensitivity semantics:** higher slider = more sensitive = more rallies; the client sends `threshold = 1 - sliderValue`.
- **Job record shape (canonical, used across backend + frontend):** `{ "status": "running"|"done"|"error", "progress": float 0.0–1.0, "result": object|null, "error": string|null }`.
- **Detect job result shape:** `{ "rallies": [{start, end, confidence}] }`. **Export job result shape:** `{ "clips": [string], "stitched": string|null }`.
- **If a pinned npm version fails to resolve,** install the latest compatible version and note it in the task report.



---

## Task 3: Progress callback — exporter (backend)

**Files:**
- Modify: `app/exporter/ffmpeg.py`
- Test: `tests/test_progress.py` (exporter portion — append)

**Interfaces:**
- Produces: `export(src: str, ranges: list[dict], out_dir: str, progress_callback=None) -> dict` — reports `progress = clips_done / (len(ranges) + 1)` after each clip, then `1.0` after concat. Default `None` → unchanged. `cut_clip`/`concat_clips` unchanged.

- [ ] **Step 1: Append failing test to `tests/test_progress.py`**

```python
from app.exporter import ffmpeg as exporter


@requires_ffmpeg
def test_export_reports_progress(sample_video, tmp_path):
    seen = []
    exporter.export(sample_video,
                    [{"start": 0.5, "end": 2.0}, {"start": 3.0, "end": 5.0}],
                    str(tmp_path), progress_callback=lambda f: seen.append(f))
    assert seen and seen[-1] == 1.0
    assert all(0.0 <= f <= 1.0 for f in seen)
    assert seen == sorted(seen)


@requires_ffmpeg
def test_export_empty_ranges_no_progress_crash(sample_video, tmp_path):
    res = exporter.export(sample_video, [], str(tmp_path),
                          progress_callback=lambda f: None)
    assert res == {"clips": [], "stitched": None}
```

- [ ] **Step 2: Run, expect FAIL**

Run: `source .venv/bin/activate && pytest tests/test_progress.py -k export -v`
Expected: FAIL (unexpected keyword `progress_callback`).

- [ ] **Step 3: Modify `export` in `app/exporter/ffmpeg.py`** (keep `cut_clip` and `concat_clips` as-is):

```python
def export(src: str, ranges: list[dict], out_dir: str,
           progress_callback=None) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    if not ranges:
        return {"clips": [], "stitched": None}
    total = len(ranges) + 1            # clips + concat step
    clips = []
    for i, r in enumerate(ranges, start=1):
        clip_path = str(out / f"clip_{i:03d}.mp4")
        cut_clip(src, float(r["start"]), float(r["end"]), clip_path)
        clips.append(clip_path)
        if progress_callback is not None:
            progress_callback(i / total)
    stitched = str(out / "highlights.mp4")
    concat_clips(clips, stitched)
    if progress_callback is not None:
        progress_callback(1.0)
    return {"clips": clips, "stitched": stitched}
```

- [ ] **Step 4: Run, expect PASS**

Run: `source .venv/bin/activate && pytest tests/test_progress.py -v`
Expected: PASS (5 tests in file).

- [ ] **Step 5: Checkpoint** — `source .venv/bin/activate && pytest -v`. Confirm green (34 passed; existing exporter tests unaffected).

---

