# Task 9 (modern-frontend)

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

## Task 9: Presentational components (frontend)

**Files:**
- Create: `frontend/src/components/ProgressBar.tsx`, `Player.tsx`, `UploadView.tsx`, `RallyList.tsx`, `Controls.tsx`, `ThemeToggle.tsx`, `ResultPanel.tsx`

**Interfaces:**
- Produces (props are the contract App wires in Task 10):
  - `ProgressBar({label, fraction})`
  - `Player` — `forwardRef<PlayerHandle, {src:string}>`; `PlayerHandle = {seekTo(t):void; play():void}`.
  - `UploadView({onFile, error})`
  - `RallyList({rallies, onToggle, onJump})`
  - `Controls({sensitivity, onSensitivity, onExport, exportDisabled})`
  - `ThemeToggle()`
  - `ResultPanel({result})` where result is `{clips:string[]; stitched:string|null}`.

- [ ] **Step 1: Create `frontend/src/components/ProgressBar.tsx`**

```tsx
export function ProgressBar({ label, fraction }: { label: string; fraction: number }) {
  const pct = Math.round(Math.min(1, Math.max(0, fraction)) * 100);
  return (
    <div className="w-full">
      <div className="mb-1 flex justify-between text-sm text-slate-600 dark:text-slate-300">
        <span>{label}</span><span>{pct}%</span>
      </div>
      <div className="h-3 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
        <div className="h-full rounded-full bg-emerald-500 transition-all duration-200"
             style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create `frontend/src/components/Player.tsx`**

```tsx
import { forwardRef, useImperativeHandle, useRef } from "react";

export interface PlayerHandle { seekTo(t: number): void; play(): void; }

export const Player = forwardRef<PlayerHandle, { src: string }>(({ src }, ref) => {
  const v = useRef<HTMLVideoElement>(null);
  useImperativeHandle(ref, () => ({
    seekTo(t) { if (v.current) v.current.currentTime = t; },
    play() { v.current?.play(); },
  }));
  return (
    <video ref={v} src={src} controls
           className="w-full rounded-lg bg-black shadow-lg" />
  );
});
```

- [ ] **Step 3: Create `frontend/src/components/UploadView.tsx`**

```tsx
import { Upload } from "lucide-react";

export function UploadView({ onFile, error }: { onFile: (f: File) => void; error: string | null }) {
  return (
    <div className="flex flex-col items-center gap-4">
      <label className="flex cursor-pointer flex-col items-center gap-3 rounded-2xl border-2
                        border-dashed border-slate-300 px-12 py-16 transition hover:border-emerald-500
                        dark:border-slate-600">
        <Upload className="h-10 w-10 text-emerald-500" />
        <span className="text-lg font-medium">Drop a match video or click to choose</span>
        <span className="text-sm text-slate-500">Fixed-camera footage works best</span>
        <input type="file" accept="video/*" className="hidden"
               onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])} />
      </label>
      {error && <p className="text-sm text-red-500">{error}</p>}
    </div>
  );
}
```

- [ ] **Step 4: Create `frontend/src/components/RallyList.tsx`**

```tsx
import type { Rally } from "../types";

export function RallyList({ rallies, onToggle, onJump }: {
  rallies: Rally[];
  onToggle: (i: number) => void;
  onJump: (t: number) => void;
}) {
  if (!rallies.length) {
    return <p className="text-sm text-slate-500">No rallies — try raising sensitivity.</p>;
  }
  return (
    <ul className="flex flex-col gap-1">
      {rallies.map((r, i) => (
        <li key={i} className="flex items-center gap-3 rounded-lg px-3 py-2
                               hover:bg-slate-100 dark:hover:bg-slate-800">
          <input type="checkbox" checked={r.included} onChange={() => onToggle(i)}
                 className="h-4 w-4 accent-emerald-500" />
          <button onClick={() => onJump(r.start)} className="flex-1 text-left text-sm">
            Rally {i + 1}: {r.start.toFixed(1)}s – {r.end.toFixed(1)}s
            <span className="ml-2 text-slate-400">conf {r.confidence.toFixed(2)}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}
```

- [ ] **Step 5: Create `frontend/src/components/Controls.tsx`**

```tsx
import { Scissors } from "lucide-react";

export function Controls({ sensitivity, onSensitivity, onExport, exportDisabled }: {
  sensitivity: number;
  onSensitivity: (v: number) => void;
  onExport: () => void;
  exportDisabled: boolean;
}) {
  return (
    <div className="flex flex-wrap items-center gap-6">
      <label className="flex items-center gap-3 text-sm">
        Sensitivity
        <input type="range" min={0} max={1} step={0.05} value={sensitivity}
               onChange={(e) => onSensitivity(parseFloat(e.target.value))}
               className="accent-emerald-500" />
      </label>
      <button onClick={onExport} disabled={exportDisabled}
              className="flex items-center gap-2 rounded-lg bg-emerald-500 px-4 py-2 font-medium
                         text-white transition hover:bg-emerald-600 disabled:opacity-40">
        <Scissors className="h-4 w-4" /> Export
      </button>
    </div>
  );
}
```

- [ ] **Step 6: Create `frontend/src/components/ThemeToggle.tsx`**

```tsx
import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

export function ThemeToggle() {
  const [dark, setDark] = useState(
    () => window.matchMedia("(prefers-color-scheme: dark)").matches,
  );
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);
  return (
    <button onClick={() => setDark((d) => !d)} aria-label="Toggle theme"
            className="rounded-lg p-2 hover:bg-slate-100 dark:hover:bg-slate-800">
      {dark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
    </button>
  );
}
```

- [ ] **Step 7: Create `frontend/src/components/ResultPanel.tsx`**

```tsx
export function ResultPanel({ result }: { result: { clips: string[]; stitched: string | null } }) {
  return (
    <div className="rounded-lg bg-slate-100 p-4 text-sm dark:bg-slate-800">
      <p className="font-medium text-emerald-600 dark:text-emerald-400">Export complete</p>
      {result.stitched && <p className="mt-2 break-all">Stitched: {result.stitched}</p>}
      <p className="mt-2 break-all">Clips: {result.clips.length}</p>
      <ul className="mt-1 list-inside list-disc break-all text-slate-500">
        {result.clips.map((c) => <li key={c}>{c}</li>)}
      </ul>
    </div>
  );
}
```

- [ ] **Step 8: Checkpoint** — `cd frontend && npm run build`. Compiles with no TS errors (unused-locals/params are errors per tsconfig, so every prop must be used). `npm run test` still green.

---

