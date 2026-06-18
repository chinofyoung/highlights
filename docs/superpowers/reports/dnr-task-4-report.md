# Task 4 Report: Frontend — Home Navigation

## Files Changed

- `frontend/src/App.tsx` — only file modified

## Changes Made

### 1. `goHome()` function (added after `handleContinueDraft`)

```tsx
function goHome() {
  setSelectedFile(null);
  setVideoId(null);
  setRallies([]);
  setDetectJob(null);
  setExportJob(null);
  setAnalyzing(false);
  setLibraryView(false);
  setUploadError(null);
}
```

Resets all view state to the upload/home screen (View 1). Clears every piece of state that gates the conditional views.

### 2. Header changes

Replaced the `<h1>` logo with a `<button>` calling `goHome`, and wrapped it + a conditional "New video" button + `<ThemeToggle />` in a flex container.

- Logo button: `onClick={goHome}`, `aria-label="Go to home / upload"`, preserves exact markup `Pickleball<span className="text-[var(--teal)]">.</span>highlights`
- "New video" button: shown only when `(videoId || selectedFile)`, calls `goHome`, styled with border/muted text matching the design system
- `<ThemeToggle />` remains at the far right, unchanged

### 3. Library-view "← Back" button

Replaced the inlined `onClick={() => { setVideoId(null); setLibraryView(false); setRallies([]); setExportJob(null); }}` with `onClick={goHome}`. The `goHome` function clears a superset of those setters (also clears `setDetectJob`, `setAnalyzing`, `setUploadError`) which is safe — those are already null/false in the library view.

## Build Result

```
vite v6.4.3 building for production...
✓ 1587 modules transformed.
dist/assets/index-Dz8odPow.js  180.19 kB │ gzip: 55.19 kB
✓ built in 881ms
```

Zero TypeScript errors. `tsc -b` passed cleanly before Vite bundled.

## Self-Review

- `goHome` resets all 8 state variables that affect view routing; no state is missed.
- The logo `<button>` preserves the exact inner markup from the plan verbatim.
- "New video" condition `(videoId || selectedFile)` matches the spec — shown on Views 2, 3, 4a, and 4; hidden on View 1 (home).
- Library Back `onClick` is now a single function reference, eliminating the inline arrow with partial resets. `goHome` is a strict superset of what was there, so no regression.
- No other handlers, views, or logic were touched.
- No imports added (no new symbols needed).

## Concerns

None. The change is purely additive (`goHome` is a new function) plus two surgical replacements. The "New video" guard `(videoId || selectedFile)` correctly hides the button on the home screen itself, preventing a no-op button from being visible when already home.
