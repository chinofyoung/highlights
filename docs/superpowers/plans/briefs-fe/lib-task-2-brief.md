# Task 2: Frontend types.ts + api.ts Library Functions + API Tests

## Context
Pickleball highlights app. Frontend React+TS+Tailwind in `/Users/chinoyoung/Code/highlights/frontend/`.

Key files to read first:
- `/Users/chinoyoung/Code/highlights/frontend/src/types.ts` — add Project interface (NOTE: this file currently contains both interface definitions AND Rally/JobRecord etc.; it's actually merged with api.ts exports — read it carefully)
- `/Users/chinoyoung/Code/highlights/frontend/src/api.ts` — add 3 new functions
- `/Users/chinoyoung/Code/highlights/frontend/src/test/api.test.ts` — extend with new tests

## Step 1: `types.ts`

Add this interface (do not remove anything existing):
```typescript
export interface Project {
  video_id: string;
  original_filename: string;
  uploaded_at: number;
  size_bytes: number;
  clip_count: number;
}
```

## Step 2: `api.ts` — add 3 functions

Add these imports at the top if not present: `import type { ..., Project } from "./types";`

Add these three functions at the end of the file:

```typescript
export async function listLibrary(): Promise<Project[]> {
  const r = await fetch("/api/library");
  if (!r.ok) {
    const detail = (await r.json().catch(() => ({}))).detail;
    throw new Error(detail || r.statusText);
  }
  return r.json();
}

export async function openProject(videoId: string): Promise<{ video_id: string; duration: number }> {
  const r = await fetch(`/api/library/${videoId}/open`, { method: "POST" });
  if (!r.ok) {
    const detail = (await r.json().catch(() => ({}))).detail;
    throw new Error(detail || r.statusText);
  }
  return r.json();
}

export async function deleteProject(videoId: string): Promise<Project[]> {
  const r = await fetch(`/api/library/${videoId}`, { method: "DELETE" });
  if (!r.ok) {
    const detail = (await r.json().catch(() => ({}))).detail;
    throw new Error(detail || r.statusText);
  }
  return r.json();
}
```

## Step 3: `test/api.test.ts` — add 3 new tests

Append to the existing `describe("api client", ...)` block:

```typescript
it("listLibrary hits GET /api/library", async () => {
  const mockProjects = [
    { video_id: "abc", original_filename: "game.mp4", uploaded_at: 200.0, size_bytes: 5000000, clip_count: 2 },
  ];
  globalThis.fetch = mockFetch(200, mockProjects) as any;
  const res = await api.listLibrary();
  expect(res).toEqual(mockProjects);
  expect(globalThis.fetch).toHaveBeenCalledWith("/api/library");
});

it("openProject sends POST /api/library/{id}/open", async () => {
  globalThis.fetch = mockFetch(200, { video_id: "abc", duration: 120.5 }) as any;
  const res = await api.openProject("abc");
  expect(res.video_id).toBe("abc");
  expect(res.duration).toBe(120.5);
  expect(globalThis.fetch).toHaveBeenCalledWith(
    "/api/library/abc/open",
    expect.objectContaining({ method: "POST" }),
  );
});

it("deleteProject sends DELETE /api/library/{id} and returns updated list", async () => {
  globalThis.fetch = mockFetch(200, []) as any;
  const res = await api.deleteProject("abc");
  expect(res).toEqual([]);
  expect(globalThis.fetch).toHaveBeenCalledWith(
    "/api/library/abc",
    expect.objectContaining({ method: "DELETE" }),
  );
});
```

## Verification

From the frontend directory:
```bash
npm run build 2>&1 | tail -20
npm run test 2>&1 | tail -30
```
Zero TypeScript errors. All tests pass.

## Report file
Write your full report to: `/Users/chinoyoung/code/highlights/docs/superpowers/plans/briefs-fe/lib-task-2-report.md`

Include: what you changed, npm run build output, npm run test output.

Return as your final message: STATUS (DONE/DONE_WITH_CONCERNS/NEEDS_CONTEXT/BLOCKED), one line on changes, one line on test results.
