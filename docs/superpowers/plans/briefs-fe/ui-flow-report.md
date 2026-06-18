# UI Flow Improvements — Implementation Report

## Files Created / Modified

| Path | Action | Summary |
|---|---|---|
| `frontend/src/components/UploadView.tsx` | Modified | Added `dragActive` state + drag event handlers; dynamic border/bg on drag |
| `frontend/src/components/SelectedVideo.tsx` | Created | Video preview, file name/size, Analyze + Reset buttons; `analyzing` busy state |
| `frontend/src/components/BallLoader.tsx` | Created | 32×32 optic-lime ball with `.ball-bounce` CSS animation; `aria-hidden` |
| `frontend/src/index.css` | Modified | Added `@keyframes ball-bounce` (motion-ok) + `@keyframes ball-pulse` (reduced-motion fallback) + `.ball-bounce` class |
| `frontend/src/App.tsx` | Modified | Added `selectedFile` + `analyzing` state; view-gating; deferred analyze logic |
| `frontend/src/test/SelectedVideo.test.tsx` | Created | 4 unit tests for SelectedVideo component |
| `frontend/src/test/App.test.tsx` | Created | 4 integration tests — no-auto-analyze contract |
| `frontend/src/test/setup.ts` | Modified | Added `window.matchMedia` stub for ThemeToggle in jsdom |

---

## Change 1 — Drag-and-drop in UploadView

`UploadView` was previously a `<label>` wrapping a hidden file input — drop events were silently ignored.

**Implementation:**
- Added `const [dragActive, setDragActive] = useState(false)`.
- Three handlers on the `<label>` element:
  - `handleDragOver(e)` — calls `e.preventDefault()` (required to allow drop), sets `dragActive = true`
  - `handleDragLeave()` — sets `dragActive = false`
  - `handleDrop(e)` — calls `e.preventDefault()`, sets `dragActive = false`, reads `e.dataTransfer.files[0]`, calls `onFile(file)` if present
- The `className` on `<label>` is constructed as a joined array that switches between the default state (`border-[var(--line)] hover:border-[var(--teal)]`) and the active-drag state (`border-[var(--teal)] bg-[var(--accent)]/10`) based on `dragActive`.
- Click-to-pick via the hidden `<input type="file">` is fully preserved.
- Props `{ onFile, error }` are unchanged.

---

## Change 2 — Select → Confirm → Analyze (no auto-analyze)

**State added to App:**
- `selectedFile: File | null` — holds the picked file before upload
- `analyzing: boolean` — true while `uploadVideo` is in flight (disables the Analyze button)

**View-gating logic (mutually exclusive):**
```
!selectedFile && !videoId    → <UploadView>
selectedFile && !videoId     → <SelectedVideo>
detectJob running            → <BallLoader> + <ProgressBar>
!detectJob && videoId        → review UI (Player + Timeline + …)
```

**Flow:**
1. `UploadView.onFile` → `handleFileSelected(file)` → sets `selectedFile`, clears any prior error
2. `SelectedVideo.onAnalyze` → `handleAnalyze()`:
   - Sets `analyzing = true`
   - Calls `api.uploadVideo(selectedFile)` → sets `videoId`, `duration`, clears `selectedFile`
   - Calls `api.startDetect(videoId, { threshold: 1 - sensitivity })` → sets `detectJob`
   - `finally`: sets `analyzing = false`; on error: sets `uploadError` (shown in UploadView)
3. `SelectedVideo.onReset` → `handleReset()` → clears `selectedFile` + `uploadError`

**SelectedVideo component** (`frontend/src/components/SelectedVideo.tsx`):
- Props: `{ file: File; onAnalyze: () => void; onReset: () => void; analyzing: boolean }`
- Creates a local object URL via `useEffect(() => { const url = URL.createObjectURL(file); setObjectUrl(url); return () => URL.revokeObjectURL(url); }, [file])` — revoked on unmount/file change to prevent memory leaks
- Shows `<video controls src={objectUrl}>` when the URL is ready
- Shows `file.name` and size in MB in monospace
- "Analyze video" button: `bg-[var(--accent)] text-[var(--accent-ink)]`, matches Export button style; disabled + shows "Uploading…" when `analyzing=true`
- "Choose a different video" button: secondary/ghost style, also disabled during analysis

