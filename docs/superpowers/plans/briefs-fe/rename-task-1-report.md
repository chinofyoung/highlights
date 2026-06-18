# Task 1 Report: Backend PATCH /api/projects/{video_id}/name endpoint + test

## Status: DONE

## Changes to routes.py

### Added `RenameBody` model (after `ExportBody`):
```python
class RenameBody(BaseModel):
    name: str
```

### Added PATCH endpoint (inserted before `@router.get("/drafts")`):
```python
@router.patch("/projects/{video_id}/name")
def rename_project(video_id: str, body: RenameBody):
    if not re.fullmatch(r'[A-Za-z0-9_]{1,40}', video_id):
        raise HTTPException(400, "Invalid video_id")
    dir = workdir.WORKDIR / video_id
    if not dir.exists():
        raise HTTPException(404, "Project not found")
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(400, "Name cannot be empty")
    # Truncate at 200 chars (do NOT error — just truncate)
    name = name[:200]
    # Read or create meta
    meta_path = dir / "meta.json"
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
    meta_path.write_text(json.dumps(meta))
    return _project_meta(dir)
```

Key implementation note: Used `workdir.WORKDIR / video_id` directly for the existence check (NOT `workdir.video_dir(video_id)`) because `video_dir()` calls `mkdir(parents=True, exist_ok=True)` and would silently create the directory, defeating the 404 guard.

## New test file: tests/test_rename.py

7 tests covering:
1. `test_rename_success` — 200, correct `original_filename`, has `video_id`
2. `test_rename_reflects_in_drafts` — after rename, GET /api/drafts shows updated name
3. `test_rename_empty_name_400` — whitespace-only name → 400
4. `test_rename_missing_404` — non-existent video_id → 404
5. `test_rename_bad_id_400` — invalid chars in video_id → 400
6. `test_rename_truncates_200` — 210-char name → 200, result length is 200
7. `test_rename_no_existing_meta` — dir with no meta.json → 200, meta written with correct name and float `uploaded_at`

## Full pytest -v output

