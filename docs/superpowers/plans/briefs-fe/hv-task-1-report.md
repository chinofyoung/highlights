# HV Task 1 Report: Backend Output Endpoints + Tests

## Status: DONE

## Test Summary
47/47 passing, output pristine. All 7 new tests pass; 40 pre-existing tests unaffected.

## Files Changed

### `app/api/routes.py`
- Added `import re` (stdlib, with other imports)
- Added `from app.exporter.ffmpeg import concat_clips`
- Added `_validate_filename(filename)` helper — regex-guards `clip_NNN.mp4` and `highlights.mp4`; raises HTTP 400 otherwise
- Added `_output_dir(video_id)` helper — calls `_require` for 404 guard, returns `workdir.video_dir(id) / "output"`
- Added 4 new endpoints:
  - `GET /api/output/{video_id}` — lists clips + stitched reel
  - `GET /api/output/{video_id}/{filename}` — serves a validated file via FileResponse
  - `DELETE /api/output/{video_id}/{filename}` — deletes clip (re-stitches or removes highlights.mp4 if last) or deletes highlights.mp4 alone
  - `DELETE /api/output/{video_id}` — wipes all clips and highlights.mp4, returns empty listing

### `tests/test_output.py` (new file)
7 tests matching the brief exactly:
- `test_list_output` — verifies 2 clips + stitched after export
- `test_get_clip_file` — verifies file download returns 200
- `test_get_bad_filename_400` — invalid name → 400, valid-but-absent → 404
- `test_delete_clip_restitches` — deleting clip_001 leaves clip_002 + new reel
- `test_delete_last_clip_removes_reel` — deleting all clips removes highlights.mp4
- `test_delete_all` — bulk delete returns `{"clips": [], "stitched": null}`
- `test_unknown_video_404` — unknown video_id returns 404

## Concerns
None. All pre-existing routes and tests are untouched. Warnings in output are pre-existing
FastAPI/httpx deprecations unrelated to this task.
