# Cancel+Play Task 2 — Frontend changes

## Context
Pickleball highlights app. You're adding 3 frontend features:
1. Cancel button during detection (with flash fix)
2. playSegment on the Player component
3. Per-rally Play button in RallyList

Working directory: `/Users/chinoyoung/Code/highlights/frontend`
Run npm from there.

## Files to change
- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/components/Player.tsx`
- `frontend/src/components/RallyList.tsx`

## Current state of key files (read before editing):
- `/Users/chinoyoung/Code/highlights/frontend/src/api.ts`
- `/Users/chinoyoung/Code/highlights/frontend/src/App.tsx`
- `/Users/chinoyoung/Code/highlights/frontend/src/components/Player.tsx`
- `/Users/chinoyoung/Code/highlights/frontend/src/components/RallyList.tsx`

## 1. api.ts — add cancelJob

Add this export after `getJob`:
```typescript
export async function cancelJob(jobId: string): Promise<void> {
  await postJSON<unknown>(`/api/jobs/${jobId}/cancel`, {});
}
```

Note: `postJSON` already exists in the file and throws on non-OK with server detail.

## 2. App.tsx — three changes

### 2a. Remove setSelectedFile(null) from handleAnalyze
In `handleAnalyze`, remove the line `setSelectedFile(null)`. Keep `selectedFile` set throughout the analysis so `SelectedVideo` can reappear if the user cancels.

### 2b. Flash fix — update the detecting view condition
Change the detecting view block condition from:
```tsx
{detectJob && detect.status === "running" && (
```
to:
```tsx
{(analyzing || detectJob) && (
```
This ensures the loader shows during both the `analyzing` (upload) phase AND while the job runs, eliminating the flash.

Also add the `analyzing` guard to the review UI. Change the review UI condition from:
```tsx
{videoId && !detectJob && (
```
to:
```tsx
{videoId && !detectJob && !analyzing && (
```

### 2c. Cancel button
Inside the detecting view block (the `{(analyzing || detectJob) && ...}` block), add a Cancel button below the ProgressBar:
```tsx
<button
  disabled={analyzing}
  onClick={async () => {
    if (detectJob) await cancelJob(detectJob);
    setDetectJob(null);
    setAnalyzing(false);
    setVideoId(null);
  }}
  className="mt-2 rounded border border-[var(--line)] px-4 py-2 text-sm
             text-[var(--muted)] hover:text-[var(--ink)] disabled:opacity-40
             transition-colors"
>
  Cancel
</button>
```
Note: the button is disabled while `analyzing` (upload phase) since there's no job to cancel yet. Import `cancelJob` from `./api`.

### 2d. Import cancelJob
Add `cancelJob` to the existing `import * as api from "./api"` — or call it as `api.cancelJob(detectJob)`. Since the file uses `import * as api`, call it as `api.cancelJob(detectJob)`.

Wait — `cancelJob` is called directly in the onClick handler inside JSX. Since all api calls go through `import * as api`, call `api.cancelJob(detectJob)` inside the onClick.

The onClick should be:
```tsx
onClick={async () => {
  if (detectJob) await api.cancelJob(detectJob);
  setDetectJob(null);
  setAnalyzing(false);
  setVideoId(null);
}}
```

## 3. Player.tsx — add playSegment to PlayerHandle

### 3a. Extend PlayerHandle interface
```typescript
export interface PlayerHandle {
  seekTo(t: number): void;
  play(): void;
  playSegment(start: number, end: number): void;
}
```

### 3b. Add segListenerRef inside the component
Inside the `forwardRef` component body, before `useImperativeHandle`, add:
```typescript
const segListenerRef = useRef<((e: Event) => void) | null>(null);
```

### 3c. Add playSegment implementation to useImperativeHandle
```typescript
playSegment(start, end) {
  if (!v.current) return;
  // Clear any previous segment listener to prevent overlapping plays
  if (segListenerRef.current) {
    v.current.removeEventListener("timeupdate", segListenerRef.current);
    segListenerRef.current = null;
  }
  v.current.currentTime = start;
  const listener = () => {
    if (v.current && v.current.currentTime >= end) {
      v.current.pause();
      v.current.removeEventListener("timeupdate", listener);
      segListenerRef.current = null;
    }
  };
  segListenerRef.current = listener;
  v.current.addEventListener("timeupdate", listener);
  v.current.play();
},
```

## 4. RallyList.tsx — add per-rally Play button

### 4a. Import Play icon
Add to imports: `import { Play } from "lucide-react";`

### 4b. Add onPlay prop
Change the props interface:
```typescript
export function RallyList({ rallies, onToggle, onJump, onPlay }: {
  rallies: Rally[];
  onToggle: (i: number) => void;
  onJump: (t: number) => void;
  onPlay: (rally: Rally) => void;
}) {
```

### 4c. Add Play button to each row
In the `<li>` for each rally, add a Play icon button BETWEEN the checkbox and the existing `<button>` (the jump-to button). The Play button should be a standalone `<button>`:

```tsx
<button
  onClick={(e) => { e.stopPropagation(); onPlay(r); }}
  className="p-1 rounded text-[var(--teal)] hover:text-[var(--accent)]
             focus-visible:outline-2 focus-visible:outline-[var(--teal)]"
  aria-label={`Play rally ${i + 1}`}
>
  <Play size={14} />
</button>
```

### 4d. Update App.tsx to pass onPlay
In `App.tsx`, the `RallyList` usage currently looks like:
```tsx
<RallyList rallies={rallies}
           onToggle={(i) => setRallies((rs) =>
             rs.map((r, j) => (j === i ? { ...r, included: !r.included } : r)))}
           onJump={(t) => { player.current?.seekTo(t); player.current?.play(); }} />
```

Add `onPlay` prop:
```tsx
<RallyList rallies={rallies}
           onToggle={(i) => setRallies((rs) =>
             rs.map((r, j) => (j === i ? { ...r, included: !r.included } : r)))}
           onJump={(t) => { player.current?.seekTo(t); player.current?.play(); }}
           onPlay={(r) => player.current?.playSegment(r.start, r.end)} />
```

## Strict TS requirements
- Every declared prop must be used (noUnusedLocals/noUnusedParams)
- The `onPlay` prop in RallyList MUST be called somewhere in the component body
- `playSegment` in PlayerHandle MUST be implemented in useImperativeHandle
- `cancelJob` in api.ts MUST be exported

## Existing App tests that must still pass
The App.test.tsx file has tests including "no-auto-analyze contract". The key constraint:
- Selecting a file shows SelectedVideo
- Clicking Analyze calls uploadVideo then startDetect
- Reset returns to UploadView

Since we're keeping `selectedFile` set through analysis now (not clearing it in handleAnalyze), verify the test "clicking Analyze video calls uploadVideo then startDetect" still passes. The test mocks `uploadVideo` and `startDetect`, and after clicking Analyze, the component will enter the detecting view (because `analyzing` becomes true then `detectJob` gets set). The test only asserts those functions were called — it does NOT assert that SelectedVideo is still visible — so it should still pass.

However, the test "selecting a file shows SelectedVideo and does NOT call startDetect" relies on SelectedVideo appearing. The current condition in App.tsx is:
```tsx
{selectedFile && !videoId && (
  <SelectedVideo ... />
)}
```
This must remain working — when a file is selected and no videoId, show SelectedVideo. This is unchanged.

## Verification
From `/Users/chinoyoung/Code/highlights/frontend/`:
1. `npm run build` — must produce 0 TS errors
2. `npm run test` — all tests must pass (existing 13 App tests + any others)

## Report
Write your full report to:
`/Users/chinoyoung/Code/highlights/docs/superpowers/plans/briefs-fe/cp-task-2-report.md`

Include: what you changed in each file, any TS errors encountered and fixed, full test output.

Return to caller: STATUS (DONE/DONE_WITH_CONCERNS/BLOCKED/NEEDS_CONTEXT), one-line build+test summary, concerns if any.
