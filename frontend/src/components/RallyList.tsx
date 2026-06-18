import { Play } from "lucide-react";
import type { Rally } from "../types";

function fmtTime(s: number): string {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

type ViewMode = "serve" | "rally";

interface Clip {
  rallyIndex: number;
  mode: ViewMode;
  start: number;
  end: number;
  serveResolved: boolean;
  included: boolean;
}

function buildClips(rallies: Rally[], view: ViewMode[]): Clip[] {
  const clips: Clip[] = [];
  rallies.forEach((r, i) => {
    if (view.includes("serve")) {
      clips.push({
        rallyIndex: i,
        mode: "serve",
        start: r.serveStart,
        end: r.serveEnd,
        serveResolved: r.serveResolved,
        included: r.included,
      });
    }
    if (view.includes("rally")) {
      clips.push({
        rallyIndex: i,
        mode: "rally",
        start: r.start,
        end: r.end,
        serveResolved: true,
        included: r.included,
      });
    }
  });
  return clips;
}

export function RallyList({ rallies, view, onViewChange, onToggle, onJump, onPlay }: {
  rallies: Rally[];
  view: ViewMode[];
  onViewChange: (v: ViewMode[]) => void;
  onToggle: (i: number) => void;
  onJump: (t: number) => void;
  onPlay: (rally: Rally) => void;
}) {
  function toggleChip(mode: ViewMode) {
    if (view.includes(mode)) {
      // keep at least one chip active
      if (view.length === 1) return;
      onViewChange(view.filter((v) => v !== mode));
    } else {
      onViewChange([...view, mode]);
    }
  }

  const chips: { label: string; mode: ViewMode }[] = [
    { label: "Rally", mode: "rally" },
    { label: "Serve", mode: "serve" },
  ];

  const clips = buildClips(rallies, view);

  return (
    <div className="flex flex-col gap-3">
      {/* Chip filter row */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-[var(--muted)] font-medium">Show:</span>
        {chips.map(({ label, mode }) => {
          const active = view.includes(mode);
          return (
            <button
              key={mode}
              onClick={() => toggleChip(mode)}
              className={[
                "rounded-full px-3 py-1 text-xs font-medium border transition-colors",
                active
                  ? "bg-[var(--teal)] border-[var(--teal)] text-white"
                  : "bg-transparent border-[var(--line)] text-[var(--muted)] hover:border-[var(--teal)] hover:text-[var(--teal)]",
              ].join(" ")}
            >
              {label}
            </button>
          );
        })}
      </div>

      {/* Clip list */}
      {clips.length === 0 ? (
        <p className="text-sm text-[var(--muted)]">
          No rallies found — nudge sensitivity up.
        </p>
      ) : (
        <ul className="flex flex-col divide-y divide-[var(--line)]">
          {clips.map((clip, ci) => {
            const rally = rallies[clip.rallyIndex];
            const clipLabel =
              view.includes("serve") && view.includes("rally")
                ? `Rally ${clip.rallyIndex + 1} (${clip.mode === "serve" ? "Serve" : "Rally"})`
                : `Rally ${clip.rallyIndex + 1}`;

            return (
              <li
                key={ci}
                className="flex items-center gap-3 py-2 px-2 rounded
                           hover:bg-[var(--surface)] transition-colors duration-100"
              >
                <input
                  type="checkbox"
                  checked={clip.included}
                  onChange={() => onToggle(clip.rallyIndex)}
                  className="h-4 w-4 rounded accent-[var(--teal)]
                             focus-visible:outline-2 focus-visible:outline-[var(--teal)]"
                />
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    // play the specific clip range via a synthetic rally-like object
                    onPlay({ ...rally, start: clip.start, end: clip.end });
                  }}
                  className="p-1 rounded text-[var(--teal)] hover:text-[var(--accent)]
                             focus-visible:outline-2 focus-visible:outline-[var(--teal)]"
                  aria-label={`Play ${clipLabel}`}
                >
                  <Play size={14} />
                </button>
                <button
                  onClick={() => onJump(clip.start)}
                  className="flex flex-1 items-baseline gap-3 text-left text-sm
                             focus-visible:outline-2 focus-visible:outline-[var(--teal)]
                             focus-visible:outline-offset-2 rounded"
                >
                  <span className="font-medium text-[var(--ink)]">{clipLabel}</span>
                  {/* Fallback-serve badge: shown when serve_resolved is false */}
                  {clip.mode === "serve" && !clip.serveResolved && (
                    <span
                      title="Serve window is estimated (no paddle onsets detected)"
                      className="text-[10px] font-mono text-[var(--muted)] opacity-60 select-none"
                    >
                      ≈
                    </span>
                  )}
                  <span className="font-mono text-xs text-[var(--muted)]">
                    {fmtTime(clip.start)} – {fmtTime(clip.end)}
                  </span>
                  <span className="ml-auto font-mono text-xs text-[var(--muted)]">
                    conf {rally.confidence.toFixed(2)}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
