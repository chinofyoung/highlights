# Task 2 Report: Frontend — renameProject api, inline rename in both sections, App.tsx fixes, frontend test

## Status: DONE

## Files Changed

1. `/Users/chinoyoung/Code/highlights/frontend/src/api.ts`
   - Added `renameProject(videoId, name)` function at the end: PATCH `/api/projects/{videoId}/name`, throws on non-OK with server detail.

2. `/Users/chinoyoung/Code/highlights/frontend/src/components/DraftsSection.tsx`
   - Full replacement: added `Pencil`, `Check`, `X` imports from lucide-react; `useRef`; `renameProject` from api.
   - New state: `editingId`, `draftName`, `inputRef`.
   - Inline edit mode per card: Pencil button enters edit, Enter/Check saves, Esc/X cancels. On save, updates item in local state without re-fetch.

3. `/Users/chinoyoung/Code/highlights/frontend/src/components/LibrarySection.tsx`
   - Full replacement: same inline rename pattern as DraftsSection.
   - Added `openError` state; `handleOpen` wrapped in try/catch, surfaces error as `text-[var(--danger)] text-sm` paragraph in section header.
   - Confirm-delete dialog and View button kept intact.

4. `/Users/chinoyoung/Code/highlights/frontend/src/App.tsx`
   - Fix 1 (stale exportJob on Back): added `setExportJob(null)` to the Back button onClick handler.
   - Fix 2 (stale state on library open): added `setRallies([])` and `setExportJob(null)` to `handleOpenProject`.

5. `/Users/chinoyoung/Code/highlights/frontend/src/test/api.test.ts`
   - Added two tests after existing `deleteProject` test:
     - `renameProject sends PATCH /api/projects/{id}/name with body`
     - `renameProject throws with server detail on non-OK`

## Build Output

```
> build
> tsc -b && vite build

vite v6.4.3 building for production...
transforming...
✓ 1587 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.75 kB │ gzip:  0.43 kB
dist/assets/index-CEHZa9TT.css   23.15 kB │ gzip:  5.23 kB
dist/assets/index-Dwde8mkg.js   176.61 kB │ gzip: 54.38 kB
✓ built in 1.15s
```

0 TypeScript errors.

## Test Output

```
> test
> vitest run

 RUN  v3.2.6 /Users/chinoyoung/Code/highlights/frontend

 ✓ src/test/timeline-math.test.ts (7 tests) 3ms
 ✓ src/test/api.test.ts (15 tests) 15ms
 ✓ src/test/useJob.test.ts (2 tests) 21ms
 ✓ src/test/SelectedVideo.test.tsx (4 tests) 86ms
 ✓ src/test/App.test.tsx (4 tests) 160ms

 Test Files  5 passed (5)
      Tests  32 passed (32)
   Start at  17:56:33
   Duration  1.48s (transform 605ms, setup 480ms, collect 1.70s, tests 285ms, environment 2.21s, prepare 412ms)
```

32 tests passed (15 in api.test.ts, including the 2 new renameProject tests).
