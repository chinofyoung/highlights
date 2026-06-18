# Rename Feature — Implementation Report

## Status: COMPLETE. All tests green.

---

## Backend: PATCH /api/projects/{video_id}/name

**File:** `app/api/routes.py`

### Pydantic model added
```python
class RenameBody(BaseModel):
    name: str
```

### Endpoint added (before `@router.get("/drafts")`)
```python
@router.patch("/projects/{video_id}/name")
def rename_project(video_id: str, body: RenameBody):
    if not re.fullmatch(r'[A-Za-z0-9_]{1,40}', video_id):
        raise HTTPException(400, "Invalid video_id")
    dir = workdir.WORKDIR / video_id          # direct, NOT video_dir() — avoids implicit mkdir
    if not dir.exists():
        raise HTTPException(404, "Project not found")
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(400, "Name cannot be empty")
    name = name[:200]                          # truncate, do not 400
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

**Key implementation note:** `workdir.video_dir()` calls `mkdir(parents=True, exist_ok=True)`, so the existence check uses `workdir.WORKDIR / video_id` directly to avoid silently creating the dir before the 404 guard.

---

## Backend Tests: `tests/test_rename.py`

7 tests, all passing:

| Test | Coverage |
|------|----------|
| `test_rename_success` | 200, `original_filename` updated, `video_id` present in response |
| `test_rename_reflects_in_drafts` | GET /api/drafts returns item with new name after rename |
| `test_rename_empty_name_400` | whitespace-only name → 400 |
| `test_rename_missing_404` | non-existent video_id → 404 |
| `test_rename_bad_id_400` | `bad!id` → 400 |
| `test_rename_truncates_200` | 210-char name → 200, result length exactly 200 |
| `test_rename_no_existing_meta` | dir without meta.json → 200, meta written with correct name and float `uploaded_at` |

---

## Frontend

### `frontend/src/api.ts`
Added:
```typescript
export async function renameProject(
  videoId: string,
  name: string,
): Promise<{ video_id: string; original_filename: string }> {
  const r = await fetch(`/api/projects/${videoId}/name`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!r.ok) {
    const detail = (await r.json().catch(() => ({}))).detail;
    throw new Error(detail || r.statusText);
  }
  return r.json();
}
```

### `frontend/src/components/DraftsSection.tsx`
- Added `Pencil`, `Check`, `X` from lucide-react; `useRef`; `renameProject` from api
- New state: `editingId: string | null`, `draftName: string`, `inputRef`
- Per-card inline rename: Pencil icon enters edit mode (focuses input via `useEffect`), Enter/Check saves, Esc/X cancels
- On save: trims name, cancels if empty (no API call); otherwise calls `renameProject`, updates that item's `original_filename` in local state
- Existing delete button and `handleDelete` unchanged

### `frontend/src/components/LibrarySection.tsx`
- Same inline rename pattern as DraftsSection (`editingId`, `editName`, `inputRef`)
- Added `openError: string | null` state; `handleOpen` wrapped in try/catch, surfaces error as `<p className="text-sm text-[var(--danger)]">` in section
- View button, confirm-delete modal, and `handleDelete` unchanged

### `frontend/src/App.tsx` — two fixes

**Fix 1 (stale exportJob — Back button):**
```tsx
// Before
onClick={() => { setVideoId(null); setLibraryView(false); setRallies([]); }}
// After
onClick={() => { setVideoId(null); setLibraryView(false); setRallies([]); setExportJob(null); }}
```

**Fix 2 (stale exportJob + rallies — handleOpenProject):**
```typescript
// Before
function handleOpenProject(videoId: string, duration: number) {
  setVideoId(videoId);
  setDuration(duration);
  setLibraryView(true);
}
// After
function handleOpenProject(videoId: string, duration: number) {
  setVideoId(videoId);
  setDuration(duration);
  setRallies([]);
  setExportJob(null);
  setLibraryView(true);
}
```

### `frontend/src/test/api.test.ts`
Added two tests:
- `renameProject sends PATCH /api/projects/{id}/name with body` — verifies method, URL, headers, body, and response shape
- `renameProject throws with server detail on non-OK` — verifies error propagation

---

## Test Results

### Backend: `pytest -v`
```
69 passed, 3 warnings in 7.42s
```
All 7 rename tests + all 62 pre-existing tests passed.

### Frontend: `npm run build && npm run test`
```
Build: 0 TypeScript errors, ✓ built in 903ms

Tests:
  ✓ src/test/timeline-math.test.ts (7 tests)
  ✓ src/test/api.test.ts (15 tests)   ← includes 2 new renameProject tests
  ✓ src/test/useJob.test.ts (2 tests)
  ✓ src/test/SelectedVideo.test.tsx (4 tests)
  ✓ src/test/App.test.tsx (4 tests)

Test Files  5 passed (5)
     Tests  32 passed (32)
```

---

## Files Changed

| File | Change |
|------|--------|
| `app/api/routes.py` | Added `RenameBody` model + `PATCH /projects/{video_id}/name` endpoint |
| `tests/test_rename.py` | New file — 7 tests |
| `frontend/src/api.ts` | Added `renameProject` function |
| `frontend/src/components/DraftsSection.tsx` | Full rewrite — inline rename UX |
| `frontend/src/components/LibrarySection.tsx` | Full rewrite — inline rename UX + `openError` |
| `frontend/src/App.tsx` | Two targeted fixes — `setExportJob(null)` in Back + `handleOpenProject` |
| `frontend/src/test/api.test.ts` | Added 2 new `renameProject` tests |
