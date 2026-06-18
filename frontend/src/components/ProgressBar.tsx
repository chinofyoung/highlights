export function ProgressBar({ label, fraction }: { label: string; fraction: number }) {
  const pct = Math.round(Math.min(1, Math.max(0, fraction)) * 100);
  return (
    <div className="w-full">
      <div className="mb-1.5 flex justify-between text-sm">
        <span className="text-[var(--ink)]">{label}</span>
        <span className="font-mono text-xs text-[var(--muted)]">{pct}%</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-[var(--line)]">
        <div
          className="h-full rounded-full bg-[var(--teal)] transition-all duration-200"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
