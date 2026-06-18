# Task 2 Report: routes.py + pipeline.py Path Migration

## Files Changed

### `app/analyzer/pipeline.py`
- `analyze()` (line 30): `workdir.video_dir(video_id) / "audio.wav"` → `workdir.uploads_dir(video_id) / "audio.wav"`

### `app/api/routes.py`
- `_output_dir()`: `video_dir(id) / "output"` → `video_dir(id) / "clips"` (no auto-create on reads)
- `upload()`: `uuid.uuid4().hex[:12]` → `workdir.make_video_id(file.filename)` for video_id; source + meta written to `uploads_dir(video_id)/`
- `_project_meta()`: source glob and meta.json read from `d / "uploads"` instead of `d`
- `_list_drafts()`: source/signals in `uploads/`, completed check via `clips/highlights.mp4`
- `_list_library()`: completed check via `clips/highlights.mp4`, clip_count from `clips/`
- `rename_project()`: regex widened `{1,40}` → `{1,60}`; meta read/write at `uploads/meta.json`; added `meta_path.parent.mkdir(parents=True, exist_ok=True)`
- `delete_draft()`: regex widened `{1,40}` → `{1,60}`; completed check via `clips/highlights.mp4`
- `open_library_project()`: regex widened `{1,40}` → `{1,60}`; source glob from `(dir / "uploads").glob("source.*")`
- `delete_library_project()`: regex widened `{1,40}` → `{1,60}`
- `export()` job body: `video_dir(id) / "output"` → `workdir.clips_dir(body.video_id)` (auto-creates `clips/`)

### `tests/test_library.py`
- `_make_completed()`: restructured to `d/uploads/` and `d/clips/` with files in correct subfolders
- `_make_draft()`: restructured to `d/uploads/` with source + signals

### `tests/test_drafts.py` (also required — plan did not mention but had old-layout helpers)
- `_make_draft()`: files moved to `d/uploads/`
- `_make_completed()`: restructured to `d/uploads/` and `d/clips/`
- `test_upload_writes_meta_and_appears_in_drafts`: meta_path updated to `uploads/meta.json`

### `tests/test_rename.py` (also required — plan did not mention but had old-layout helpers)
- `_make_draft()`: files moved to `d/uploads/`
- `test_rename_no_existing_meta`: setup uses `uploads/source.mp4`; assertion updated to `d/uploads/meta.json`

## Pytest Commands and Final Output

**Step 1 failure verification** (fixtures updated, routes not yet):
```
.venv/bin/python -m pytest tests/test_library.py -v
Result: 1 failed (test_list_library_returns_only_completed), 5 passed
```

**Step 5 verification** (library + api):
```
.venv/bin/python -m pytest tests/test_library.py tests/test_api.py -v
Result: 12 passed, 3 warnings
```

**Final full-suite run**:
```
.venv/bin/python -m pytest -q
Result: 100 passed, 3 warnings in 9.10s
```

## Self-Review

- All 10 routes.py edits (a)-(j) applied verbatim from the plan.
- `_output_dir` correctly uses `video_dir(id) / "clips"` (not `clips_dir`) so reads/deletes do not auto-create the clips directory.
- Export job uses `clips_dir(body.video_id)` which auto-creates `clips/` on write — correct.
- Traversal guards (`d.resolve().parent != workdir.WORKDIR.resolve()`) retained in `delete_draft` and `delete_library_project`.
- All four validating endpoints widened from `{1,40}` to `{1,60}`.
- `uuid` import in `routes.py` is now unused (was used in the old `upload` for `uuid.uuid4().hex[:12]`). Left in place as the plan's verbatim `upload` implementation does not mention removing it and it causes no test failure.

## Concerns

1. **Plan omitted `test_drafts.py` and `test_rename.py`**: The plan's Step 1 only named `test_library.py`, but `test_drafts.py` and `test_rename.py` had identical old-layout helpers. These required the same fixture updates; without them 6 tests would fail. Applied the equivalent structural change to both files.

2. **Unused `import uuid` in `routes.py`**: The `upload` endpoint no longer calls `uuid.uuid4()` directly (it delegates to `workdir.make_video_id`), leaving `import uuid` unused. Harmless, but a linter would flag it. Removed only if the caller requests cleanup.

3. **Baseline discrepancy**: The plan's Global Constraints state "Baseline before this plan: 95 passed." but Task 1 was already done and the actual baseline entering Task 2 was 100 passed (5 new workdir tests added in Task 1). Final count matches: 100 passed.
