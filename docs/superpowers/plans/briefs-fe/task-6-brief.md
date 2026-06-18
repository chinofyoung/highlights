# Task 6 (modern-frontend)

## Global Constraints

- **Backend Python floor:** 3.10+ (interpreter is 3.10.8). Activate `.venv` before any pytest.
- **No new backend dependencies** — background work uses stdlib `threading`.
- **Backward-compatible analyzer/exporter signatures:** new `progress_callback` params MUST default to `None` so existing callers/tests keep working.
- **Existing backend suite (24 tests) must stay green** except the two `/api/detect` & `/api/export` tests in `tests/test_api.py`, which are intentionally updated in Task 4 to the new job flow.
- **Git is disabled** (not a git repo; user policy forbids state-changing git). Wherever a step says "Commit", instead run the task's tests (and build, where relevant) and confirm green. Never run a state-changing git command.
- **Node 22 / npm 10** are installed. Frontend commands run from `frontend/`.
- **Sensitivity semantics:** higher slider = more sensitive = more rallies; the client sends `threshold = 1 - sliderValue`.
- **Job record shape (canonical, used across backend + frontend):** `{ "status": "running"|"done"|"error", "progress": float 0.0–1.0, "result": object|null, "error": string|null }`.
- **Detect job result shape:** `{ "rallies": [{start, end, confidence}] }`. **Export job result shape:** `{ "clips": [string], "stitched": string|null }`.
- **If a pinned npm version fails to resolve,** install the latest compatible version and note it in the task report.



---

## Task 6: API client + types (frontend)

**Files:**
- Create: `frontend/src/types.ts`, `frontend/src/api.ts`, `frontend/src/test/api.test.ts`

**Interfaces:**
- Produces:
  - `types.ts`: `Rally {start:number; end:number; confidence:number; included:boolean}`, `JobRecord {status:"running"|"done"|"error"; progress:number; result:any; error:string|null}`, `DetectParams {threshold?:number}`.
  - `api.ts`: `uploadVideo(file:File): Promise<{video_id:string; duration:number}>`, `startDetect(videoId:string, params:DetectParams): Promise<{job_id:string}>`, `startExport(videoId:string, ranges:{start:number;end:number}[]): Promise<{job_id:string}>`, `getJob(jobId:string): Promise<JobRecord>`, `resegment(videoId:string, params:DetectParams): Promise<{rallies:Rally[]}>`, `videoUrl(videoId:string): string`. All throw `Error(detail)` on non-OK.

- [ ] **Step 1: Write failing tests `frontend/src/test/api.test.ts`**

```ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import * as api from "../api";

beforeEach(() => { vi.restoreAllMocks(); });

function mockFetch(status: number, body: any) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response);
}

describe("api client", () => {
  it("startDetect posts and returns job_id", async () => {
    global.fetch = mockFetch(200, { job_id: "abc" }) as any;
    const res = await api.startDetect("v1", { threshold: 0.3 });
    expect(res.job_id).toBe("abc");
    expect(global.fetch).toHaveBeenCalledWith(
      "/api/detect",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("throws with server detail on non-OK", async () => {
    global.fetch = mockFetch(400, { detail: "bad video" }) as any;
    await expect(api.uploadVideo(new File([""], "x.txt"))).rejects.toThrow("bad video");
  });

  it("getJob returns the record", async () => {
    global.fetch = mockFetch(200, { status: "done", progress: 1, result: { rallies: [] }, error: null }) as any;
    const rec = await api.getJob("j1");
    expect(rec.status).toBe("done");
  });

  it("videoUrl builds the right path", () => {
    expect(api.videoUrl("v9")).toBe("/api/video/v9");
  });
});
```

- [ ] **Step 2: Run, expect FAIL**

Run: `cd frontend && npx vitest run src/test/api.test.ts`
Expected: FAIL (module/exports missing).

- [ ] **Step 3: Create `frontend/src/types.ts`**

```ts
export interface Rally {
  start: number;
  end: number;
  confidence: number;
  included: boolean;
}

export interface JobRecord {
  status: "running" | "done" | "error";
  progress: number;
  result: any;
  error: string | null;
}

export interface DetectParams {
  threshold?: number;
}
```

- [ ] **Step 4: Create `frontend/src/api.ts`**

```ts
import type { JobRecord, Rally, DetectParams } from "./types";

async function postJSON<T>(url: string, body: unknown): Promise<T> {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const detail = (await r.json().catch(() => ({}))).detail;
    throw new Error(detail || r.statusText);
  }
  return r.json();
}

export async function uploadVideo(file: File): Promise<{ video_id: string; duration: number }> {
  const fd = new FormData();
  fd.append("file", file);
  const r = await fetch("/api/upload", { method: "POST", body: fd });
  if (!r.ok) {
    const detail = (await r.json().catch(() => ({}))).detail;
    throw new Error(detail || r.statusText);
  }
  return r.json();
}

export function startDetect(videoId: string, params: DetectParams) {
  return postJSON<{ job_id: string }>("/api/detect", { video_id: videoId, params });
}

export function startExport(videoId: string, ranges: { start: number; end: number }[]) {
  return postJSON<{ job_id: string }>("/api/export", { video_id: videoId, ranges });
}

export async function getJob(jobId: string): Promise<JobRecord> {
  const r = await fetch(`/api/jobs/${jobId}`);
  if (!r.ok) throw new Error("job lookup failed");
  return r.json();
}

export function resegment(videoId: string, params: DetectParams) {
  return postJSON<{ rallies: Rally[] }>("/api/resegment", { video_id: videoId, params });
}

export function videoUrl(videoId: string): string {
  return `/api/video/${videoId}`;
}
```

- [ ] **Step 5: Run, expect PASS**

Run: `cd frontend && npx vitest run src/test/api.test.ts`
Expected: PASS (4 tests).

- [ ] **Step 6: Checkpoint** — `cd frontend && npm run build && npm run test`. Both green.

---

