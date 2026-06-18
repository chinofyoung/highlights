# Task 1 Brief: Backend PATCH /api/projects/{video_id}/name endpoint + test

## Objective
Add a rename endpoint to the FastAPI backend and write a full test suite for it.

## File to modify
- `/Users/chinoyoung/code/highlights/app/api/routes.py` — add the new endpoint
- `/Users/chinoyoung/code/highlights/tests/test_rename.py` — new test file

## Backend endpoint spec

Add a Pydantic body model right after the existing models section:

```python
class RenameBody(BaseModel):
    name: str
```

Add the endpoint handler (insert before the `@router.get("/drafts")` route):

```python
@router.patch("/projects/{video_id}/name")
def rename_project(video_id: str, body: RenameBody):
    if not re.fullmatch(r'[A-Za-z0-9_]{1,40}', video_id):
        raise HTTPException(400, "Invalid video_id")
    dir = workdir.video_dir(video_id)
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

Key rules:
- `video_id` validated with `re.fullmatch(r'[A-Za-z0-9_]{1,40}', video_id)` → 400 if invalid
- `dir = workdir.video_dir(video_id)` — do NOT use `workdir.WORKDIR / video_id` directly
- If dir doesn't exist → 404
- Strip the name; if empty → 400 "Name cannot be empty"
- Truncate to 200 chars (do NOT raise on length)
- Read existing meta.json if present (fallback to `{}`); set `original_filename = name`; if no `uploaded_at`, set from dir mtime; write back
- Return `_project_meta(dir)` — this includes `video_id`, `original_filename`, `uploaded_at`, `size_bytes`

## Test file spec

File: `/Users/chinoyoung/code/highlights/tests/test_rename.py`

The test file must follow the same pattern as `test_drafts.py` — use `monkeypatch` to set `workdir.WORKDIR = tmp_path`.

Helper to create a draft folder (has source + signals, NO output/highlights.mp4):
```python
def _make_draft(tmp_path, video_id, filename="orig.mp4", uploaded_at=100.0):
    d = tmp_path / video_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "source.mp4").write_bytes(b"x")
    (d / "signals.npz").write_bytes(b"x")
    (d / "meta.json").write_text(json.dumps({
        "original_filename": filename,
        "uploaded_at": uploaded_at,
    }))
    return d
```

Required tests:

1. `test_rename_success` — patch with `{"name": "My Final Cut"}` → 200, response `original_filename == "My Final Cut"`, response has `video_id`
2. `test_rename_reflects_in_drafts` — after rename, `GET /api/drafts` returns item with `original_filename == "My Final Cut"`
3. `test_rename_empty_name_400` — patch with `{"name": "   "}` → 400
4. `test_rename_missing_404` — patch `/api/projects/missing/name` → 404
5. `test_rename_bad_id_400` — patch `/api/projects/bad!id/name` → 400
6. `test_rename_truncates_200` — patch with a name 210 chars long → 200, `original_filename` has length 200
7. `test_rename_no_existing_meta` — dir exists with source but NO meta.json, patch → 200, meta.json written with correct name and `uploaded_at` set to dir mtime (float)

## workdir.video_dir — CRITICAL NOTE

`video_dir(video_id)` in `workdir.py` calls `mkdir(parents=True, exist_ok=True)` — it creates the directory if it doesn't exist. So you MUST check existence BEFORE calling `video_dir`. Use:

```python
dir = workdir.WORKDIR / video_id
if not dir.exists():
    raise HTTPException(404, "Project not found")
```

Do NOT call `workdir.video_dir(video_id)` for the existence check — it would silently create the dir. After the existence check, you can use `dir` directly (it's already the resolved path).

## Run tests

After implementing, run:
```bash
cd /Users/chinoyoung/code/highlights && source .venv/bin/activate && pytest tests/test_rename.py -v
```

Then run the full suite:
```bash
pytest -v
```

## Report

Write your report to: `/Users/chinoyoung/Code/highlights/docs/superpowers/plans/briefs-fe/rename-task-1-report.md`

Include: what you changed in routes.py, the new test file summary, and the full pytest -v output.

Return: STATUS (DONE/BLOCKED/NEEDS_CONTEXT), one-line test summary.
