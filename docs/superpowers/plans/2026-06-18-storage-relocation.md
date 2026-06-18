# Storage Relocation to ~/Documents/Highlights Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move per-video storage from `app/workdir/` to `~/Documents/Highlights/<slug>_<id>/` with `uploads/` and `clips/` subfolders, preserving all API behavior.

**Architecture:** Centralize the new layout in `app/workdir.py` (base path resolver, `make_video_id`, `uploads_dir`/`clips_dir` helpers, signals retargeted to `uploads/`). Then update `app/api/routes.py` and `app/analyzer/pipeline.py` to build every path through those helpers. Path-only change; detection/serve/eval logic untouched.

**Tech Stack:** Python 3.10+, FastAPI, numpy, pathlib, pytest.

## Global Constraints

- Base path: `~/Documents/Highlights` via `Path.home() / "Documents" / "Highlights"`; overridable by env var `HIGHLIGHTS_HOME`. `workdir.WORKDIR` stays the single module-level base (tests monkeypatch it).
- Per-video folder: `f"{slug}_{uuid4().hex[:6]}"`; slug = filename stem sanitized to `[A-Za-z0-9_]`, collapsed, capped 40 chars, fallback `video`.
- Two subfolders only: `uploads/` (source.<ext>, audio.wav, signals.npz, meta.json) and `clips/` (clip_NNN.mp4, highlights.mp4).
- video_id charset stays `[A-Za-z0-9_]`; validation regex widened from `{1,40}` to `{1,60}` (still no `/` or `.` → traversal-safe). Keep all `.resolve().parent == WORKDIR.resolve()` guards.
- Read/delete endpoints must NOT auto-create `clips/` (`_output_dir` uses `video_dir(id) / "clips"`, not the `clips_dir()` helper). Only the export job creates `clips/`.
- No migration of old `app/workdir/` projects.
- Git is disabled for this project (not a git repo). Each task ends with a **Checkpoint** that runs the full test suite instead of committing.
- Test command: `.venv/bin/python -m pytest`. Baseline before this plan: 95 passed.

---

### Task 1: workdir.py — base path, video-id, dir helpers, signals under uploads/

**Files:**
- Modify: `app/workdir.py` (entire file)
- Test: `tests/test_workdir.py` (append cases; keep existing two)

**Interfaces:**
- Produces:
  - `WORKDIR: Path` (module global; `~/Documents/Highlights` or `$HIGHLIGHTS_HOME`)
  - `make_video_id(original_filename: str) -> str` → `"<slug>_<6hex>"`
  - `video_dir(video_id) -> Path` (creates `WORKDIR/<id>`)
  - `uploads_dir(video_id) -> Path` (creates `WORKDIR/<id>/uploads`)
  - `clips_dir(video_id) -> Path` (creates `WORKDIR/<id>/clips`)
  - `save_signals(video_id, motion, audio, hop_seconds, onsets=None)` → writes `uploads/signals.npz`
  - `load_signals(video_id) -> (motion, audio, hop, onsets)` → reads `uploads/signals.npz`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_workdir.py` (add `import re` at the top alongside the existing imports):

```python
def test_make_video_id_sanitizes_and_suffixes():
    vid = workdir.make_video_id("My Match!.mov")
    assert re.fullmatch(r"My_Match_[0-9a-f]{6}", vid)


def test_make_video_id_unique_for_same_name():
    a = workdir.make_video_id("game.mp4")
    b = workdir.make_video_id("game.mp4")
    assert a != b
    assert a.startswith("game_") and b.startswith("game_")


def test_make_video_id_empty_or_symbols_falls_back_to_video():
    assert workdir.make_video_id("!!!.mp4").startswith("video_")
    assert workdir.make_video_id("").startswith("video_")


def test_signals_saved_under_uploads(tmp_path, monkeypatch):
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)
    workdir.save_signals("vid", np.array([0.1]), np.array([0.2]), 0.1)
    assert (tmp_path / "vid" / "uploads" / "signals.npz").exists()
    m, a, hop, o = workdir.load_signals("vid")
    assert np.allclose(m, [0.1]) and hop == 0.1


