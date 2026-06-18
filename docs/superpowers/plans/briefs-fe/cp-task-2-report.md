# CP Task 2 — Implementation Report

## Status: DONE

Build: 0 TS errors. Tests: 21/21 passed (5 test files).

---

## Changes Made

### frontend/src/api.ts
Added `cancelJob` export after `getJob`. Uses the existing `postJSON` helper to POST to `/api/jobs/${jobId}/cancel`.

### frontend/src/components/Player.tsx
- Extended `PlayerHandle` interface with `playSegment(start: number, end: number): void`
- Added `segListenerRef` (`useRef<((e: Event) => void) | null>(null)`) inside the component body before `useImperativeHandle`
- Implemented `playSegment` in `useImperativeHandle`: clears any prior segment listener, seeks to `start`, registers a `timeupdate` listener that pauses and cleans up when `currentTime >= end`, then calls `play()`

### frontend/src/components/RallyList.tsx
- Added `import { Play } from "lucide-react"`
- Added `onPlay: (rally: Rally) => void` to the props destructure and interface
- Inserted a `<button>` with a `<Play size={14} />` icon between the checkbox and the existing jump button; calls `onPlay(r)` with `e.stopPropagation()` to avoid triggering the parent `<li>` hover

### frontend/src/App.tsx
Four sub-changes:

1. **Removed `setSelectedFile(null)`** from `handleAnalyze` so `selectedFile` remains set during upload/detection (enables the Cancel button to return to SelectedVideo state).

2. **Flash fix — detecting view condition** changed from `{detectJob && detect.status === "running"}` to `{(analyzing || detectJob) && ...}` so the loader appears during the upload phase too.

3. **Cancel button** added inside the detecting block. Disabled while `analyzing` (no job to cancel yet). On click: calls `api.cancelJob(detectJob)` if a job exists, then resets `detectJob`, `analyzing`, and `videoId` to null.

4. **Review UI guard** updated from `{videoId && !detectJob}` to `{videoId && !detectJob && !analyzing}` to prevent the review panel from briefly flashing before the detecting view appears.

5. **`onPlay` prop** wired to `RallyList`: `onPlay={(r) => player.current?.playSegment(r.start, r.end)}`

---

## Test Output

```
 ✓ src/test/timeline-math.test.ts (7 tests)
 ✓ src/test/api.test.ts (4 tests)
 ✓ src/test/useJob.test.ts (2 tests)
 ✓ src/test/SelectedVideo.test.tsx (4 tests)
 ✓ src/test/App.test.tsx (4 tests)

 Test Files  5 passed (5)
      Tests  21 passed (21)
```

No TS errors encountered. No existing tests required modification.
