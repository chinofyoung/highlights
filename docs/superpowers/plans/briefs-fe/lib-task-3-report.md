# Task 3 Report: LibrarySection component + App.tsx integration

## Files Created

### `frontend/src/components/LibrarySection.tsx` (new)
- Props: `{ onOpen: (videoId: string, duration: number) => void }`
- Fetches `listLibrary()` on mount; returns `null` if empty
- Renders a "Library (N)" section heading matching DraftsSection style
- Each project card shows: `original_filename` (font-display, truncate), mono detail line with `toLocaleDateString()` · MB · clips count
- **View** button: `bg-[var(--teal)] text-white`, calls `openProject(p.video_id)` then `onOpen(r.video_id, r.duration)`
- **Delete** button: `Trash2` icon (size=14), `text-[var(--muted)] hover:text-[var(--danger)]`, sets `confirmDeleteId`
- **Delete confirmation dialog**: accessible modal with `role="dialog"`, `aria-modal="true"`, `aria-labelledby` pointing to title; uses design tokens; Cancel/Delete buttons; Delete calls `deleteProject` and updates list

## Files Modified

### `frontend/src/App.tsx`
- Added import: `import { LibrarySection } from "./components/LibrarySection";`
- Added state: `const [libraryView, setLibraryView] = useState(false);`
- Added handler `handleOpenProject(videoId, duration)` — sets videoId, duration, libraryView=true
- Landing view (View 1): added `<LibrarySection onOpen={handleOpenProject} />` after DraftsSection
- Added new View 4a block: `{libraryView && videoId && ...}` renders Back + Re-edit buttons and `<HighlightsView videoId={videoId} />`
  - Back button: resets videoId, libraryView, rallies
  - Re-edit button: calls `api.resegment`, sets rallies, sets libraryView=false → drops into review UI
- Added `!libraryView` guard to View 4 review block: `{videoId && !libraryView && !detectJob && !analyzing && ...}`

### `frontend/src/test/App.test.tsx`
- Added to `vi.mock("../api", ...)` factory: `listLibrary`, `deleteProject`, `openProject`
- Added to `beforeEach` reset: `vi.mocked(api.listLibrary).mockResolvedValue([])`

## Build Output

```
vite v6.4.3 building for production...
✓ 1587 modules transformed.
dist/index.html                   0.75 kB │ gzip:  0.43 kB
dist/assets/index-COILnmT8.css   22.55 kB │ gzip:  5.14 kB
dist/assets/index-JjR3DTqm.js   172.15 kB │ gzip: 53.56 kB
✓ built in 906ms
```

Zero TypeScript errors.

## Test Output

```
 ✓ src/test/timeline-math.test.ts (7 tests) 5ms
 ✓ src/test/api.test.ts (13 tests) 16ms
 ✓ src/test/useJob.test.ts (2 tests) 19ms
 ✓ src/test/SelectedVideo.test.tsx (4 tests) 109ms
 ✓ src/test/App.test.tsx (4 tests) 132ms

 Test Files  5 passed (5)
      Tests  30 passed (30)
```

All 30 tests pass.