def test_uploads_and_clips_dirs_created(tmp_path, monkeypatch):
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)
    assert workdir.uploads_dir("v").name == "uploads"
    assert workdir.clips_dir("v").name == "clips"
    assert (tmp_path / "v" / "uploads").is_dir()
    assert (tmp_path / "v" / "clips").is_dir()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_workdir.py -v`
Expected: FAIL — `make_video_id`/`uploads_dir`/`clips_dir` not defined; `test_signals_saved_under_uploads` fails because signals currently land at `tmp_path/vid/signals.npz`, not `uploads/`.

- [ ] **Step 3: Rewrite app/workdir.py**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_workdir.py -v`
Expected: PASS (existing 2 + 5 new).

- [ ] **Step 5: Checkpoint**

Run: `.venv/bin/python -m pytest -q`
Expected: fully green. NOTE: `routes.py` still reads old root paths in this task; that is fine because `test_library.py` fixtures still build the old layout and `routes.py` is unchanged here. The suite stays green; routes/fixtures move together in Task 2.

---

### Task 2: routes.py + pipeline.py path migration

**Files:**
- Modify: `app/api/routes.py` (multiple functions)
- Modify: `app/analyzer/pipeline.py:28`
- Test: `tests/test_library.py` (update `_make_completed` / `_make_draft` fixtures)

**Interfaces:**
- Consumes: `workdir.make_video_id`, `workdir.uploads_dir`, `workdir.clips_dir`, `workdir.video_dir`, `workdir.WORKDIR` (Task 1).
- Produces: no new public symbols; relocates where the API reads/writes files.

- [ ] **Step 1: Update the test fixtures to the new layout (failing first)**

In `tests/test_library.py`, replace `_make_completed` and `_make_draft` with:

```python
def _make_completed(tmp_path, video_id, *, filename="game.mp4", uploaded_at=200.0, clip_count=2):
    d = tmp_path / video_id
    uploads = d / "uploads"
    clips = d / "clips"
    uploads.mkdir(parents=True, exist_ok=True)
    clips.mkdir(parents=True, exist_ok=True)
    (uploads / "source.mp4").write_bytes(b"fakevideo")
    (uploads / "signals.npz").write_bytes(b"x")
    (uploads / "meta.json").write_text(json.dumps({"original_filename": filename, "uploaded_at": uploaded_at}))
    (clips / "highlights.mp4").write_bytes(b"x")
    for i in range(1, clip_count + 1):
        (clips / f"clip_{i:03d}.mp4").write_bytes(b"x")
    return d


def _make_draft(tmp_path, video_id):
    d = tmp_path / video_id
    uploads = d / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    (uploads / "source.mp4").write_bytes(b"fakevideo")
    (uploads / "signals.npz").write_bytes(b"x")
    return d
```

- [ ] **Step 2: Run library tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_library.py -v`
Expected: FAIL — `_list_library`/`_list_drafts` still look for `output/highlights.mp4` and root `source.*`, so the new-layout fixtures aren't recognized (e.g. `test_list_library_returns_only_completed` finds no completed project).

- [ ] **Step 3: Update app/analyzer/pipeline.py**

Change the single audio path line in `analyze()` (currently `app/analyzer/pipeline.py:28`):

```python
    wav = str(workdir.uploads_dir(video_id) / "audio.wav")
```

(Everything else in `pipeline.py` is unchanged; signals already go through `workdir.save_signals`/`load_signals`.)

- [ ] **Step 4: Update app/api/routes.py**

Apply each change below.

(a) `_output_dir` (read-safe `clips/`, no auto-create):

```python
def _output_dir(video_id: str) -> Path:
    _require(video_id)          # raises 404 if unknown
    return workdir.video_dir(video_id) / "clips"
