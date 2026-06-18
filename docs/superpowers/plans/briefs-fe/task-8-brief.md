# Task 8 (modern-frontend)

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

## Task 8: Timeline trim math (frontend, pure)

**Files:**
- Create: `frontend/src/timeline-math.ts`, `frontend/src/test/timeline-math.test.ts`

**Interfaces:**
- Produces (pure functions, no DOM):
  - `pxToTime(px:number, trackWidthPx:number, duration:number):number`
  - `clampStart(newStart:number, rally:{start:number;end:number}, prevEnd:number, minGap:number):number` — clamps to `[prevEnd, rally.end - minGap]`.
  - `clampEnd(newEnd:number, rally:{start:number;end:number}, nextStart:number, minGap:number):number` — clamps to `[rally.start + minGap, nextStart]`.
  - `moveBody(deltaT:number, rally:{start:number;end:number}, prevEnd:number, nextStart:number):{start:number;end:number}` — shifts both edges by `deltaT`, preserving length, clamped between `prevEnd` and `nextStart`.
  - `MIN_GAP = 0.2`.

- [ ] **Step 1: Write failing tests `frontend/src/test/timeline-math.test.ts`**

```ts
import { describe, it, expect } from "vitest";
import { pxToTime, clampStart, clampEnd, moveBody, MIN_GAP } from "../timeline-math";

describe("timeline math", () => {
  it("pxToTime maps proportionally", () => {
    expect(pxToTime(50, 100, 10)).toBe(5);
    expect(pxToTime(0, 100, 10)).toBe(0);
  });

  it("clampStart respects prevEnd floor", () => {
    expect(clampStart(1, { start: 5, end: 8 }, 3, MIN_GAP)).toBe(3);
  });

  it("clampStart respects min gap ceiling", () => {
    expect(clampStart(7.9, { start: 5, end: 8 }, 0, MIN_GAP)).toBe(8 - MIN_GAP);
  });

  it("clampEnd respects nextStart ceiling", () => {
    expect(clampEnd(12, { start: 5, end: 8 }, 10, MIN_GAP)).toBe(10);
  });

  it("clampEnd respects min gap floor", () => {
    expect(clampEnd(5.1, { start: 5, end: 8 }, 99, MIN_GAP)).toBe(5 + MIN_GAP);
  });

  it("moveBody preserves length and clamps to prevEnd", () => {
    const r = moveBody(-10, { start: 5, end: 8 }, 2, 99);
    expect(r.end - r.start).toBeCloseTo(3);
    expect(r.start).toBe(2);
  });

  it("moveBody clamps to nextStart", () => {
    const r = moveBody(10, { start: 5, end: 8 }, 0, 12);
    expect(r.end).toBe(12);
    expect(r.end - r.start).toBeCloseTo(3);
  });
});
```

- [ ] **Step 2: Run, expect FAIL**

Run: `cd frontend && npx vitest run src/test/timeline-math.test.ts`
Expected: FAIL (module missing).

- [ ] **Step 3: Create `frontend/src/timeline-math.ts`**

```ts
export const MIN_GAP = 0.2;

export function pxToTime(px: number, trackWidthPx: number, duration: number): number {
  if (trackWidthPx <= 0) return 0;
  return (px / trackWidthPx) * duration;
}

export function clampStart(
  newStart: number,
  rally: { start: number; end: number },
  prevEnd: number,
  minGap: number,
): number {
  return Math.min(Math.max(newStart, prevEnd), rally.end - minGap);
}

export function clampEnd(
  newEnd: number,
  rally: { start: number; end: number },
  nextStart: number,
  minGap: number,
): number {
  return Math.max(Math.min(newEnd, nextStart), rally.start + minGap);
}

export function moveBody(
  deltaT: number,
  rally: { start: number; end: number },
  prevEnd: number,
  nextStart: number,
): { start: number; end: number } {
  const len = rally.end - rally.start;
  let start = rally.start + deltaT;
  start = Math.max(prevEnd, Math.min(start, nextStart - len));
  return { start, end: start + len };
}
```

- [ ] **Step 4: Run, expect PASS**

Run: `cd frontend && npx vitest run src/test/timeline-math.test.ts`
Expected: PASS (7 tests).

- [ ] **Step 5: Checkpoint** — `cd frontend && npm run build && npm run test`. All green (api + useJob + timeline-math).

---

