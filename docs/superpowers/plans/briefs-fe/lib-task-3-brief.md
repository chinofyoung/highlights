# Task 3: LibrarySection component + App.tsx integration

## Context
Pickleball highlights app. Frontend React+TS+Tailwind in `/Users/chinoyoung/Code/highlights/frontend/`.

**IMPORTANT**: Task 2 already added `Project` to `types.ts` and `listLibrary`/`openProject`/`deleteProject` to `api.ts`. Read these files before starting.

Key files to read first:
- `/Users/chinoyoung/Code/highlights/frontend/src/App.tsx` — modify this
- `/Users/chinoyoung/Code/highlights/frontend/src/api.ts` — has the new library functions
- `/Users/chinoyoung/Code/highlights/frontend/src/types.ts` — has Project interface
- `/Users/chinoyoung/Code/highlights/frontend/src/components/DraftsSection.tsx` — reference component pattern
- `/Users/chinoyoung/Code/highlights/frontend/src/components/HighlightsView.tsx` — used in library-view
- `/Users/chinoyoung/Code/highlights/frontend/src/test/App.test.tsx` — existing tests; must stay green

## Step 1: Create `frontend/src/components/LibrarySection.tsx`

Props: `{ onOpen: (videoId: string, duration: number) => void }`

Behavior:
- On mount: call `listLibrary()` → set state; if empty return `null` (render nothing)
- Heading: "Library" + count, same style as DraftsSection's "Unfinished drafts (N)"
- Each project card (same card layout as DraftsSection):
  - `original_filename` (font-display, truncate)
  - Mono detail line: `new Date(p.uploaded_at * 1000).toLocaleDateString()` · `(p.size_bytes/1e6).toFixed(1) MB` · `p.clip_count clips`
  - **View** button: `bg-[var(--accent)] text-[var(--ink)]` (or use teal: `bg-[var(--teal)] text-white`). On click: `const r = await openProject(p.video_id); onOpen(r.video_id, r.duration);`
  - **Delete** button: lucide `Trash2` icon (size=14), `text-[var(--muted)] hover:text-[var(--danger)]`. On click: opens confirm dialog.

**Delete confirmation dialog** (accessible inline modal):
- Overlay: `fixed inset-0 bg-black/50 z-50 flex items-center justify-center`
- Dialog box: `role="dialog"`, `aria-modal="true"`, `aria-labelledby` pointing to title
- Title: project `original_filename`
- Body: "Removes the video, clips, and reel. This can't be undone."
- Buttons: "Cancel" (close dialog) and "Delete" (calls `deleteProject(p.video_id)`, sets list to result, closes dialog)
- Use design tokens: `bg-[var(--surface)]`, `border-[var(--line)]`, `text-[var(--ink)]`, Delete button `bg-[var(--danger)] text-white`

State to manage: `projects`, `confirmDeleteId: string | null` (which project is pending delete confirmation)

## Step 2: Modify `App.tsx`

**Add imports**:
```typescript
import { LibrarySection } from "./components/LibrarySection";
```

**Add state** (alongside existing state):
```typescript
const [libraryView, setLibraryView] = useState(false);
```

**Add handler** `handleOpenProject`:
```typescript
function handleOpenProject(videoId: string, duration: number) {
  setVideoId(videoId);
  setDuration(duration);
  setLibraryView(true);
}
```

**Landing view** — add LibrarySection alongside DraftsSection:
```tsx
{!selectedFile && !videoId && (
  <>
    <UploadView onFile={handleFileSelected} error={uploadError} />
    <DraftsSection />
    <LibrarySection onOpen={handleOpenProject} />
  </>
)}
```

**Library-view screen** — new conditional block before the review block. Place it AFTER the detecting block (View 3) and before or replacing View 4 for the library case:
```tsx
{libraryView && videoId && (
  <>
    <div className="flex items-center gap-3">
      <button
        onClick={() => { setVideoId(null); setLibraryView(false); setRallies([]); }}
        className="rounded border border-[var(--line)] px-3 py-1.5 text-sm text-[var(--muted)] hover:text-[var(--ink)] transition-colors"
      >
        ← Back
      </button>
      <button
        onClick={async () => {
          const { rallies: rs } = await api.resegment(videoId, { threshold: 1 - sensitivity });
          setRallies(rs.map(r => ({ ...r, included: true })));
          setLibraryView(false);
        }}
        className="rounded bg-[var(--teal)] px-3 py-1.5 text-sm text-white hover:opacity-90 transition-opacity"
      >
        Re-edit
      </button>
    </div>
    <HighlightsView videoId={videoId} />
  </>
)}
```

**Review block (View 4)** — add `!libraryView` guard so it doesn't show when in library-view:
```tsx
{videoId && !libraryView && !detectJob && !analyzing && (
  ...existing review UI...
)}
```

**Key constraints**:
- `libraryView` is ONLY set to true in `handleOpenProject` (library flow)
- Normal upload→detect→review→export flow: `libraryView` stays `false` throughout; after export `exp.status === "done"` shows `HighlightsView` from within the review block (unchanged behavior)
- No phase should render two screens at once; `libraryView` takes priority for the library-opened video
- The `Back` button: `setVideoId(null); setLibraryView(false); setRallies([]);` — returns to landing
- Re-edit: calls `resegment`, sets rallies, sets `libraryView(false)` → falls into existing review UI (View 4)

## Step 3: Fix App.test.tsx

The App test's `vi.mock("../api", ...)` block needs `listLibrary` mocked (since `LibrarySection` now calls it on mount). Add to the mock:
```typescript
listLibrary: vi.fn().mockResolvedValue([]),
deleteProject: vi.fn().mockResolvedValue([]),
openProject: vi.fn(),
```
Also add to `beforeEach`:
```typescript
vi.mocked(api.listLibrary).mockResolvedValue([]);
```
The `api` import in the test is `import * as api from "../api"` — you need to add these to both the `vi.mock` factory and the `beforeEach` reset.

## Verification

```bash
npm run build 2>&1 | tail -20
npm run test 2>&1 | tail -30
```
Zero TS errors. All tests pass (including existing App tests).

## Report file
Write your full report to: `/Users/chinoyoung/code/highlights/docs/superpowers/plans/briefs-fe/lib-task-3-report.md`

Include: files created/modified, build output, test output.

Return as your final message: STATUS (DONE/DONE_WITH_CONCERNS/NEEDS_CONTEXT/BLOCKED), one line on changes, one line on test results.
