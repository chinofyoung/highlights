# Highlights View — Implementation Report

## Overview

Added a post-export Highlights view to the pickleball highlights app: users can watch the stitched reel and individual clips, delete clips (which re-stitches the reel), and clear all output.

---

## Backend: Endpoints + Path Safety

### Path-safety approach

All filename path params are validated with `_validate_filename(filename: str)` before any filesystem access:

```python
def _validate_filename(filename: str) -> str:
    if not re.fullmatch(r'^(clip_\d+\.mp4|highlights\.mp4)$', filename):
        raise HTTPException(400, "Invalid filename")
    return filename
```

`re.fullmatch` anchors both ends — any path traversal attempt (`../foo`, `clip_001.mp4.sh`, etc.) fails the regex and returns HTTP 400 before the output directory is ever consulted.

### Output directory resolution

```python
def _output_dir(video_id: str) -> Path:
    _require(video_id)   # raises 404 for unknown video_id
    return workdir.video_dir(video_id) / "output"
```

Unknown `video_id` always raises 404; missing output dir is not a 404 (listing returns empty).

### Endpoints added to `app/api/routes.py`

| Method | Path | Behavior |
|--------|------|----------|
| GET | `/api/output/{video_id}` | Lists `clip_*.mp4` (sorted) + stitched flag. Returns `{clips:[], stitched:null}` if output dir absent (video_id still validated). |
| GET | `/api/output/{video_id}/{filename}` | Validates filename; `FileResponse` if exists, 404 otherwise. |
| DELETE | `/api/output/{video_id}/{filename}` | Validates filename; 404 if absent. See re-stitch logic below. Returns updated listing. |
| DELETE | `/api/output/{video_id}` | Deletes all clips and highlights.mp4; returns `{clips:[], stitched:null}`. |

### Re-stitch logic (DELETE clip)

```
if filename matches clip_*.mp4:
    delete the file
    remaining = sorted(dir.glob("clip_*.mp4"))
    if remaining:
        concat_clips([str(p) for p in remaining], str(dir/"highlights.mp4"))
    else:
        (dir/"highlights.mp4").unlink(missing_ok=True)
elif filename == "highlights.mp4":
    delete it, leave clips intact
```

Deleting the last clip removes the reel automatically. The re-encode uses the existing `concat_clips()` from `app/exporter/ffmpeg.py` (re-encode concat, not stream-copy).

---

## Frontend: HighlightsView behavior

### API additions (`frontend/src/api.ts`)

Four new exports:
- `listOutput(videoId)` — GET `/api/output/{videoId}` → `{clips, stitched}`
- `outputUrl(videoId, filename)` — pure string builder, no fetch
- `deleteClip(videoId, filename)` — DELETE `/api/output/{videoId}/{filename}` → updated listing
- `clearOutput(videoId)` — DELETE `/api/output/{videoId}` → `{clips:[], stitched:null}`

All throw with server `detail` on non-OK, matching the existing client pattern.

### HighlightsView.tsx

- Mounts → `listOutput(videoId)` into state `{clips, stitched}`
- State: `listing` + `version: number` (cache-bust counter)
- Combined reel: `<video controls src={outputUrl(videoId,'highlights.mp4') + '?v=' + version}>` — the `?v=` param forces the browser to re-fetch the freshly re-stitched reel after any clip delete
- Clips grid: responsive 1-col / sm:2-col; each card has `<video>`, mono filename, `Trash2` delete button (`text-[var(--muted)] hover:text-[var(--danger)]`)
- Delete clip → `deleteClip(videoId, name)` → set listing + increment version (reel reloads)
- Clear all → `clearOutput(videoId)` → set listing + increment version
- Empty state: "No highlights yet — export some rallies."
- Design tokens used throughout: `--ink`, `--muted`, `--line`, `--surface`, `--danger`, `--teal`; `font-display`, `font-mono`

### App.tsx changes

- `ResultPanel` import + usage removed; `ResultPanel.tsx` deleted (was unused)
- `<HighlightsView videoId={videoId!} />` rendered when `exp.status === "done" && videoId`
- HighlightsView fetches its own listing on mount — stays correct after deletes without any extra state in App

---

## Tests

### Backend (`tests/test_output.py`) — 7 new tests

All under `@requires_ffmpeg` except `test_unknown_video_404` and the filename-validation assertions in `test_get_bad_filename_400`.

| Test | What it verifies |
|------|-----------------|
| `test_list_output` | After export with 2 ranges: 2 clips listed, `stitched == "highlights.mp4"` |
| `test_get_clip_file` | `GET clip_001.mp4` → 200 |
| `test_get_bad_filename_400` | Invalid names → 400; valid-pattern-but-absent (`clip_999.mp4`) → 404 |
| `test_delete_clip_restitches` | DELETE `clip_001.mp4` → response has `clips==["clip_002.mp4"]`, `stitched` present |
| `test_delete_last_clip_removes_reel` | DELETE last clip → `stitched is None` |
| `test_delete_all` | DELETE `/api/output/{vid}` → `{clips:[], stitched:null}` |
| `test_unknown_video_404` | Unknown video_id → 404 |

Pattern: identical to `tests/test_api.py` (`_client()`, `_poll()`, `monkeypatch workdir.WORKDIR`).

### Frontend (`frontend/src/test/api.test.ts`) — 4 new tests

Added to the existing `describe("api client", ...)` block:
- `listOutput` hits GET `/api/output/{id}`, returns parsed body
- `outputUrl` builds `/api/output/{id}/{filename}`
- `deleteClip` sends DELETE to `/api/output/{id}/{filename}`, returns updated listing
- `clearOutput` sends DELETE to `/api/output/{id}`, returns empty listing

---

## Verification outputs

### Backend: `pytest -v` (47 tests)

```
======================== 47 passed, 3 warnings in 6.86s ========================
```

All 47 passing. The 3 warnings are pre-existing FastAPI `on_event` deprecations — not from this change.

### Frontend: `npm run build` + `npm run test`

```
vite v6.4.3 building for production...
✓ 1585 modules transformed.
✓ built in 841ms
```

```
Tests  25 passed (25)
Test Files  5 passed (5)
```

Zero TypeScript errors. 25/25 tests pass across 5 test files.

---

## Files changed

**Backend:**
- `app/api/routes.py` — added `import re`, `concat_clips` import, `_validate_filename`, `_output_dir`, 4 endpoints
- `tests/test_output.py` — new file, 7 tests

**Frontend:**
- `frontend/src/api.ts` — 4 new exports
- `frontend/src/components/HighlightsView.tsx` — new file
- `frontend/src/App.tsx` — ResultPanel → HighlightsView swap
- `frontend/src/test/api.test.ts` — 4 new tests
- `frontend/src/components/ResultPanel.tsx` — deleted (unused)
