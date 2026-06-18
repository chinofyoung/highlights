# Task 1 Report: Backend Library Endpoints + Tests

## Changes to `app/api/routes.py`

1. **Added `_project_meta(d: Path) -> dict` helper** (lines 132–156): Extracts common metadata (video_id, original_filename, uploaded_at, size_bytes) from a project directory. Reads meta.json with fallback to source filename and directory mtime when missing or broken. Used by both `_list_drafts` and `_list_library`.

2. **Refactored `_list_drafts`**: Now calls `_project_meta(d)` instead of duplicating the metadata extraction logic. Appends `analyzed` key after calling the helper.

3. **Added `_list_library()` internal helper**: Scans WORKDIR for completed projects (those with `output/highlights.mp4`), calls `_project_meta` for each, adds `clip_count`, sorts by `uploaded_at` DESC.

4. **Added `GET /api/library`**: Calls `_list_library()`, returns `[]` when WORKDIR missing.

5. **Added `POST /api/library/{video_id}/open`**: Validates video_id, checks directory exists (using `WORKDIR / video_id` to avoid auto-creation), finds source file, probes duration via ffprobe, puts result in state registry, returns `{video_id, duration}`.

6. **Added `DELETE /api/library/{video_id}`**: Validates video_id, checks directory exists, verifies parent is WORKDIR (path traversal guard), rmtrees the folder, removes from state registry, returns updated library list.

## Created `tests/test_library.py`

Six tests following the same monkeypatch-before-import pattern as `test_drafts.py`:

- `test_list_library_returns_only_completed` — verifies only completed projects appear; checks clip_count, original_filename, uploaded_at
- `test_list_library_empty_when_workdir_missing` — WORKDIR nonexistent → returns `[]`
- `test_delete_library_removes_folder` — folder deleted, returned list is `[]`
- `test_delete_library_not_found` — 404 on unknown video_id
- `test_delete_library_invalid_id` — 400 on `bad!id`
- `test_open_rehydrates_state` (`@requires_ffmpeg`) — full upload → detect → export → simulate restart → open → verify video and resegment work

## Test Results

### `pytest tests/test_library.py -v`
```
6 passed, 3 warnings in 0.71s
```
All 6 tests passed (ffmpeg available, so `test_open_rehydrates_state` ran and passed).

### Full suite `pytest -v`
```
62 passed, 3 warnings in 7.38s
```
All existing tests continue to pass. No regressions.
