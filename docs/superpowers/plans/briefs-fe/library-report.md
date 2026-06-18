# Library Feature — Implementation Report

## Backend Endpoints

### `GET /api/library`
Scans `workdir.WORKDIR` subdirs; includes only completed projects (`output/highlights.mp4` exists). Returns list of `{video_id, original_filename, uploaded_at, size_bytes, clip_count}` sorted by `uploaded_at` DESC. Empty list if WORKDIR missing.

### `POST /api/library/{video_id}/open` (rehydrate)
Validates `video_id` with `re.fullmatch(r'[A-Za-z0-9_]{1,40}', ...)` → 400 on fail. Looks up `workdir.video_dir(video_id)` → 404 if missing. Finds `source.*` via glob → 404 if absent. Calls `probe_duration(str(source))` → 400 on ValueError. Writes `state.put(video_id, {"path": ..., "duration": ...})`. Returns `{video_id, duration}`.

After a process restart, calling open rehydrates in-memory state so `GET /api/video/{id}` and `POST /api/resegment` both work using the cached `signals.npz`.

### `DELETE /api/library/{video_id}`
Same regex + 400 guard. Path-safety: `dir.resolve().parent == workdir.WORKDIR.resolve()` else 400. `shutil.rmtree(dir)`. `state._REGISTRY.pop(video_id, None)`. Returns updated library list (same shape as GET).

### `_project_meta` helper
Extracted from `_list_drafts` internals: reads `meta.json` for `original_filename` and `uploaded_at` (with fallbacks to source filename and `st_mtime`), computes `size_bytes` via `rglob`. Used by both `_list_drafts` and `_list_library`.

---

## LibrarySection + Confirm Dialog

`frontend/src/components/LibrarySection.tsx`:
- On mount: `listLibrary()` → state; returns `null` if empty.
- Heading "Library (N)" matching DraftsSection style.
- Each card: `original_filename` (font-display), mono detail line with `toLocaleDateString()` · size in MB · clip count.
- **View** button: `bg-[var(--teal)]`, calls `openProject(p.video_id)` then `onOpen(r.video_id, r.duration)`.
- **Delete** button: lucide `Trash2` size=14, `text-[var(--muted)] hover:text-[var(--danger)]`. Sets `confirmDeleteId`.
- **Confirm dialog**: `fixed inset-0 bg-black/50 z-50` overlay; inner `role="dialog" aria-modal="true" aria-labelledby="delete-dialog-title"` panel with project name as title, body text "Removes the video, clips, and reel. This can't be undone.", Cancel + Delete buttons. Delete calls `deleteProject(p.video_id)` → sets list to result. Clicking overlay dismisses. All tokens: `var(--surface)`, `var(--line)`, `var(--ink)`, `var(--muted)`, `var(--danger)`.

---

## App.tsx View-Mode Transitions

New state: `const [libraryView, setLibraryView] = useState(false)`.

### Landing (`!selectedFile && !videoId`)
Renders `<UploadView>` + `<DraftsSection>` + `<LibrarySection onOpen={handleOpenProject} />`.

### `handleOpenProject(videoId, duration)`
```ts
setVideoId(videoId); setDuration(duration); setLibraryView(true);
```
Does NOT start detect. Falls into the library-view screen.

### Library-view screen (`libraryView && videoId`)
Renders a header row with:
- **Back** button: `setVideoId(null); setLibraryView(false); setRallies([]);` → returns to landing.
- **Re-edit** button: `await api.resegment(videoId, {...}); setRallies(...); setLibraryView(false);` → falls into review UI.

Followed by `<HighlightsView videoId={videoId} />`.

### Review block (View 4)
Guard changed to `videoId && !libraryView && !detectJob && !analyzing` so library-view and review never render simultaneously.

### Normal flow (unchanged)
Upload → analyze → detect job → review → export → `exp.status === "done"` → `<HighlightsView>` inside review block. `libraryView` stays `false` throughout.

No phase renders two screens at once: `libraryView` takes precedence for the library-opened video; the review block's `!libraryView` guard ensures separation.

---

## New Tests

### `tests/test_library.py` (6 tests)
1. `test_list_library_returns_only_completed` — completed project with 2 clips + draft dir; GET returns only completed with `clip_count==2`, `original_filename=="game.mp4"`, `uploaded_at==200.0`.
2. `test_list_library_empty_when_workdir_missing` — missing WORKDIR → `[]`.
3. `test_delete_library_removes_folder` — DELETE removes dir on disk, returns empty list.
4. `test_delete_library_not_found` — DELETE missing → 404.
5. `test_delete_library_invalid_id` — DELETE `bad!id` → 400.
6. `@requires_ffmpeg test_open_rehydrates_state` — full upload→detect→export flow; clears state; POST open → 200 with `duration>0`; GET video → 200; POST resegment → 200 with `rallies` list.

### `frontend/src/test/api.test.ts` (3 new tests, 13 total)
- `listLibrary` hits GET /api/library and returns array.
- `openProject` sends POST /api/library/{id}/open and returns `{video_id, duration}`.
- `deleteProject` sends DELETE /api/library/{id} and returns updated list.

### `frontend/src/test/App.test.tsx` (unchanged count, 4 tests)
Added `listLibrary`, `openProject`, `deleteProject` to `vi.mock` factory and `beforeEach` reset so LibrarySection's mount effect is mocked. All existing "no-auto-analyze" tests pass unchanged.

---

## Test Results

### Backend: `pytest -v`
```
62 passed, 3 warnings in 7.81s
```

### Frontend: `npm run build`
```
✓ 1587 modules transformed.
dist/assets/index-JjR3DTqm.js  172.15 kB │ gzip: 53.56 kB
✓ built in 975ms
```
Zero TypeScript errors.

### Frontend: `npm run test`
```
✓ src/test/timeline-math.test.ts  (7 tests)
✓ src/test/api.test.ts           (13 tests)
✓ src/test/useJob.test.ts         (2 tests)
✓ src/test/SelectedVideo.test.tsx (4 tests)
✓ src/test/App.test.tsx           (4 tests)

Test Files  5 passed (5)
     Tests  30 passed (30)
  Duration  1.12s
```

---

## Concerns
None. All spec requirements met. Path-safety, input validation, and accessibility (role/aria) are in place.
