# Storage Relocation to ~/Documents/Highlights — Design Spec

**Date:** 2026-06-18
**Status:** Approved for planning

## Summary

Move all per-video storage out of the project tree (`app/workdir/`) into the
user's OS Documents folder at `~/Documents/Highlights/`. Each video gets a
human-readable, collision-proof folder containing two subfolders: `uploads/`
(source video + working files) and `clips/` (exported clips). Existing
`app/workdir/` projects are abandoned (no migration, no dual-read).

## Goals

- Store data under `~/Documents/Highlights/<video>/` on macOS and Windows.
- Per-video folder name is human-readable AND unique.
- Exactly two subfolders per video: `uploads/` and `clips/`.
- Keep all current API behavior (upload, detect, resegment, export, drafts,
  library, rename, delete) working — this is a path-only relocation.
- Preserve the path-traversal security guards.

## Non-Goals (YAGNI)

- Migrating or reading existing `app/workdir/` projects.
- Detecting OneDrive-relocated Windows Documents folders.
- Configurable subfolder names.

## Current Layout (baseline)

```
app/workdir/<uuid12>/
  source.<ext>
  audio.wav
  signals.npz
  meta.json            # {original_filename, uploaded_at}
  output/
    clip_001.mp4 ...
    highlights.mp4
```

- `WORKDIR = Path(__file__).parent.parent / "workdir"` in `app/workdir.py`.
- `video_id` is `uuid4().hex[:12]` and is the folder name and project key,
  validated as `[A-Za-z0-9_]{1,40}` in rename/open/delete routes.
- `app/api/routes.py` builds all paths via `workdir.video_dir(video_id)` and
  `workdir.WORKDIR`; output paths are `video_dir/output`.
- `app/analyzer/pipeline.py` writes `audio.wav` via
  `workdir.video_dir(video_id) / "audio.wav"` and signals via `workdir`.
- Tests monkeypatch `workdir.WORKDIR` to a tmp dir.

## Target Layout

```
~/Documents/Highlights/
  <slug>_<6hex>/
    uploads/
      source.<ext>
      audio.wav
      signals.npz
      meta.json
    clips/
      clip_001.mp4 ...
      highlights.mp4
```

## Component Designs

### Base location — `app/workdir.py`

```python
import os
from pathlib import Path

def _base() -> Path:
    override = os.environ.get("HIGHLIGHTS_HOME")
    if override:
        return Path(override)
    return Path.home() / "Documents" / "Highlights"

WORKDIR = _base()
```

`WORKDIR` remains the single module-level base. Tests continue to monkeypatch
`workdir.WORKDIR`. `HIGHLIGHTS_HOME` is an optional override for CI/flexibility.

### Folder naming — `app/workdir.py`

```python
import re, uuid

def _slugify(name: str) -> str:
    stem = Path(name).stem
    slug = re.sub(r'[^A-Za-z0-9_]+', '_', stem).strip('_')
    slug = re.sub(r'_+', '_', slug)[:40].strip('_')
    return slug or "video"

def make_video_id(original_filename: str) -> str:
    return f"{_slugify(original_filename)}_{uuid.uuid4().hex[:6]}"
```

- `My Match!.mov` → `My_Match_3f9a2b`. Empty/all-symbol → `video_3f9a2b`.
- Result is always within `[A-Za-z0-9_]`; max length 40 (slug) + 1 + 6 = 47.

### Directory helpers — `app/workdir.py`

```python
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
```

`save_signals`/`load_signals` change their target from `video_dir(...)` to
`uploads_dir(...)`; their logic is otherwise unchanged.

### Route updates — `app/api/routes.py`

Behavior is identical; only paths move.

- **`_validate_video_id` regex:** widen `[A-Za-z0-9_]{1,40}` → `[A-Za-z0-9_]{1,60}`
  everywhere it appears (rename, draft delete, library open, library delete).
  Still excludes `/` and `.`, so traversal-safe.
- **upload:** `video_id = workdir.make_video_id(file.filename or "video")`;
  `dest = workdir.uploads_dir(video_id) / f"source{ext}"`;
  `meta.json` written to `workdir.uploads_dir(video_id) / "meta.json"`.
- **`_output_dir(video_id)`** returns `workdir.video_dir(video_id) / "clips"`
  **without** creating `clips/` (do NOT use the `clips_dir()` helper here):
  read/delete endpoints rely on the `if not out_dir.exists()` short-circuit, so
  the directory must not be auto-created on a GET. Only the export job creates
  `clips/` (via `clips_dir()`). Output GET/DELETE endpoints and
  `_validate_filename` (`clip_NNN.mp4` / `highlights.mp4`) are otherwise
  unchanged. (This matches the baseline, where `output/` was never auto-created
  while `video_dir()` created the project root.)
- **`_project_meta(d)`:** `source_files = list((d / "uploads").glob("source.*"))`;
  `meta_path = d / "uploads" / "meta.json"`; `size_bytes` via `d.rglob("*")`;
  `video_id = d.name`.
- **`_list_drafts`:** `has_source` = `uploads/source.*` exists;
  `completed` = `clips/highlights.mp4` exists; `analyzed` = `uploads/signals.npz`
  exists.
- **`_list_library`:** `clips/highlights.mp4` exists; `clip_count` =
  `len(clips/clip_*.mp4)`.
- **rename_project:** `meta_path = dir / "uploads" / "meta.json"`.
- **open_library_project / delete_draft / delete_library_project:** project dir
  = `workdir.WORKDIR / video_id`; source = `uploads/source.*`; highlights check
  = `clips/highlights.mp4`; keep `dir.resolve().parent == workdir.WORKDIR.resolve()`.
- **export job (`/export` run):** `out_dir = str(workdir.clips_dir(body.video_id))`.

### Pipeline — `app/analyzer/pipeline.py`

`wav = str(workdir.uploads_dir(video_id) / "audio.wav")` (one line). Signals are
already written/read via `workdir.save_signals`/`load_signals`, which now target
`uploads/`.

## Error Handling

- Folder creation uses `mkdir(parents=True, exist_ok=True)` — safe if the
  Documents/Highlights tree does not yet exist.
- `make_video_id` always yields a non-empty, valid id (falls back to `video`).
- Path-traversal guards unchanged; widened regex still excludes separators.

## Testing

- `tests/test_workdir.py`:
  - `save_signals`/`load_signals` round-trip writes under `uploads/`
    (assert the file lands at `WORKDIR/<id>/uploads/signals.npz`).
  - `make_video_id`: sanitizes (`"My Match!.mov"` → starts with `My_Match_`),
    appends a 6-hex suffix, two calls on the same name differ, all-symbol/empty
    name → starts with `video_`.
  - `uploads_dir`/`clips_dir` create the right subpaths.
- Update any test that asserts the old `output/` or root-level
  `source.*`/`signals.npz`/`meta.json` paths to the new `clips/` and
  `uploads/` locations (e.g. `tests/test_api.py`, `tests/test_library.py`,
  `tests/test_pipeline.py` if they inspect structure).
- All tests keep monkeypatching `workdir.WORKDIR` to a `tmp_path`, so nothing
  writes to the real Documents folder.
- Full backend suite must stay green (relocation is path-only).

## Rollout

No migration. After deploy, new uploads land in `~/Documents/Highlights/`.
Old `app/workdir/` can be deleted manually by the user; the app ignores it.
