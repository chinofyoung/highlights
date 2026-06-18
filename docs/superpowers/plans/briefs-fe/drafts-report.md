# Drafts Feature — Implementation Report

## Summary

Implemented: list + delete drafts (Parts A, B, C), DraftsSection UI, HighlightsView error fix, and ffmpeg cleanup fix. All tests pass.

---

## Part A — meta.json on upload

**File changed:** `app/api/routes.py`

After `state.put(video_id, ...)` on the success path (probe passed), the upload handler now writes:

```python
(workdir.video_dir(video_id) / "meta.json").write_text(
    json.dumps({"original_filename": file.filename or "video", "uploaded_at": time.time()})
)
```

This runs only on success — the `HTTPException(400)` branch is raised before this line. Imports added: `json`, `time`, `shutil`.

---

## Part B — Drafts endpoints

**File changed:** `app/api/routes.py`

### Draft definition

A folder under `workdir.WORKDIR` is a **draft** iff:
- `has_source`: at least one file matching `source.*` exists in the directory.
- NOT `completed`: `(dir / "output" / "highlights.mp4")` does NOT exist.

Completed videos (exported highlights) are excluded. Dirs with no source file are excluded.

### GET /api/drafts

Implemented via `_list_drafts()` helper (reused by DELETE). Scans `workdir.WORKDIR` iterdir. For each draft:
- `analyzed`: `(dir / "signals.npz").exists()`
- `original_filename` + `uploaded_at`: from `meta.json` if present; fallback to source file's name + dir mtime.
- `size_bytes`: recursive sum via `dir.rglob("*")`.
- Returns list sorted by `uploaded_at` DESC.
- Returns `[]` if `workdir.WORKDIR` doesn't exist.

### DELETE /api/drafts/{video_id}

Path safety: `re.fullmatch(r'[A-Za-z0-9_]{1,40}', video_id)` — rejects dots, `!`, special chars. Note: regex extended to allow `_` (underscores appear in test IDs). Resolves `dir.resolve().parent == workdir.WORKDIR.resolve()` before `shutil.rmtree`. Returns updated drafts list.

---

## Part C — DraftsSection frontend

### types.ts
Added:
```typescript
export interface Draft {
  video_id: string;
  original_filename: string;
  uploaded_at: number;
  analyzed: boolean;
  size_bytes: number;
}
```

### api.ts
Added `listDrafts()` (GET `/api/drafts`) and `deleteDraft(videoId)` (DELETE `/api/drafts/${videoId}`), both throwing on non-OK with server detail — consistent pattern with other API clients.

### DraftsSection.tsx (new)
- Fetches `listDrafts()` on mount; renders `null` if empty (self-hiding).
- Each draft card shows: filename (font-display), upload date (toLocaleString), size (font-mono, MB), status pill ("Analyzed" / "Uploaded" based on `analyzed`).
- Delete button: `Trash2` icon, `text-[var(--muted)] hover:text-[var(--danger)]`.
- On delete: calls `deleteDraft(video_id)`, sets state to returned list.
- Styled secondary to main CTA using `--surface`, `--line`, `--muted` tokens.

### App.tsx
View 1 (`!selectedFile && !videoId`) now renders `<DraftsSection />` below `<UploadView>`, wrapped in a fragment. Other phases untouched.

---

## Part D — Two small fixes

### D1 — ffmpeg.py concat_clips cleanup

**File changed:** `app/exporter/ffmpeg.py`

Wrapped the `subprocess.run(...)` call in `try: ... finally: listfile.unlink(missing_ok=True)` so the temp `.txt` list file is removed even when ffmpeg fails (previously only cleaned on success path). Return value and behavior unchanged.

### D2 — HighlightsView.tsx error handling

**File changed:** `frontend/src/components/HighlightsView.tsx`

Added `fetchError` state. `useEffect` now calls `.catch((e) => setFetchError(...))` instead of swallowing errors. A `<p className="text-sm text-[var(--danger)]">` renders the error message above the highlights section.

---

## New tests

### Backend — `tests/test_drafts.py`

