# UI Flow Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add real drag-and-drop to the upload zone, introduce a select-then-confirm flow so the app does not auto-analyze on file pick, and show a bouncing-ball animation during detection.

**Architecture:** App.tsx gains a `selectedFile` state that gates three mutually-exclusive views (UploadView → SelectedVideo → detecting/results). UploadView handles drag events locally with a `dragActive` flag. BallLoader is a pure CSS-animated component rendered alongside the existing ProgressBar when a detect job is running.

**Tech Stack:** React 18, TypeScript 5 (strict), Tailwind CSS v4 arbitrary-value syntax, Vitest + React Testing Library, CSS @keyframes in index.css.

## Global Constraints

- Design tokens: `--bg --surface --ink --muted --line --accent --accent-ink --teal --danger` via `bg-[var(--accent)]` Tailwind syntax.
- Fonts: `font-display` (Archivo), `font-body` (Hanken Grotesk), `font-mono` (Space Mono).
- `noUnusedLocals` / `noUnusedParameters` are enabled — every declared variable and prop MUST be used.
- Do NOT change: `api.ts`, `useJob.ts`, `timeline-math.ts`, prop shapes of `ProgressBar`, `Player`, `Timeline`, `RallyList`, `Controls`, `ResultPanel`.
- Do NOT run any git commands.
- `npm run build` must produce 0 TypeScript errors.
- `npm run test` must pass all 13 existing tests plus new ones.
- New tests go in `frontend/src/test/`.
- Report written to `/Users/chinoyoung/Code/highlights/docs/superpowers/plans/briefs-fe/ui-flow-report.md`.
- Working directory for all `npm` commands: `/Users/chinoyoung/Code/highlights/frontend`.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `frontend/src/components/UploadView.tsx` | Modify | Add drag events + `dragActive` visual state |
| `frontend/src/components/SelectedVideo.tsx` | Create | Preview selected file + Analyze / Reset buttons |
| `frontend/src/components/BallLoader.tsx` | Create | Bouncing-ball CSS animation |
| `frontend/src/index.css` | Modify | Add `@keyframes ball-bounce` |
| `frontend/src/App.tsx` | Modify | Add `selectedFile` state + view-gating + deferred analyze logic |
| `frontend/src/test/SelectedVideo.test.tsx` | Create | Unit tests for SelectedVideo |
| `frontend/src/test/App.test.tsx` | Create | Integration test: no-auto-analyze contract |

---

### Task 1: Drag-and-drop in UploadView

**Files:**
- Modify: `frontend/src/components/UploadView.tsx`

**Interfaces:**
- Consumes: existing props `{ onFile: (f: File) => void; error: string | null }` — unchanged.
- Produces: same export `UploadView` — no interface change for callers.

- [ ] **Step 1: Read the current file**

  Open `frontend/src/components/UploadView.tsx`. Confirm it is a `<label>` wrapping a hidden `<input type="file">`.

