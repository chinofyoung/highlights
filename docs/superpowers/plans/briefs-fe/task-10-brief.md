# Task 10 (modern-frontend)

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

## Task 10: Timeline + App integration (frontend)

**Files:**
- Create: `frontend/src/components/Timeline.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `timeline-math` (pxToTime/clampStart/clampEnd/moveBody/MIN_GAP), all components, `api`, `useJob`, `types`.
- Produces:
  - `Timeline({rallies, duration, onChange, onPreview})` — renders blocks with left/right drag handles + body drag; calls `onChange(index, {start,end})` during drag and `onPreview(t)` to live-seek.
  - `App` — full flow state machine wiring upload → detect job (ProgressBar) → review (Player + Timeline + RallyList + Controls) → export job (ProgressBar) → ResultPanel.

- [ ] **Step 1: Create `frontend/src/components/Timeline.tsx`**

```tsx
import { useRef } from "react";
import type { Rally } from "../types";
import { pxToTime, clampStart, clampEnd, moveBody, MIN_GAP } from "../timeline-math";

type Drag = { index: number; mode: "start" | "end" | "body"; startX: number; orig: Rally } | null;

export function Timeline({ rallies, duration, onChange, onPreview }: {
  rallies: Rally[];
  duration: number;
  onChange: (index: number, next: { start: number; end: number }) => void;
  onPreview: (t: number) => void;
}) {
  const track = useRef<HTMLDivElement>(null);
  const drag = useRef<Drag>(null);

  const onPointerDown = (e: React.PointerEvent, index: number, mode: "start" | "end" | "body") => {
    e.stopPropagation();
    (e.target as Element).setPointerCapture(e.pointerId);
    drag.current = { index, mode, startX: e.clientX, orig: rallies[index] };
  };

  const onPointerMove = (e: React.PointerEvent) => {
    const d = drag.current;
    if (!d || !track.current) return;
    const width = track.current.getBoundingClientRect().width;
    const deltaT = pxToTime(e.clientX - d.startX, width, duration);
    const prevEnd = d.index > 0 ? rallies[d.index - 1].end : 0;
    const nextStart = d.index < rallies.length - 1 ? rallies[d.index + 1].start : duration;

    if (d.mode === "start") {
      const start = clampStart(d.orig.start + deltaT, d.orig, prevEnd, MIN_GAP);
      onChange(d.index, { start, end: d.orig.end });
      onPreview(start);
    } else if (d.mode === "end") {
      const end = clampEnd(d.orig.end + deltaT, d.orig, nextStart, MIN_GAP);
      onChange(d.index, { start: d.orig.start, end });
      onPreview(end);
    } else {
      const moved = moveBody(deltaT, d.orig, prevEnd, nextStart);
      onChange(d.index, moved);
      onPreview(moved.start);
    }
  };

  const onPointerUp = () => { drag.current = null; };

  return (
    <div ref={track} onPointerMove={onPointerMove} onPointerUp={onPointerUp}
         className="relative h-12 w-full rounded-lg bg-slate-200 dark:bg-slate-700"
         style={{ touchAction: "none" }}>
      {rallies.map((r, i) => {
        const left = (100 * r.start) / duration;
        const width = (100 * (r.end - r.start)) / duration;
        return (
          <div key={i}
               className={`absolute top-0 h-full rounded ${r.included ? "bg-emerald-500/80" : "bg-slate-400/60"}`}
               style={{ left: `${left}%`, width: `${width}%` }}
               onPointerDown={(e) => onPointerDown(e, i, "body")}
               onClick={() => onPreview(r.start)}>
            <div onPointerDown={(e) => onPointerDown(e, i, "start")}
                 className="absolute left-0 top-0 h-full w-2 cursor-ew-resize rounded-l bg-white/70" />
            <div onPointerDown={(e) => onPointerDown(e, i, "end")}
                 className="absolute right-0 top-0 h-full w-2 cursor-ew-resize rounded-r bg-white/70" />
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 2: Replace `frontend/src/App.tsx`** with the full flow

```tsx
import { useRef, useState } from "react";
import * as api from "./api";
import { useJob } from "./useJob";
import type { Rally } from "./types";
import { UploadView } from "./components/UploadView";
import { ProgressBar } from "./components/ProgressBar";
import { Player, type PlayerHandle } from "./components/Player";
import { Timeline } from "./components/Timeline";
import { RallyList } from "./components/RallyList";
import { Controls } from "./components/Controls";
import { ThemeToggle } from "./components/ThemeToggle";
import { ResultPanel } from "./components/ResultPanel";

export default function App() {
  const [videoId, setVideoId] = useState<string | null>(null);
  const [duration, setDuration] = useState(0);
  const [rallies, setRallies] = useState<Rally[]>([]);
  const [sensitivity, setSensitivity] = useState(0.5);
  const [detectJob, setDetectJob] = useState<string | null>(null);
  const [exportJob, setExportJob] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const player = useRef<PlayerHandle>(null);

  const detect = useJob(detectJob);
  const exp = useJob(exportJob);

  // detect job completed → load rallies
  if (detect.status === "done" && detectJob && detect.result) {
    const rs: Rally[] = detect.result.rallies.map((r: any) => ({ ...r, included: true }));
    setRallies(rs);
    setDetectJob(null);
  }

  async function handleFile(file: File) {
    setUploadError(null);
    try {
      const up = await api.uploadVideo(file);
      setVideoId(up.video_id);
      setDuration(up.duration);
      const { job_id } = await api.startDetect(up.video_id, { threshold: 1 - sensitivity });
      setDetectJob(job_id);
    } catch (e) {
      setUploadError(String(e instanceof Error ? e.message : e));
    }
  }

  async function handleSensitivity(v: number) {
    setSensitivity(v);
    if (!videoId) return;
    try {
      const { rallies: rs } = await api.resegment(videoId, { threshold: 1 - v });
      setRallies(rs.map((r) => ({ ...r, included: true })));
    } catch { /* surfaced via UI elsewhere if needed */ }
  }

  async function handleExport() {
    if (!videoId) return;
    const ranges = rallies.filter((r) => r.included).map((r) => ({ start: r.start, end: r.end }));
    const { job_id } = await api.startExport(videoId, ranges);
    setExportJob(job_id);
  }

  const includedCount = rallies.filter((r) => r.included).length;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-900 dark:text-slate-100">
      <header className="flex items-center justify-between px-8 py-5">
        <h1 className="text-xl font-bold">🎾 Pickleball Highlights</h1>
        <ThemeToggle />
      </header>

      <main className="mx-auto flex max-w-3xl flex-col gap-6 px-8 pb-16">
        {!videoId && <UploadView onFile={handleFile} error={uploadError} />}

        {detectJob && detect.status === "running" && (
          <ProgressBar label="Detecting rallies…" fraction={detect.progress} />
        )}
        {detect.status === "error" && (
          <p className="text-sm text-red-500">Detection failed: {detect.error}</p>
        )}

        {videoId && !detectJob && (
          <>
            <Player ref={player} src={api.videoUrl(videoId)} />
            <Timeline rallies={rallies} duration={duration}
                      onChange={(i, next) => setRallies((rs) =>
                        rs.map((r, j) => (j === i ? { ...r, ...next } : r)))}
                      onPreview={(t) => { player.current?.seekTo(t); }} />
            <Controls sensitivity={sensitivity} onSensitivity={handleSensitivity}
                      onExport={handleExport} exportDisabled={includedCount === 0} />
            <RallyList rallies={rallies}
                       onToggle={(i) => setRallies((rs) =>
                         rs.map((r, j) => (j === i ? { ...r, included: !r.included } : r)))}
                       onJump={(t) => { player.current?.seekTo(t); player.current?.play(); }} />

            {exportJob && exp.status === "running" && (
              <ProgressBar label="Exporting…" fraction={exp.progress} />
            )}
            {exp.status === "error" && (
              <p className="text-sm text-red-500">Export failed: {exp.error}</p>
            )}
            {exp.status === "done" && exp.result && <ResultPanel result={exp.result} />}
          </>
        )}
      </main>
    </div>
  );
}
```

- [ ] **Step 3: Build to verify it compiles**

Run: `cd frontend && npm run build`
Expected: PASS — no TypeScript errors, `dist/` regenerated.

- [ ] **Step 4: Run all frontend tests**

Run: `cd frontend && npm run test`
Expected: PASS (api + useJob + timeline-math; 13 tests).

- [ ] **Step 5: Apply visual polish with the frontend-design skill**

Invoke the `frontend-design` skill to refine the aesthetic (typography scale, spacing rhythm, accent palette, the timeline as centerpiece, light/dark balance) so it reads as distinctive rather than templated. Keep all component prop contracts and the flow unchanged; only adjust classes/markup styling. Re-run `npm run build` and `npm run test` afterward; both must stay green.

- [ ] **Step 6: Checkpoint** — `cd frontend && npm run build && npm run test`. Green.

---

