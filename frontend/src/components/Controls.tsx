import { Scissors } from "lucide-react";

export function Controls({ sensitivity, onSensitivity, onExport, exportDisabled }: {
  sensitivity: number;
  onSensitivity: (v: number) => void;
  onExport: () => void;
  exportDisabled: boolean;
}) {
  return (
    <div className="flex flex-wrap items-center gap-4">
      <label className="flex items-center gap-3 text-sm text-[var(--ink)]">
        <span className="font-medium text-[var(--muted)]">Sensitivity</span>
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={sensitivity}
          onChange={(e) => onSensitivity(parseFloat(e.target.value))}
          className="w-28 accent-[var(--teal)] focus-visible:outline-2 focus-visible:outline-[var(--teal)]"
        />
        <span className="font-mono text-xs text-[var(--muted)] w-8 text-right">
          {Math.round(sensitivity * 100)}%
        </span>
      </label>

      <button
        onClick={onExport}
        disabled={exportDisabled}
        className="flex items-center gap-2 rounded bg-[var(--accent)] px-4 py-2 text-sm font-semibold
                   text-[var(--accent-ink)] transition-colors duration-150
                   hover:brightness-95
                   disabled:opacity-40 disabled:cursor-not-allowed
                   focus-visible:outline-2 focus-visible:outline-[var(--teal)] focus-visible:outline-offset-2"
      >
        <Scissors className="h-4 w-4" />
        Export highlights
      </button>
    </div>
  );
}
