import { Play } from "lucide-react";
import type { Rally } from "../types";

function fmtTime(s: number): string {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

export function RallyList({ rallies, onToggle, onJump, onPlay }: {
  rallies: Rally[];
  onToggle: (i: number) => void;
  onJump: (t: number) => void;
  onPlay: (rally: Rally) => void;
}) {
  if (!rallies.length) {
    return (
      <p className="text-sm text-[var(--muted)]">
        No rallies found — nudge sensitivity up.
      </p>
    );
  }
  return (
    <ul className="flex flex-col divide-y divide-[var(--line)]">
      {rallies.map((r, i) => (
        <li key={i} className="flex items-center gap-3 py-2 px-2 rounded
                               hover:bg-[var(--surface)] transition-colors duration-100">
          <input
            type="checkbox"
            checked={r.included}
            onChange={() => onToggle(i)}
            className="h-4 w-4 rounded accent-[var(--teal)]
                       focus-visible:outline-2 focus-visible:outline-[var(--teal)]"
          />
          <button
            onClick={(e) => { e.stopPropagation(); onPlay(r); }}
            className="p-1 rounded text-[var(--teal)] hover:text-[var(--accent)]
                       focus-visible:outline-2 focus-visible:outline-[var(--teal)]"
            aria-label={`Play rally ${i + 1}`}
          >
            <Play size={14} />
          </button>
          <button
            onClick={() => onJump(r.start)}
            className="flex flex-1 items-baseline gap-3 text-left text-sm
                       focus-visible:outline-2 focus-visible:outline-[var(--teal)] focus-visible:outline-offset-2 rounded"
          >
            <span className="font-medium text-[var(--ink)]">Rally {i + 1}</span>
            <span className="font-mono text-xs text-[var(--muted)]">
              {fmtTime(r.start)} – {fmtTime(r.end)}
            </span>
            <span className="ml-auto font-mono text-xs text-[var(--muted)]">
              conf {r.confidence.toFixed(2)}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}
