# HV Task 2 Brief: Frontend HighlightsView + API additions + Tests

## Goal
Add output-management API functions to api.ts, create HighlightsView.tsx component,
wire it into App.tsx replacing ResultPanel on export-done, and add frontend tests.

## Working directory
/Users/chinoyoung/Code/highlights/frontend
Run tests: `npm run test` (from frontend/)
Build check: `npm run build` (from frontend/)

## Backend API shape (already implemented)
The backend now exposes:
- GET  /api/output/{videoId}       → { clips: string[], stitched: string | null }
- GET  /api/output/{videoId}/{filename} → video file
- DELETE /api/output/{videoId}/{filename} → { clips: string[], stitched: string | null }
- DELETE /api/output/{videoId}     → { clips: string[], stitched: string | null }

## File 1: frontend/src/api.ts (EXTEND only — do not break existing functions)

Add these four exports at the bottom of the file:

```typescript
export async function listOutput(videoId: string): Promise<{ clips: string[]; stitched: string | null }> {
  const r = await fetch(`/api/output/${videoId}`);
  if (!r.ok) {
    const detail = (await r.json().catch(() => ({}))).detail;
    throw new Error(detail || r.statusText);
  }
  return r.json();
}

export function outputUrl(videoId: string, filename: string): string {
  return `/api/output/${videoId}/${filename}`;
}

export async function deleteClip(videoId: string, filename: string): Promise<{ clips: string[]; stitched: string | null }> {
  const r = await fetch(`/api/output/${videoId}/${filename}`, { method: "DELETE" });
  if (!r.ok) {
    const detail = (await r.json().catch(() => ({}))).detail;
    throw new Error(detail || r.statusText);
  }
  return r.json();
}

export async function clearOutput(videoId: string): Promise<{ clips: string[]; stitched: string | null }> {
  const r = await fetch(`/api/output/${videoId}`, { method: "DELETE" });
  if (!r.ok) {
    const detail = (await r.json().catch(() => ({}))).detail;
    throw new Error(detail || r.statusText);
  }
  return r.json();
}
```

## File 2: frontend/src/components/HighlightsView.tsx (NEW)

Props: `{ videoId: string }`

State:
- `listing: { clips: string[]; stitched: string | null }` initialized to `{ clips: [], stitched: null }`
- `version: number` initialized to 0 (used for cache-busting)

Behavior:
- On mount: call `listOutput(videoId)` → set listing
- If `stitched != null`: show a `<video controls>` with `src={outputUrl(videoId, 'highlights.mp4') + '?v=' + version}` labelled "Combined reel"
- "Clips" section: responsive grid; each clip:
  - `<video controls src={outputUrl(videoId, name)}>` (no cache-bust needed on individual clips — they don't change)
  - Clip name in mono font
  - Delete button: lucide `Trash2` icon, `text-[var(--muted)] hover:text-[var(--danger)]`
  - On click: `await deleteClip(videoId, name)` → set listing to result AND increment version
- "Clear all" button: secondary style → `await clearOutput(videoId)` → set listing + increment version
- Empty state (no clips AND no stitched): show "No highlights yet — export some rallies."
- Heading "Highlights" using `font-[var(--font-display)]` or `font-display` (Tailwind v4)

Design tokens available (from index.css CSS vars):
- `--accent`, `--teal`, `--ink`, `--muted`, `--line`, `--surface`, `--danger`
- `--font-display`, `--font-body`, `--font-mono`

Lucide React is already installed. Import: `import { Trash2 } from "lucide-react"`

Use strict TypeScript — no `any`, no ts-ignore.

## File 3: frontend/src/App.tsx (MODIFY)

Currently, App.tsx renders `<ResultPanel result={exp.result} />` when export is done.
Replace it with `<HighlightsView videoId={videoId!} />`.

The `ResultPanel` import and usage should be removed. Check if ResultPanel.tsx is used
anywhere else before deleting it — if unused, delete the file.

Keep the entire rest of the review/export flow intact (Player, Timeline, Controls, RallyList,
detect flow, export progress bar, export error, etc.).

The export job state (`exp`) can still be used for the loading state, but once done,
show HighlightsView (which fetches its own listing).

HighlightsView should be rendered when `exp.status === "done"` AND `videoId` is set.

## File 4: frontend/src/test/api.test.ts (EXTEND)

Add new test cases to the existing `describe("api client", ...)` block (or a new describe block
at the bottom of the file — either is fine). Test the four new functions:

```typescript
it("listOutput hits GET /api/output/{id}", async () => {
  globalThis.fetch = mockFetch(200, { clips: ["clip_001.mp4"], stitched: "highlights.mp4" }) as any;
  const res = await api.listOutput("v1");
  expect(res.clips).toEqual(["clip_001.mp4"]);
  expect(res.stitched).toBe("highlights.mp4");
  expect(globalThis.fetch).toHaveBeenCalledWith("/api/output/v1");
});

it("outputUrl builds the right path", () => {
  expect(api.outputUrl("v9", "clip_001.mp4")).toBe("/api/output/v9/clip_001.mp4");
});

it("deleteClip sends DELETE and returns updated listing", async () => {
  globalThis.fetch = mockFetch(200, { clips: ["clip_002.mp4"], stitched: "highlights.mp4" }) as any;
  const res = await api.deleteClip("v1", "clip_001.mp4");
  expect(res.clips).toEqual(["clip_002.mp4"]);
  expect(globalThis.fetch).toHaveBeenCalledWith(
    "/api/output/v1/clip_001.mp4",
    expect.objectContaining({ method: "DELETE" }),
  );
});

it("clearOutput sends DELETE to /api/output/{id}", async () => {
  globalThis.fetch = mockFetch(200, { clips: [], stitched: null }) as any;
  const res = await api.clearOutput("v1");
  expect(res.clips).toEqual([]);
  expect(res.stitched).toBeNull();
  expect(globalThis.fetch).toHaveBeenCalledWith(
    "/api/output/v1",
    expect.objectContaining({ method: "DELETE" }),
  );
});
```

## Verification
```bash
npm run build
cd /Users/chinoyoung/Code/highlights/frontend && npm run test
```
Both must pass with 0 errors.
