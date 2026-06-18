# HV Task 2 Report

## Status: DONE

## Summary

All four deliverables implemented and verified.

### API additions (api.ts)
- Added `listOutput`, `outputUrl`, `deleteClip`, `clearOutput` at the bottom of the file.
- No existing functions were modified.

### HighlightsView.tsx (new)
- Created at `frontend/src/components/HighlightsView.tsx`.
- Props: `{ videoId: string }`.
- Fetches listing on mount via `listOutput`.
- Shows combined reel video with cache-bust `?v={version}` when `stitched != null`.
- Clips rendered in a responsive 1-col / 2-col grid with inline video, mono filename, Trash2 delete button.
- Delete increments `version` and updates listing.
- "Clear all" button shown when content exists; calls `clearOutput` → updates listing + increments version.
- Empty state: "No highlights yet — export some rallies."
- Heading uses `font-display` Tailwind utility (consistent with ResultPanel pattern).

### App.tsx modifications
- Replaced `import { ResultPanel }` with `import { HighlightsView }`.
- Replaced `<ResultPanel result={exp.result} />` with `<HighlightsView videoId={videoId!} />` guarded by `exp.status === "done" && videoId`.
- ResultPanel.tsx deleted (confirmed no other usages).

### Tests (api.test.ts)
- Added 4 tests inside the existing `describe("api client", ...)` block:
  `listOutput`, `outputUrl`, `deleteClip`, `clearOutput`.

## Test Results
25 passed (25) across 5 test files — 0 failures.

## Build Results
`tsc -b && vite build` — 0 TypeScript errors, bundle produced successfully.

## Files Changed
- `frontend/src/api.ts` — added 4 exports
- `frontend/src/components/HighlightsView.tsx` — new file
- `frontend/src/App.tsx` — swapped ResultPanel → HighlightsView
- `frontend/src/test/api.test.ts` — added 4 tests
- `frontend/src/components/ResultPanel.tsx` — deleted (unused)

## Concerns
None.