- [ ] **Step 2: Add `dragActive` state and handlers**

  Replace the entire file content with:

  ```tsx
  import { useState } from "react";
  import { Upload } from "lucide-react";

  export function UploadView({ onFile, error }: { onFile: (f: File) => void; error: string | null }) {
    const [dragActive, setDragActive] = useState(false);

    function handleDragOver(e: React.DragEvent<HTMLLabelElement>) {
      e.preventDefault();
      setDragActive(true);
    }

    function handleDragLeave() {
      setDragActive(false);
    }

    function handleDrop(e: React.DragEvent<HTMLLabelElement>) {
      e.preventDefault();
      setDragActive(false);
      const file = e.dataTransfer.files[0];
      if (file) onFile(file);
    }

    return (
      <div className="flex flex-col items-center gap-6 py-8">
        <div className="text-center">
          <h2 className="font-display text-3xl font-extrabold tracking-tight text-[var(--ink)] sm:text-4xl">
            Find the rallies.<br />Skip the standing around.
          </h2>
          <p className="mt-3 text-[var(--muted)] max-w-md mx-auto">
            Drop in a match recorded from one fixed angle. We'll spot every rally
            so you can cut a highlight reel in minutes.
          </p>
        </div>

        <label
          className={[
            "flex w-full max-w-md cursor-pointer flex-col items-center gap-4 rounded-lg",
            "border-2 border-dashed px-10 py-14",
            "transition-colors duration-150",
            "focus-within:outline-2 focus-within:outline-[var(--teal)] focus-within:outline-offset-2",
            dragActive
              ? "border-[var(--teal)] bg-[var(--accent)]/10"
              : "border-[var(--line)] hover:border-[var(--teal)] hover:bg-[var(--teal)]/5",
          ].join(" ")}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <Upload className="h-9 w-9 text-[var(--teal)]" />
          <span className="text-base font-medium text-[var(--ink)]">
            Drop a match video or click to choose
          </span>
          <span className="text-sm text-[var(--muted)]">
            MP4, MOV, or any format your browser supports
          </span>
          <input
            type="file"
            accept="video/*"
            className="sr-only"
            onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])}
          />
        </label>

        {error && (
          <p className="text-sm text-[var(--danger)]">{error}</p>
        )}
      </div>
    );
  }
  ```

- [ ] **Step 3: Build-check**

  From `frontend/`:
  ```bash
  npm run build
  ```
  Expected: 0 TypeScript errors, build succeeds.

- [ ] **Step 4: Run existing tests**

  ```bash
  npm run test
  ```
  Expected: all 13 existing tests pass (none touch UploadView internals).

---

### Task 2: SelectedVideo component

**Files:**
- Create: `frontend/src/components/SelectedVideo.tsx`
- Create: `frontend/src/test/SelectedVideo.test.tsx`

**Interfaces:**
- Produces: `export function SelectedVideo({ file, onAnalyze, onReset, analyzing }: { file: File; onAnalyze: () => void; onReset: () => void; analyzing: boolean })`
  - `file`: the File to preview
  - `onAnalyze`: called when user clicks "Analyze video"
  - `onReset`: called when user clicks "Choose a different video"
  - `analyzing`: when true, disable the Analyze button and show busy state

  Note: the spec says props `{ file, onAnalyze, onReset }` but we add `analyzing: boolean` so the parent can disable the button while the upload is in-flight. All props are used.

- [ ] **Step 1: Write the failing test first**

  Create `frontend/src/test/SelectedVideo.test.tsx`:

  ```tsx
  import { describe, it, expect, vi } from "vitest";
  import { render, screen } from "@testing-library/react";
  import userEvent from "@testing-library/user-event";
  import { SelectedVideo } from "../components/SelectedVideo";

  function makeFile(name = "match.mp4", sizeBytes = 1024 * 1024 * 50) {
    return new File([new ArrayBuffer(0)], name, { type: "video/mp4" }) as File & { size: number };
  }

  describe("SelectedVideo", () => {
    it("renders the file name", () => {
      render(
        <SelectedVideo
          file={makeFile("rally-game.mp4")}
          onAnalyze={vi.fn()}
          onReset={vi.fn()}
          analyzing={false}
        />
      );
      expect(screen.getByText(/rally-game\.mp4/)).toBeInTheDocument();
    });

    it("calls onAnalyze when Analyze video button is clicked", async () => {
      const onAnalyze = vi.fn();
      render(
        <SelectedVideo
          file={makeFile()}
          onAnalyze={onAnalyze}
          onReset={vi.fn()}
          analyzing={false}
        />
      );
      await userEvent.click(screen.getByRole("button", { name: /analyze video/i }));
      expect(onAnalyze).toHaveBeenCalledOnce();
    });

    it("calls onReset when Choose a different video is clicked", async () => {
      const onReset = vi.fn();
      render(
        <SelectedVideo
          file={makeFile()}
          onAnalyze={vi.fn()}
          onReset={onReset}
          analyzing={false}
        />
      );
      await userEvent.click(screen.getByRole("button", { name: /choose a different video/i }));
      expect(onReset).toHaveBeenCalledOnce();
    });

    it("disables Analyze button and shows busy text when analyzing=true", () => {
      render(
        <SelectedVideo
          file={makeFile()}
          onAnalyze={vi.fn()}
          onReset={vi.fn()}
          analyzing={true}
        />
      );
      const btn = screen.getByRole("button", { name: /uploading/i });
      expect(btn).toBeDisabled();
    });
  });
  ```

