# Task 7 (modern-frontend)

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

## Task 7: useJob polling hook (frontend)

**Files:**
- Create: `frontend/src/useJob.ts`, `frontend/src/test/useJob.test.ts`

**Interfaces:**
- Consumes: `api.getJob`.
- Produces: `useJob(jobId: string | null): { status, progress, result, error }`. Polls `getJob` every 500ms while a non-null jobId is `running`; stops on `done`/`error` or when jobId becomes null; cleans up the interval on unmount.

- [ ] **Step 1: Write failing tests `frontend/src/test/useJob.test.ts`**

```ts
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useJob } from "../useJob";
import * as api from "../api";

beforeEach(() => { vi.useFakeTimers(); });
afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); });

describe("useJob", () => {
  it("polls until done and exposes result", async () => {
    const seq = [
      { status: "running", progress: 0.5, result: null, error: null },
      { status: "done", progress: 1, result: { rallies: [] }, error: null },
    ];
    vi.spyOn(api, "getJob").mockImplementation(async () => seq.shift() as any ?? seq[0]);

    const { result } = renderHook(() => useJob("j1"));
    await vi.advanceTimersByTimeAsync(600);
    await waitFor(() => expect(result.current.status).toBe("running"));
    await vi.advanceTimersByTimeAsync(600);
    await waitFor(() => expect(result.current.status).toBe("done"));
    expect(result.current.result).toEqual({ rallies: [] });
  });

  it("does nothing when jobId is null", async () => {
    const spy = vi.spyOn(api, "getJob");
    renderHook(() => useJob(null));
    await vi.advanceTimersByTimeAsync(1000);
    expect(spy).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run, expect FAIL**

Run: `cd frontend && npx vitest run src/test/useJob.test.ts`
Expected: FAIL (module missing).

- [ ] **Step 3: Create `frontend/src/useJob.ts`**

```ts
import { useEffect, useState } from "react";
import { getJob } from "./api";
import type { JobRecord } from "./types";

const IDLE: JobRecord = { status: "running", progress: 0, result: null, error: null };

export function useJob(jobId: string | null): JobRecord {
  const [rec, setRec] = useState<JobRecord>(IDLE);

  useEffect(() => {
    if (!jobId) return;
    setRec(IDLE);
    let active = true;

    const tick = async () => {
      try {
        const next = await getJob(jobId);
        if (!active) return;
        setRec(next);
        if (next.status !== "running") clearInterval(id);
      } catch (e) {
        if (!active) return;
        setRec({ status: "error", progress: 0, result: null, error: String(e) });
        clearInterval(id);
      }
    };

    const id = setInterval(tick, 500);
    tick();
    return () => { active = false; clearInterval(id); };
  }, [jobId]);

  return rec;
}
```

- [ ] **Step 4: Run, expect PASS**

Run: `cd frontend && npx vitest run src/test/useJob.test.ts`
Expected: PASS (2 tests).

- [ ] **Step 5: Checkpoint** — `cd frontend && npm run build && npm run test`. Green.

---

