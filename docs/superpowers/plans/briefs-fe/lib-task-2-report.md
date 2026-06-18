# Task 2 Report: Frontend types.ts + api.ts Library Functions + API Tests

## Changes Made

### 1. `/Users/chinoyoung/Code/highlights/frontend/src/types.ts`
Added `Project` interface after the existing `Draft` interface:
```typescript
export interface Project {
  video_id: string;
  original_filename: string;
  uploaded_at: number;
  size_bytes: number;
  clip_count: number;
}
```

### 2. `/Users/chinoyoung/Code/highlights/frontend/src/api.ts`
- Updated import on line 1 to include `Project`: `import type { JobRecord, Rally, DetectParams, Draft, Project } from "./types";`
- Appended three new exported functions at the end of the file:
  - `listLibrary()` — GET /api/library, returns `Promise<Project[]>`
  - `openProject(videoId)` — POST /api/library/{id}/open, returns `Promise<{ video_id: string; duration: number }>`
  - `deleteProject(videoId)` — DELETE /api/library/{id}, returns `Promise<Project[]>`

### 3. `/Users/chinoyoung/Code/highlights/frontend/src/test/api.test.ts`
Appended three new test cases inside the existing `describe("api client", ...)` block:
- `listLibrary hits GET /api/library`
- `openProject sends POST /api/library/{id}/open`
- `deleteProject sends DELETE /api/library/{id} and returns updated list`

## npm run build output

```
> build
> tsc -b && vite build

vite v6.4.3 building for production...
transforming...
✓ 1586 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.75 kB │ gzip:  0.43 kB
dist/assets/index-Dfi0dK5-.css   21.51 kB │ gzip:  4.98 kB
dist/assets/index-DK1l_BqB.js   167.91 kB │ gzip: 52.88 kB
✓ built in 827ms
```

Zero TypeScript errors.

## npm run test output

```
> test
> vitest run

 RUN  v3.2.6 /Users/chinoyoung/Code/highlights/frontend

 ✓ src/test/timeline-math.test.ts (7 tests) 4ms
 ✓ src/test/api.test.ts (13 tests) 16ms
 ✓ src/test/useJob.test.ts (2 tests) 18ms
 ✓ src/test/SelectedVideo.test.tsx (4 tests) 96ms
 ✓ src/test/App.test.tsx (4 tests) 137ms

 Test Files  5 passed (5)
      Tests  30 passed (30)
   Start at  17:42:57
   Duration  1.25s (transform 217ms, setup 395ms, collect 809ms, tests 271ms, environment 2.11s, prepare 466ms)
```

All 30 tests pass (api.test.ts grew from 10 to 13 tests).