- [ ] **Step 2: Run test to confirm it fails**

  ```bash
  npm run test -- --reporter=verbose 2>&1 | head -40
  ```
  Expected: FAIL — `SelectedVideo` module not found.

- [ ] **Step 3: Install @testing-library/user-event if needed**

  Check whether it's already installed:
  ```bash
  ls /Users/chinoyoung/Code/highlights/frontend/node_modules/@testing-library/ 2>/dev/null
  ```
  If `user-event` is NOT listed, install it:
  ```bash
  npm install --save-dev @testing-library/user-event
  ```
  If it IS listed, skip this step.

- [ ] **Step 4: Create SelectedVideo.tsx**

  Create `frontend/src/components/SelectedVideo.tsx`:

  ```tsx
  import { useEffect, useState } from "react";

  export function SelectedVideo({
    file,
    onAnalyze,
    onReset,
    analyzing,
  }: {
    file: File;
    onAnalyze: () => void;
    onReset: () => void;
    analyzing: boolean;
  }) {
    const [objectUrl, setObjectUrl] = useState<string | null>(null);

    useEffect(() => {
      const url = URL.createObjectURL(file);
      setObjectUrl(url);
      return () => { URL.revokeObjectURL(url); };
    }, [file]);

    const sizeMB = (file.size / (1024 * 1024)).toFixed(1);

    return (
      <div className="flex flex-col items-center gap-6 py-8">
        <div className="text-center">
          <h2 className="font-display text-2xl font-extrabold tracking-tight text-[var(--ink)]">
            Ready to analyze
          </h2>
          <p className="mt-2 font-mono text-sm text-[var(--muted)]">
            {file.name}
            <span className="ml-2 text-[var(--muted)]">· {sizeMB} MB</span>
          </p>
        </div>

        {objectUrl && (
          <video
            controls
            src={objectUrl}
            className="w-full max-w-xl rounded-lg border border-[var(--line)] bg-black"
          />
        )}

        <div className="flex flex-col items-center gap-3 sm:flex-row">
          <button
            onClick={onAnalyze}
            disabled={analyzing}
            className="flex items-center gap-2 rounded bg-[var(--accent)] px-6 py-2.5 text-sm font-semibold
                       text-[var(--accent-ink)] transition-colors duration-150
                       hover:brightness-95
                       disabled:opacity-50 disabled:cursor-not-allowed
                       focus-visible:outline-2 focus-visible:outline-[var(--teal)] focus-visible:outline-offset-2"
          >
            {analyzing ? "Uploading…" : "Analyze video"}
          </button>

          <button
            onClick={onReset}
            disabled={analyzing}
            className="rounded px-4 py-2.5 text-sm font-medium text-[var(--muted)]
                       hover:text-[var(--ink)] transition-colors duration-150
                       disabled:opacity-50 disabled:cursor-not-allowed
                       focus-visible:outline-2 focus-visible:outline-[var(--teal)] focus-visible:outline-offset-2"
          >
            Choose a different video
          </button>
        </div>
      </div>
    );
  }
  ```

- [ ] **Step 5: Run tests to confirm they pass**

  ```bash
  npm run test
  ```
  Expected: all prior tests pass + all 4 new SelectedVideo tests pass.

- [ ] **Step 6: Build-check**

  ```bash
  npm run build
  ```
  Expected: 0 TypeScript errors.

---

### Task 3: BallLoader component + @keyframes

**Files:**
- Create: `frontend/src/components/BallLoader.tsx`
- Modify: `frontend/src/index.css` (add `@keyframes ball-bounce` + `.ball-bounce` class)

**Interfaces:**
- Produces: `export function BallLoader()` — no props. Self-contained animation.