---

## Change 3 — BallLoader during detection

**`frontend/src/components/BallLoader.tsx`:**
- A `<div class="flex justify-center py-2">` wrapping a 32×32 optic-lime circle (`h-8 w-8 rounded-full bg-[var(--accent)] ball-bounce`).
- `aria-hidden="true"` — screen readers hear the "Finding rallies…" ProgressBar label instead.
- Rendered in App above the ProgressBar when `detectJob && detect.status === "running"`.

**`frontend/src/index.css` additions:**
- `@keyframes ball-bounce` — scoped inside `@media (prefers-reduced-motion: no-preference)`: translates Y from 0 → −28px → 0 with matching shadow scaling (larger shadow at bottom = natural depth cue).
- `@keyframes ball-pulse` — scoped inside `@media (prefers-reduced-motion: reduce)`: simple opacity 1 → 0.4 → 1 pulse.
- `.ball-bounce` class — applies `ball-bounce` animation at 0.65s with a sporty ease-in-out cubic-bezier.
- `@media (prefers-reduced-motion: reduce) .ball-bounce` — overrides to `ball-pulse` animation.
- The existing global `animation-duration: 0.01ms !important` reduced-motion reset remains at the bottom and provides belt-and-suspenders coverage.

---

## New Tests

### `frontend/src/test/SelectedVideo.test.tsx` (4 tests)

| Test | Assertion |
|---|---|
| renders the file name | `screen.getByText(/rally-game\.mp4/)` is in the document |
| calls onAnalyze on button click | `vi.fn()` called once after `userEvent.click` on "Analyze video" |
| calls onReset on button click | `vi.fn()` called once after `userEvent.click` on "Choose a different video" |
| disables button + shows busy when analyzing=true | button with name /uploading/i is `disabled` |

Notes:
- `URL.createObjectURL` / `revokeObjectURL` mocked at module level (jsdom does not implement these).
- `makeFile()` creates a zero-byte `File` with the given name.

### `frontend/src/test/App.test.tsx` (4 tests)

| Test | Assertion |
|---|---|
| shows UploadView initially | "find the rallies" text present on mount |
| selecting a file shows SelectedVideo and does NOT call startDetect | After `userEvent.upload`, "Analyze video" button appears; `api.startDetect` and `api.uploadVideo` have NOT been called |
| clicking Analyze video calls uploadVideo then startDetect | After upload + click, `api.uploadVideo` called with the file; `api.startDetect` called with `("v1", { threshold: 0.5 })` |
| Reset button returns to UploadView | After upload + clicking "Choose a different video", "find the rallies" text is back |

Notes:
- Entire `api` module mocked via `vi.mock("../api", ...)` — no real fetch.
- `URL.createObjectURL/revokeObjectURL` mocked (SelectedVideo is rendered in tests 2–4).
- `window.matchMedia` stub added to `setup.ts` — ThemeToggle calls `matchMedia` on mount.

**Total test count:** 21 (13 original + 4 SelectedVideo + 4 App)

---

## Build Output

```
> build
> tsc -b && vite build

vite v6.4.3 building for production...
transforming...
✓ 1585 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.75 kB │ gzip:  0.43 kB
dist/assets/index-BA51T4hn.css   19.48 kB │ gzip:  4.66 kB
dist/assets/index-DSrLgtJq.js   161.66 kB │ gzip: 51.65 kB
✓ built in 1.03s
```

0 TypeScript errors.

---

## Test Output

```
 RUN  v3.2.6 /Users/chinoyoung/Code/highlights/frontend

 ✓ src/test/api.test.ts (4 tests) 14ms
 ✓ src/test/timeline-math.test.ts (7 tests) 7ms
 ✓ src/test/useJob.test.ts (2 tests) 17ms
 ✓ src/test/SelectedVideo.test.tsx (4 tests) 89ms
 ✓ src/test/App.test.tsx (4 tests) 131ms

 Test Files  5 passed (5)
      Tests  21 passed (21)
   Start at  15:08:05
   Duration  1.19s (transform 185ms, setup 358ms, collect 674ms, tests 258ms, environment 2.14s, prepare 511ms)
```