7 tests total:
- `test_list_drafts_returns_only_drafts` — confirms `vid_draft` appears, `vid_done` does not; checks `original_filename`, `analyzed`, `uploaded_at`.
- `test_list_drafts_empty_when_workdir_missing` — returns `[]` gracefully.
- `test_list_drafts_no_meta_uses_fallback` — uses source filename and mtime when no meta.json.
- `test_delete_draft_removes_folder` — 200, folder gone, returned list excludes it.
- `test_delete_draft_not_found` — 404.
- `test_delete_draft_invalid_id` (`bad!id`) — 400.
- `test_delete_draft_invalid_id_dot` (`bad.id`) — 400.
- `test_upload_writes_meta_and_appears_in_drafts` (`@requires_ffmpeg`) — real upload writes meta.json with correct filename, video appears in GET /api/drafts.

### Frontend — `src/test/api.test.ts`

2 new tests added:
- `listDrafts hits GET /api/drafts` — asserts method + URL.
- `deleteDraft sends DELETE and returns updated list` — asserts method + URL.

`App.test.tsx` was updated to mock `listDrafts`/`deleteDraft` so `DraftsSection` doesn't throw during App mount tests.

---

## Test results

### Backend: `pytest -v`
```
======================== 55 passed, 3 warnings in 7.58s ========================
```

### Frontend: `npm run build && npm run test`
```
vite v6.4.3 building for production...
✓ built in 1.33s
 Test Files  5 passed (5)
      Tests  27 passed (27)
   Duration  1.65s
```

---

## Safety Fix + Test Hygiene — 2026-06-17

### Fix 1: DELETE /api/drafts/{video_id} — 409 guard for completed folders

**Change:** Added a check in `delete_draft` (`app/api/routes.py`) before `shutil.rmtree`:
if `(dir / "output" / "highlights.mp4").exists()` → raise `HTTPException(409, "Not a draft (already exported)")`.

**New test:** `test_delete_completed_draft_returns_409` appended to `tests/test_drafts.py`.
- Constructs a completed folder (source.mp4 + output/highlights.mp4) via existing `_make_completed` helper.
- DELETE → expects 409 with "already exported" in detail.
- Asserts folder still exists on disk (rmtree was not called).

**Backend test output:**
```
tests/test_drafts.py::test_list_drafts_returns_only_drafts PASSED
tests/test_drafts.py::test_list_drafts_empty_when_workdir_missing PASSED
tests/test_drafts.py::test_list_drafts_no_meta_uses_fallback PASSED
tests/test_drafts.py::test_delete_draft_removes_folder PASSED
tests/test_drafts.py::test_delete_draft_not_found PASSED
tests/test_drafts.py::test_delete_draft_invalid_id PASSED
tests/test_drafts.py::test_delete_draft_invalid_id_dot PASSED
tests/test_drafts.py::test_delete_completed_draft_returns_409 PASSED
tests/test_drafts.py::test_upload_writes_meta_and_appears_in_drafts PASSED
======================== 9 passed, 3 warnings in 0.50s =========================
Full suite: 56 passed, 3 warnings in 8.14s
```

### Fix 2: React act() warning in App.test.tsx

**Change:** Added `act` to `@testing-library/react` import; added `await act(async () => {})` after each `render(<App />)` call in all four tests (first test made async); added `vi.mocked(api.listDrafts).mockResolvedValue([])` and `vi.mocked(api.deleteDraft).mockResolvedValue([])` in `beforeEach` after `vi.clearAllMocks()` so mocks survive between tests.

**Result:** act() warning absent — no `Warning: An update to ... inside a test was not wrapped in act` in output.

**Frontend test output:**
```
Test Files  5 passed (5)
      Tests  27 passed (27)
   Duration  1.32s
npm run build: 0 TypeScript errors
```

---

## Files changed

| File | Change |
|------|--------|
| `app/api/routes.py` | meta.json write on upload; `_list_drafts()`; GET `/api/drafts`; DELETE `/api/drafts/{video_id}`; added imports |
| `app/exporter/ffmpeg.py` | try/finally in `concat_clips` |
| `tests/test_drafts.py` | new — 8 tests (7 unit + 1 ffmpeg) |
| `frontend/src/types.ts` | `Draft` interface |
| `frontend/src/api.ts` | `listDrafts`, `deleteDraft` |
| `frontend/src/components/DraftsSection.tsx` | new component |
| `frontend/src/components/HighlightsView.tsx` | error state + display |
| `frontend/src/App.tsx` | DraftsSection import + render in View 1 |
| `frontend/src/test/api.test.ts` | 2 new API tests |
| `frontend/src/test/App.test.tsx` | mock updated for new API functions |
