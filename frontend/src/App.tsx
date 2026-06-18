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
import { HighlightsView } from "./components/HighlightsView";
import { DraftsSection } from "./components/DraftsSection";
import { LibrarySection } from "./components/LibrarySection";

export default function App() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [videoId, setVideoId] = useState<string | null>(null);
  const [duration, setDuration] = useState(0);
  const [rallies, setRallies] = useState<Rally[]>([]);
  const [view, setView] = useState<("serve" | "rally")[]>(["rally"]);
  const [sensitivity, setSensitivity] = useState(0.5);
  const [detectJob, setDetectJob] = useState<string | null>(null);
  const [exportJob, setExportJob] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [libraryView, setLibraryView] = useState(false);
  const player = useRef<PlayerHandle>(null);

  const detect = useJob(detectJob);
  const exp = useJob(exportJob);

  // detect job completed → load rallies
  if (detect.status === "done" && detectJob && detect.result) {
    const rs: Rally[] = detect.result.rallies.map(api.toRally);
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

  function handleOpenProject(videoId: string, duration: number) {
    setVideoId(videoId);
    setDuration(duration);
    setRallies([]);
    setExportJob(null);
    setLibraryView(true);
  }

  async function handleSensitivity(v: number) {
    setSensitivity(v);
    if (!videoId) return;
    try {
      const { rallies: rs } = await api.resegment(videoId, { threshold: 1 - v });
      setRallies(rs);
    } catch { /* surfaced via UI elsewhere if needed */ }
  }

  async function handleExport() {
    if (!videoId) return;
    const ranges: { start: number; end: number }[] = [];
    for (const r of rallies) {
      if (!r.included) continue;
      if (view.includes("serve")) ranges.push({ start: r.serveStart, end: r.serveEnd });
      if (view.includes("rally")) ranges.push({ start: r.start, end: r.end });
    }
    ranges.sort((a, b) => a.start - b.start);
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
          <>
            <UploadView onFile={handleFileSelected} error={uploadError} />
            <DraftsSection />
            <LibrarySection onOpen={handleOpenProject} />
          </>
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
        {(analyzing || detectJob) && (
          <>
            <BallLoader />
            <ProgressBar label="Finding rallies…" fraction={detect.progress} />
            <button
              disabled={analyzing}
              onClick={async () => {
                if (detectJob) await api.cancelJob(detectJob);
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
          </>
        )}
        {detect.status === "error" && (
          <p className="text-sm text-[var(--danger)]">Detection failed: {detect.error}</p>
        )}

        {/* View 4a: library-view — opened from Library */}
        {libraryView && videoId && (
          <>
            <div className="flex items-center gap-3">
              <button
                onClick={() => { setVideoId(null); setLibraryView(false); setRallies([]); setExportJob(null); }}
                className="rounded border border-[var(--line)] px-3 py-1.5 text-sm text-[var(--muted)] hover:text-[var(--ink)] transition-colors"
              >
                ← Back
              </button>
              <button
                onClick={async () => {
                  const { rallies: rs } = await api.resegment(videoId, { threshold: 1 - sensitivity });
                  setRallies(rs);
                  setLibraryView(false);
                }}
                className="rounded bg-[var(--teal)] px-3 py-1.5 text-sm text-white hover:opacity-90 transition-opacity"
              >
                Re-edit
              </button>
            </div>
            <HighlightsView videoId={videoId} />
          </>
        )}

        {/* View 4: review + export */}
        {videoId && !libraryView && !detectJob && !analyzing && (
          <>
            <Player ref={player} src={api.videoUrl(videoId)} />
            <Timeline rallies={rallies} duration={duration}
                      onChange={(i, next) => setRallies((rs) =>
                        rs.map((r, j) => (j === i ? { ...r, ...next } : r)))}
                      onPreview={(t) => { player.current?.seekTo(t); }} />
            <Controls sensitivity={sensitivity} onSensitivity={handleSensitivity}
                      onExport={handleExport} exportDisabled={includedCount === 0} />
            <RallyList rallies={rallies}
                       view={view}
                       onViewChange={setView}
                       onToggle={(i) => setRallies((rs) =>
                         rs.map((r, j) => (j === i ? { ...r, included: !r.included } : r)))}
                       onJump={(t) => { player.current?.seekTo(t); player.current?.play(); }}
                       onPlay={(r) => player.current?.playSegment(r.start, r.end)} />

            {exportJob && exp.status === "running" && (
              <ProgressBar label="Exporting highlights…" fraction={exp.progress} />
            )}
            {exp.status === "error" && (
              <p className="text-sm text-[var(--danger)]">Export failed: {exp.error}</p>
            )}
            {exp.status === "done" && videoId && <HighlightsView videoId={videoId} />}
          </>
        )}
      </main>
    </div>
  );
}