- [ ] **Step 1: Add keyframes to index.css**

  Open `frontend/src/index.css`. After the existing `@keyframes segment-in` block (around line 41), add:

  ```css
  @media (prefers-reduced-motion: no-preference) {
    @keyframes ball-bounce {
      0%, 100% {
        transform: translateY(0);
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.20);
      }
      50% {
        transform: translateY(-28px);
        box-shadow: 0 24px 32px rgba(0, 0, 0, 0.08);
      }
    }
  }

  @media (prefers-reduced-motion: reduce) {
    @keyframes ball-pulse {
      0%, 100% { opacity: 1; }
      50%       { opacity: 0.4; }
    }
  }

  .ball-bounce {
    animation: ball-bounce 0.65s cubic-bezier(0.33, 0, 0.66, 1) infinite;
  }

  @media (prefers-reduced-motion: reduce) {
    .ball-bounce {
      animation: ball-pulse 1.2s ease-in-out infinite;
    }
  }
  ```

  The full updated section between `@keyframes segment-in` and `.segment-animate` should now look like this (add the new blocks AFTER the segment-in block, BEFORE .segment-animate):

  ```css
  @keyframes segment-in {
    from { opacity: 0; transform: scaleX(0.8); }
    to   { opacity: 1; transform: scaleX(1); }
  }

  @media (prefers-reduced-motion: no-preference) {
    @keyframes ball-bounce {
      0%, 100% {
        transform: translateY(0);
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.20);
      }
      50% {
        transform: translateY(-28px);
        box-shadow: 0 24px 32px rgba(0, 0, 0, 0.08);
      }
    }
  }

  @media (prefers-reduced-motion: reduce) {
    @keyframes ball-pulse {
      0%, 100% { opacity: 1; }
      50%       { opacity: 0.4; }
    }
  }

  .ball-bounce {
    animation: ball-bounce 0.65s cubic-bezier(0.33, 0, 0.66, 1) infinite;
  }

  @media (prefers-reduced-motion: reduce) {
    .ball-bounce {
      animation: ball-pulse 1.2s ease-in-out infinite;
    }
  }

  .segment-animate {
    animation: segment-in 0.25s ease-out both;
    transform-origin: left center;
  }

  @media (prefers-reduced-motion: reduce) {
    .segment-animate {
      animation: none;
    }
    * {
      transition-duration: 0.01ms !important;
      animation-duration: 0.01ms !important;
    }
  }
  ```

  Note: The existing `@media (prefers-reduced-motion: reduce)` block that resets ALL animations must stay at the bottom. The `.ball-bounce` reduced-motion override is redundant with the global `animation-duration: 0.01ms !important` but is explicit for clarity.

- [ ] **Step 2: Create BallLoader.tsx**

  Create `frontend/src/components/BallLoader.tsx`:

  ```tsx
  export function BallLoader() {
    return (
      <div className="flex justify-center py-2">
        <div
          className="ball-bounce h-8 w-8 rounded-full bg-[var(--accent)]"
          aria-hidden="true"
        />
      </div>
    );
  }
  ```

  The ball is 32×32px optic-lime circle. The `aria-hidden` hides it from screen readers (the ProgressBar label "Finding rallies…" already conveys the state). The bounce and shadow are handled by `.ball-bounce` from index.css.

- [ ] **Step 3: Build-check**

  ```bash
  npm run build
  ```
  Expected: 0 TypeScript errors.

- [ ] **Step 4: Run tests**

  ```bash
  npm run test
  ```
  Expected: all prior tests still pass.

---

### Task 4: Wire everything together in App.tsx + integration test

