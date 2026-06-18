# DNR Task 1 Report: Backend — rename re-keys (moves) the project folder

## Files Changed

- `app/workdir.py` — added `unique_video_id(name, current)` function after `make_video_id`
- `app/api/routes.py` — rewrote `rename_project` body (lines 200–224) to move the folder via `shutil.move`, re-key in-memory state, and return `_project_meta(new_dir)`
- `tests/test_rename.py` — appended 3 new tests; reconciled 2 pre-existing tests

## Pytest Commands and Full Output

### Step 2: Verify new tests fail before implementation

```
.venv/bin/python -m pytest tests/test_rename.py -k "moves_folder or collision or same_sanitized" -v

collected 10 items / 7 deselected / 3 selected

tests/test_rename.py::test_rename_moves_folder_and_rekeys_state FAILED   [ 33%]
tests/test_rename.py::test_rename_collision_appends_suffix FAILED        [ 66%]
tests/test_rename.py::test_rename_same_sanitized_name_no_move PASSED     [100%]

2 failed, 1 passed (test_rename_same_sanitized_name_no_move already passed because
the old code happened to work for the no-move case)
```

### Step 5: All rename tests after implementation

```
.venv/bin/python -m pytest tests/test_rename.py -v

10 passed, 3 warnings in 0.33s
```

### Step 6: Full suite

```
.venv/bin/python -m pytest -q

104 passed, 3 warnings in 8.21s
```

## Pre-existing Tests Reconciled

Two pre-existing tests broke after the rename started moving folders:

### 1. `test_rename_reflects_in_drafts` (line 33)

**Why it broke:** The test renamed `vid_abc` to `"My Final Cut"`. With the new code the folder moves to `My_Final_Cut` (slugified). The test then looked for `video_id == "vid_abc"` in the drafts list — that entry is gone.

**Fix:** Capture the returned `video_id` from the PATCH response (`new_id = r_rename.json()["video_id"]`) and use that to find the item in the drafts list. The assertion strength is unchanged — still verifies `original_filename == "My Final Cut"` and that the item exists in the list.

### 2. `test_rename_no_existing_meta` (line 97)

**Why it broke:** Renamed `vid_nometa` to `"No Meta Name"`. Slugified to `No_Meta_Name`, folder moved. The test then checked `d / "uploads" / "meta.json"` where `d` still pointed to the original `vid_nometa` path.

**Fix:** Use `tmp_path / data["video_id"] / "uploads" / "meta.json"` (the returned `video_id` determines the actual folder location). All assertions about `original_filename` and `uploaded_at` are unchanged.

## Self-Review

- `unique_video_id` correctly returns `current` when the sanitized base equals `current` (no spurious `_2` suffix when name hasn't changed slug).
- The collision loop correctly skips the `current` folder itself — so renaming "My_Match" to "My Match" when `My_Match` already exists doesn't collide with itself.
- `shutil.move` is already imported in `routes.py`.
- State re-key handles the case where no state entry exists (no `put` if `info is None`).
- The `source.*` glob for the new path update is defensive — if no source file found, original path is kept.
- `_project_meta` derives `video_id` from `d.name`, so returning `_project_meta(new_dir)` naturally yields the new id.

## Concerns

None. Implementation is straightforward and all 104 tests pass.