```

(b) `upload` — id from filename, source + meta under `uploads/`:

```python
@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    video_id = workdir.make_video_id(file.filename or "video")
    ext = Path(file.filename or "video.mp4").suffix or ".mp4"
    dest = workdir.uploads_dir(video_id) / f"source{ext}"
    dest.write_bytes(await file.read())
    try:
        duration = probe_duration(str(dest))
    except ValueError:
        raise HTTPException(400, "Uploaded file is not a decodable video")
    state.put(video_id, {"path": str(dest), "duration": duration})
    (workdir.uploads_dir(video_id) / "meta.json").write_text(
        json.dumps({"original_filename": file.filename or "video", "uploaded_at": time.time()})
    )
    return {"video_id": video_id, "duration": duration}
```

(c) `_project_meta` — read source/meta from `uploads/`:

```python
def _project_meta(d: Path) -> dict:
    """Return common metadata for a project directory."""
    uploads = d / "uploads"
    source_files = list(uploads.glob("source.*"))
    meta_path = uploads / "meta.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
            original_filename = meta.get(
                "original_filename",
                source_files[0].name if source_files else d.name,
            )
            uploaded_at = float(meta.get("uploaded_at", d.stat().st_mtime))
        except Exception:
            original_filename = source_files[0].name if source_files else d.name
            uploaded_at = d.stat().st_mtime
    else:
        original_filename = source_files[0].name if source_files else d.name
        uploaded_at = d.stat().st_mtime
    size_bytes = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
    return {
        "video_id": d.name,
        "original_filename": original_filename,
        "uploaded_at": uploaded_at,
        "size_bytes": size_bytes,
    }
```

(d) `_list_drafts` — source/signals in `uploads/`, completed in `clips/`:

```python
def _list_drafts() -> list[dict]:
    if not workdir.WORKDIR.exists():
        return []
    results = []
    for d in workdir.WORKDIR.iterdir():
        if not d.is_dir():
            continue
        uploads = d / "uploads"
        source_files = list(uploads.glob("source.*"))
        has_source = len(source_files) > 0
        completed = (d / "clips" / "highlights.mp4").exists()
        if not has_source or completed:
            continue
        analyzed = (uploads / "signals.npz").exists()
        meta = _project_meta(d)
        meta["analyzed"] = analyzed
        results.append(meta)
    results.sort(key=lambda x: x["uploaded_at"], reverse=True)
    return results
```

(e) `_list_library` — completed + clip_count from `clips/`:

```python
def _list_library() -> list[dict]:
    if not workdir.WORKDIR.exists():
        return []
    results = []
    for d in workdir.WORKDIR.iterdir():
        if not d.is_dir():
            continue
        if not (d / "clips" / "highlights.mp4").exists():
            continue
        meta = _project_meta(d)
        meta["clip_count"] = len(list((d / "clips").glob("clip_*.mp4")))
        results.append(meta)
    results.sort(key=lambda x: x["uploaded_at"], reverse=True)
    return results
```

(f) `rename_project` — widen regex to `{1,60}`, meta in `uploads/`:

```python
@router.patch("/projects/{video_id}/name")
def rename_project(video_id: str, body: RenameBody):
    if not re.fullmatch(r'[A-Za-z0-9_]{1,60}', video_id):
        raise HTTPException(400, "Invalid video_id")
    dir = workdir.WORKDIR / video_id
    if not dir.exists():
        raise HTTPException(404, "Project not found")
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(400, "Name cannot be empty")
    name = name[:200]
    meta_path = dir / "uploads" / "meta.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
        except Exception:
            meta = {}
    else:
        meta = {}
    meta["original_filename"] = name
    if "uploaded_at" not in meta:
        meta["uploaded_at"] = dir.stat().st_mtime
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta))
    return _project_meta(dir)
```

(g) `delete_draft` — widen regex, completed check in `clips/`:

```python
@router.delete("/drafts/{video_id}")
def delete_draft(video_id: str):
    if not re.fullmatch(r'[A-Za-z0-9_]{1,60}', video_id):
        raise HTTPException(400, "Invalid video_id")
    d = workdir.WORKDIR / video_id
    if not d.exists():
        raise HTTPException(404, "Draft not found")
    if d.resolve().parent != workdir.WORKDIR.resolve():
        raise HTTPException(400, "Invalid video_id")
    if (d / "clips" / "highlights.mp4").exists():
        raise HTTPException(409, "Not a draft (already exported)")
    shutil.rmtree(d)
    return _list_drafts()