**Files:**
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/test/App.test.tsx`

**Interfaces:**
- Consumes:
  - `SelectedVideo` from `./components/SelectedVideo` — props `{ file: File; onAnalyze: () => void; onReset: () => void; analyzing: boolean }`
  - `BallLoader` from `./components/BallLoader` — no props
  - Existing `api.uploadVideo`, `api.startDetect` — signatures unchanged
- Produces: no new exports; App remains the default export.

**View-gating logic:**
```
!selectedFile && !videoId          → <UploadView>
selectedFile && !videoId           → <SelectedVideo>
detectJob running                  → <BallLoader> + <ProgressBar>
!detectJob && videoId set          → review UI (Player + Timeline + …)
```

- [ ] **Step 1: Write the failing integration test**

  Create `frontend/src/test/App.test.tsx`:

  ```tsx
  import { describe, it, expect, vi, beforeEach } from "vitest";
  import { render, screen, waitFor } from "@testing-library/react";
  import userEvent from "@testing-library/user-event";
  import App from "../App";
  import * as api from "../api";

  // Mock the entire api module so no real fetch happens
  vi.mock("../api", () => ({
    uploadVideo: vi.fn(),
    startDetect: vi.fn(),
    startExport: vi.fn(),
    getJob: vi.fn(),
    resegment: vi.fn(),
    videoUrl: vi.fn((id: string) => `/api/video/${id}`),
  }));

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("App — no-auto-analyze contract", () => {
    it("shows UploadView initially", () => {
      render(<App />);
      expect(screen.getByText(/find the rallies/i)).toBeInTheDocument();
    });

    it("selecting a file shows SelectedVideo and does NOT call startDetect", async () => {
      render(<App />);

      const input = document.querySelector<HTMLInputElement>("input[type=file]")!;
      const file = new File(["video"], "match.mp4", { type: "video/mp4" });

      await userEvent.upload(input, file);

      // SelectedVideo should now be visible
      await waitFor(() =>
        expect(screen.getByRole("button", { name: /analyze video/i })).toBeInTheDocument()
      );

      // startDetect must NOT have been called yet
      expect(api.startDetect).not.toHaveBeenCalled();
      expect(api.uploadVideo).not.toHaveBeenCalled();
    });

    it("clicking Analyze video calls uploadVideo then startDetect", async () => {
      vi.mocked(api.uploadVideo).mockResolvedValue({ video_id: "v1", duration: 120 });
      vi.mocked(api.startDetect).mockResolvedValue({ job_id: "j1" });
      vi.mocked(api.getJob).mockResolvedValue({
        status: "running",
        progress: 0,
        result: null,
        error: null,
      });

      render(<App />);

      const input = document.querySelector<HTMLInputElement>("input[type=file]")!;
      const file = new File(["video"], "match.mp4", { type: "video/mp4" });
      await userEvent.upload(input, file);

      await waitFor(() =>
        expect(screen.getByRole("button", { name: /analyze video/i })).toBeInTheDocument()
      );

      await userEvent.click(screen.getByRole("button", { name: /analyze video/i }));

      await waitFor(() => expect(api.uploadVideo).toHaveBeenCalledWith(file));
      await waitFor(() => expect(api.startDetect).toHaveBeenCalledWith("v1", { threshold: 0.5 }));
    });

    it("Reset button returns to UploadView", async () => {
      render(<App />);

      const input = document.querySelector<HTMLInputElement>("input[type=file]")!;
      const file = new File(["video"], "match.mp4", { type: "video/mp4" });
      await userEvent.upload(input, file);

      await waitFor(() =>
        expect(screen.getByRole("button", { name: /choose a different video/i })).toBeInTheDocument()
      );

      await userEvent.click(screen.getByRole("button", { name: /choose a different video/i }));

      await waitFor(() =>
        expect(screen.getByText(/find the rallies/i)).toBeInTheDocument()
      );
    });
  });
  ```

- [ ] **Step 2: Run tests to confirm new tests fail**

  ```bash
  npm run test -- --reporter=verbose 2>&1 | grep -A3 "App —"
  ```
  Expected: tests in `App.test.tsx` FAIL (App still auto-analyzes / SelectedVideo not imported).

- [ ] **Step 3: Rewrite App.tsx**

  Replace the full content of `frontend/src/App.tsx` with:

  ```tsx
  import { useRef, useState } from "react";
  import * as api from "./api";
  import { useJob } from "./useJob";
  import type { Rally } from "./types";
  import { UploadView } from "./components/UploadView";
  import { SelectedVideo } from "./components/SelectedVideo";
  import { BallLoader } from "./components/BallLoader";
  import { ProgressBar } from "./components/ProgressBar";
  import { Player, type PlayerHandle } from "./components/Player";
  import { Timeline } from "./components/Timeline";
  import { RallyList } from "./components/RallyList";
  import { Controls } from "./components/Controls";
  import { ThemeToggle } from "./components/ThemeToggle";
  import { ResultPanel } from "./components/ResultPanel";

  export default function App() {
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [videoId, setVideoId] = useState<string | null>(null);
    const [duration, setDuration] = useState(0);
    const [rallies, setRallies] = useState<Rally[]>([]);
    const [sensitivity, setSensitivity] = useState(0.5);
    const [detectJob, setDetectJob] = useState<string | null>(null);
    const [exportJob, setExportJob] = useState<string | null>(null);
    const [uploadError, setUploadError] = useState<string | null>(null);
    const [analyzing, setAnalyzing] = useState(false);
    const player = useRef<PlayerHandle>(null);

    const detect = useJob(detectJob);
    const exp = useJob(exportJob);

    // detect job completed → load rallies
    if (detect.status === "done" && detectJob && detect.result) {
      const rs: Rally[] = detect.result.rallies.map((r: any) => ({ ...r, included: true }));
      setRallies(rs);
      setDetectJob(null);
    }

    function handleFileSelected(file: File) {
      setUploadError(null);
      setSelectedFile(file);
    }

    async function handleAnalyze() {
      if (!selectedFile) return;
      setUploadError(null);
      setAnalyzing(true);
      try {
        const up = await api.uploadVideo(selectedFile);
        setVideoId(up.video_id);
        setDuration(up.duration);
        setSelectedFile(null);
        const { job_id } = await api.startDetect(up.video_id, { threshold: 1 - sensitivity });
        setDetectJob(job_id);
      } catch (e) {
        setUploadError(String(e instanceof Error ? e.message : e));
      } finally {
        setAnalyzing(false);
      }
    }

    function handleReset() {
      setSelectedFile(null);
      setUploadError(null);
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
      <div className="min-h-screen bg-[var(--bg)] text-[var(--ink)]">
        <header className="flex items-center justify-between border-b border-[var(--line)] px-6 py-4 sm:px-8">
          <h1 className="font-display text-lg font-bold tracking-tight text-[var(--ink)]">
            Pickleball<span className="text-[var(--teal)]">.</span>highlights
          </h1>
          <ThemeToggle />
        </header>

        <main className="mx-auto flex max-w-3xl flex-col gap-6 px-4 pb-16 pt-8 sm:px-8">
          {/* View 1: no file selected, no video uploaded */}
          {!selectedFile && !videoId && (
            <UploadView onFile={handleFileSelected} error={uploadError} />
          )}

          {/* View 2: file selected, not yet uploaded/detecting */}
          {selectedFile && !videoId && (
            <SelectedVideo
              file={selectedFile}
              onAnalyze={handleAnalyze}
              onReset={handleReset}
              analyzing={analyzing}
            />
          )}

          {/* View 3: detecting */}
          {detectJob && detect.status === "running" && (
            <>
              <BallLoader />
              <ProgressBar label="Finding rallies…" fraction={detect.progress} />
            </>
          )}
          {detect.status === "error" && (
            <p className="text-sm text-[var(--danger)]">Detection failed: {detect.error}</p>
          )}

          {/* View 4: review + export */}
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
                <ProgressBar label="Exporting highlights…" fraction={exp.progress} />
              )}
              {exp.status === "error" && (
                <p className="text-sm text-[var(--danger)]">Export failed: {exp.error}</p>
              )}
              {exp.status === "done" && exp.result && <ResultPanel result={exp.result} />}
            </>
          )}
        </main>
      </div>
    );
  }
  ```

- [ ] **Step 4: Run all tests**

  ```bash
  npm run test
  ```
  Expected: all 13 original tests + 4 SelectedVideo tests + 4 App tests = 21 total, all passing.

  If any test fails, investigate and fix before proceeding. Common issues:
  - `@testing-library/user-event` not installed → `npm install --save-dev @testing-library/user-event`
  - `vi.mock("../api")` path issues → check the relative path from `src/test/App.test.tsx` to `src/api.ts` (should be `../api`).

- [ ] **Step 5: Final build-check**

  ```bash
  npm run build
  ```
  Expected: 0 TypeScript errors, build artifacts in `dist/`.

---

### Task 5: Write the report

**Files:**
- Create: `/Users/chinoyoung/Code/highlights/docs/superpowers/plans/briefs-fe/ui-flow-report.md`

**Interfaces:**
- Consumes: final build output and test output from Task 4.

- [ ] **Step 1: Capture build and test output**

  ```bash
  cd /Users/chinoyoung/Code/highlights/frontend && npm run build 2>&1
  ```
  ```bash
  cd /Users/chinoyoung/Code/highlights/frontend && npm run test 2>&1
  ```
  Copy the relevant summary lines.

- [ ] **Step 2: Write the report**

  Create `/Users/chinoyoung/Code/highlights/docs/superpowers/plans/briefs-fe/ui-flow-report.md` with the following sections:

  1. **Files created/modified** — table of path, action, summary
  2. **Drag-and-drop implementation** — how `dragActive` state + handlers work
  3. **Select/analyze gating** — state machine in App, view conditions
  4. **BallLoader** — how CSS keyframe + reduced-motion is wired
  5. **New tests** — what each test asserts, final count
  6. **Build output** — paste the `tsc -b && vite build` result
  7. **Test output** — paste the vitest summary

  The report must be complete enough that a reviewer can audit the implementation without running it.

---

## Self-Review Checklist

**Spec coverage:**
- [x] Change 1: drag-drop handlers on `<label>`, `dragActive` state, visual tint — Task 1
- [x] Change 1: click-to-pick via existing `<input>` preserved — Task 1
- [x] Change 2: `selectedFile` state, no auto-upload/detect on pick — Task 4 (App rewrite)
- [x] Change 2: `SelectedVideo` component with video preview, file name, Analyze button — Task 2
- [x] Change 2: `onAnalyze` triggers upload then detect — Task 4
- [x] Change 2: `onReset` clears `selectedFile` — Task 4
- [x] Change 2: Analyze button disabled/busy during upload — Task 2 (`analyzing` prop), Task 4 (`analyzing` state)
- [x] Change 2: uploadError shown in UploadView — preserved in App rewrite
- [x] Change 2: `threshold = 1 - sensitivity` preserved — Task 4
- [x] Change 2: view gating — Task 4
- [x] Change 3: `BallLoader` with CSS bounce — Task 3
- [x] Change 3: `@keyframes ball-bounce` in index.css — Task 3
- [x] Change 3: reduced-motion handled — Task 3
- [x] Change 3: BallLoader rendered alongside ProgressBar in detect state — Task 4
- [x] Tests: SelectedVideo unit tests — Task 2
- [x] Tests: App no-auto-analyze contract — Task 4
- [x] Tests: all 13 existing tests preserved — checked in each task
- [x] Report written to correct path — Task 5

**Placeholder scan:** No TBDs, TODOs, or "implement later" in any step. All steps contain complete code.

**Type consistency:**
- `SelectedVideo` prop `analyzing: boolean` is used in Task 2 (test renders with `analyzing={false}` and `analyzing={true}`) and in Task 4 (App passes `analyzing={analyzing}`).
- `handleFileSelected` in App is the `onFile` callback passed to UploadView — correct type `(f: File) => void`.
- `detect.result.rallies` access is guarded by `detect.status === "done" && detect.result` — same pattern as original App.
- `vi.mocked(api.startDetect)` in App.test expects `{ threshold: 0.5 }` which matches `1 - sensitivity` where `sensitivity = 0.5` (default).