```
============================= test session starts ==============================
platform darwin -- Python 3.10.8, pytest-9.1.0, pluggy-1.6.0 -- /Users/chinoyoung/Code/highlights/.venv/bin/python3.10
cachedir: .pytest_cache
rootdir: /Users/chinoyoung/Code/highlights
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.14.0
collecting ... collected 69 items

tests/test_api.py::test_full_flow_jobs PASSED                            [  1%]
tests/test_api.py::test_unknown_job_404 PASSED                           [  2%]
tests/test_api.py::test_upload_rejects_non_video PASSED                  [  4%]
tests/test_api.py::test_params_ignores_unknown_keys PASSED               [  5%]
tests/test_api.py::test_cancel_unknown_job_404 PASSED                    [  7%]
tests/test_api.py::test_cancel_sets_status PASSED                        [  8%]
tests/test_audio.py::test_extract_wav_creates_file PASSED                [ 10%]
tests/test_audio.py::test_audio_energy_higher_during_sine PASSED         [ 11%]
tests/test_deps.py::test_ffmpeg_available_returns_bool PASSED            [ 13%]
tests/test_deps.py::test_probe_duration_reads_length PASSED              [ 14%]
tests/test_deps.py::test_probe_duration_rejects_non_video PASSED         [ 15%]
tests/test_drafts.py::test_list_drafts_returns_only_drafts PASSED        [ 17%]
tests/test_drafts.py::test_list_drafts_empty_when_workdir_missing PASSED [ 18%]
tests/test_drafts.py::test_list_drafts_no_meta_uses_fallback PASSED      [ 20%]
tests/test_drafts.py::test_delete_draft_removes_folder PASSED            [ 21%]
tests/test_drafts.py::test_delete_draft_not_found PASSED                 [ 23%]
tests/test_drafts.py::test_delete_draft_invalid_id PASSED                [ 24%]
tests/test_drafts.py::test_delete_draft_invalid_id_dot PASSED            [ 26%]
tests/test_drafts.py::test_delete_completed_draft_returns_409 PASSED     [ 28%]
tests/test_drafts.py::test_upload_writes_meta_and_appears_in_drafts PASSED [ 28%]
tests/test_exporter.py::test_cut_clip_has_expected_duration PASSED       [ 30%]
tests/test_exporter.py::test_export_produces_clips_and_stitch PASSED     [ 31%]
tests/test_exporter.py::test_export_empty_ranges PASSED                  [ 33%]
tests/test_jobs.py::test_create_returns_running_job PASSED               [ 34%]
tests/test_jobs.py::test_update_sets_fields PASSED                       [ 36%]
tests/test_jobs.py::test_get_returns_copy_not_reference PASSED           [ 37%]
tests/test_jobs.py::test_update_unknown_job_is_noop PASSED               [ 39%]
tests/test_jobs.py::test_concurrent_updates_are_safe PASSED              [ 40%]
tests/test_jobs.py::test_create_has_cancelled_false PASSED               [ 42%]
tests/test_jobs.py::test_cancel_sets_cancelled_true PASSED               [ 43%]
tests/test_jobs.py::test_cancel_unknown_is_noop PASSED                   [ 44%]
tests/test_library.py::test_list_library_returns_only_completed PASSED   [ 46%]
tests/test_library.py::test_list_library_empty_when_workdir_missing PASSED [ 47%]
tests/test_library.py::test_delete_library_removes_folder PASSED         [ 49%]
tests/test_library.py::test_delete_library_not_found PASSED              [ 50%]
tests/test_library.py::test_delete_library_invalid_id PASSED             [ 52%]
tests/test_library.py::test_open_rehydrates_state PASSED                 [ 53%]
tests/test_motion.py::test_motion_energy_higher_during_movement PASSED   [ 55%]
tests/test_output.py::test_list_output PASSED                            [ 56%]
tests/test_output.py::test_get_clip_file PASSED                          [ 57%]
tests/test_output.py::test_get_bad_filename_400 PASSED                   [ 59%]
tests/test_output.py::test_delete_clip_restitches PASSED                 [ 60%]
tests/test_output.py::test_delete_last_clip_removes_reel PASSED          [ 62%]
tests/test_output.py::test_delete_all PASSED                             [ 63%]
tests/test_output.py::test_unknown_video_404 PASSED                      [ 65%]
tests/test_pipeline.py::test_save_and_load_signals_roundtrip PASSED      [ 66%]
tests/test_pipeline.py::test_analyze_detects_middle_rally PASSED         [ 68%]
tests/test_pipeline.py::test_resegment_uses_cache PASSED                 [ 69%]
tests/test_progress.py::test_motion_reports_monotonic_progress PASSED    [ 71%]
tests/test_progress.py::test_motion_without_callback_unchanged PASSED    [ 72%]
tests/test_progress.py::test_analyze_reports_progress_ending_at_one PASSED [ 73%]
tests/test_progress.py::test_export_reports_progress PASSED              [ 75%]
tests/test_progress.py::test_export_empty_ranges_no_progress_crash PASSED [ 76%]
tests/test_rename.py::test_rename_success PASSED                         [ 78%]
tests/test_rename.py::test_rename_reflects_in_drafts PASSED              [ 79%]
tests/test_rename.py::test_rename_empty_name_400 PASSED                  [ 81%]
tests/test_rename.py::test_rename_missing_404 PASSED                     [ 82%]
tests/test_rename.py::test_rename_bad_id_400 PASSED                      [ 84%]
tests/test_rename.py::test_rename_truncates_200 PASSED                   [ 85%]
tests/test_rename.py::test_rename_no_existing_meta PASSED                [ 86%]
tests/test_segment.py::test_normalize_constant_is_zeros PASSED           [ 88%]
tests/test_segment.py::test_normalize_scales_to_unit PASSED              [ 89%]
tests/test_segment.py::test_combine_takes_max PASSED                     [ 91%]
tests/test_segment.py::test_segment_finds_single_active_span PASSED      [ 92%]
tests/test_segment.py::test_segment_merges_short_gap PASSED              [ 94%]
tests/test_segment.py::test_segment_drops_short_span PASSED              [ 95%]
tests/test_segment.py::test_segment_applies_padding_and_clamps PASSED    [ 97%]
tests/test_segment.py::test_segment_empty_when_all_quiet PASSED          [ 98%]
tests/test_segment.py::test_combine_and_segment_handle_empty PASSED      [100%]

======================== 69 passed, 3 warnings in 7.48s ========================
```