```

(h) `open_library_project` — widen regex, source from `uploads/`:

```python
@router.post("/library/{video_id}/open")
def open_library_project(video_id: str):
    if not re.fullmatch(r'[A-Za-z0-9_]{1,60}', video_id):
        raise HTTPException(400, "Invalid video_id")
    dir = workdir.WORKDIR / video_id
    if not dir.exists():
        raise HTTPException(404, "Not found")
    source = next((dir / "uploads").glob("source.*"), None)
    if source is None:
        raise HTTPException(404, "Source not found")
    try:
        dur = probe_duration(str(source))
    except ValueError:
        raise HTTPException(400, "Cannot probe video duration")
    state.put(video_id, {"path": str(source), "duration": dur})
    return {"video_id": video_id, "duration": dur}
```

(i) `delete_library_project` — widen regex (rest unchanged):

```python
@router.delete("/library/{video_id}")
def delete_library_project(video_id: str):
    if not re.fullmatch(r'[A-Za-z0-9_]{1,60}', video_id):
        raise HTTPException(400, "Invalid video_id")
    dir = workdir.WORKDIR / video_id
    if not dir.exists():
        raise HTTPException(404, "Not found")
    if dir.resolve().parent != workdir.WORKDIR.resolve():
        raise HTTPException(400, "Invalid video_id")
    shutil.rmtree(dir)
    state._REGISTRY.pop(video_id, None)
    return _list_library()
```

(j) `export` job body — write clips into `clips/` (currently `app/api/routes.py:322`):

```python
    out_dir = str(workdir.clips_dir(body.video_id))
```

- [ ] **Step 5: Run library + api tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_library.py tests/test_api.py -v`
Expected: PASS. (`test_full_flow_jobs` uploads `m.mp4` → id like `m_ab12cd`, exports into `clips/`, `stitched` not None; `test_delete_library_invalid_id` still 400 on `bad!id`; `open` rehydrates from `uploads/source.*`.)

- [ ] **Step 6: Checkpoint**

Run: `.venv/bin/python -m pytest -q`
Expected: fully green (Task-1 baseline of 100 passed maintained; no test count change in Task 2).

---

## Self-Review

**Spec coverage:**
- Base location `~/Documents/Highlights` + `HIGHLIGHTS_HOME` override → Task 1 `_base`/`WORKDIR`. ✅
- Folder naming `slug_<6hex>`, sanitize/cap/fallback → Task 1 `_slugify`/`make_video_id` + tests. ✅
- `uploads/` + `clips/` helpers, signals under `uploads/` → Task 1. ✅
- upload writes source + meta to `uploads/` → Task 2(b). ✅
- `_output_dir` → `clips/` without auto-create → Task 2(a). ✅
- `_project_meta`/`_list_drafts`/`_list_library` read new layout → Task 2(c,d,e). ✅
- rename/open/delete-draft/delete-library use new paths + widened `{1,60}` regex + traversal guards → Task 2(f,g,h,i). ✅
- export writes to `clips/` → Task 2(j). ✅
- pipeline audio.wav under `uploads/` → Task 2 Step 3. ✅
- No migration → nothing reads `app/workdir/`; not implemented (correct). ✅
- Tests keep monkeypatching `workdir.WORKDIR`; fixtures updated → Task 2 Step 1. ✅

**Placeholder scan:** None. Every code step shows complete code; commands have expected output.

**Type/name consistency:** `make_video_id`, `uploads_dir`, `clips_dir`, `video_dir`, `WORKDIR` are defined in Task 1 and used with identical names in Task 2. `save_signals`/`load_signals` signatures unchanged from current code (only target dir moved). The `{1,60}` regex is applied verbatim to all four validating endpoints. `_output_dir` deliberately uses `video_dir(id) / "clips"` (not `clips_dir`) per the Global Constraint, consistent with `list_output`'s `if not out_dir.exists()` short-circuit.
