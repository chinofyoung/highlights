import { useRef } from "react";
import type { Rally } from "../types";
import { pxToTime, clampStart, clampEnd, moveBody, MIN_GAP } from "../timeline-math";

type Drag = { index: number; mode: "start" | "end" | "body"; startX: number; orig: Rally } | null;

function fmtTime(s: number): string {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

export function Timeline({ rallies, duration, onChange, onPreview }: {
  rallies: Rally[];
  duration: number;
  onChange: (index: number, next: { start: number; end: number }) => void;
  onPreview: (t: number) => void;
}) {
  const track = useRef<HTMLDivElement>(null);
  const drag = useRef<Drag>(null);

  const endDrag = () => { drag.current = null; };

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

  return (
    <div className="space-y-1">
      {/* Court strip — the signature element */}
      <div
        ref={track}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
        onLostPointerCapture={endDrag}
        className="relative h-14 w-full overflow-hidden rounded bg-[var(--surface)] border border-[var(--line)]"
        style={{ touchAction: "none" }}
      >
        {/* Center line — evoking the pickleball court NVZ divider */}
        <div className="pointer-events-none absolute inset-x-0 top-1/2 h-px -translate-y-1/2 bg-[var(--line)]" />

        {/* Minute tick lines — behind segments */}
        {duration > 0 && (() => {
          const ticks: number[] = [];
          for (let t = 60; t < duration; t += 60) ticks.push(t);
          return ticks.map((t) => (
            <div
              key={t}
              aria-hidden
              className="pointer-events-none absolute top-0 h-full w-px bg-[var(--line)]"
              style={{ left: `${(100 * t) / duration}%` }}
            />
          ));
        })()}

        {rallies.map((r, i) => {
          const left = (100 * r.start) / duration;
          const width = (100 * (r.end - r.start)) / duration;
          const widthPct = duration > 0 ? (100 * (r.end - r.start)) / duration : 0;
          const dur = r.end - r.start;
          const fullLabel = `R${i + 1} ${fmtTime(dur)}`;
          const shortLabel = `R${i + 1}`;
          const labelText = widthPct > 9 ? fullLabel : widthPct > 3.5 ? shortLabel : null;
          const tooltipText = `Rally ${i + 1} · ${fmtTime(r.start)}–${fmtTime(r.end)} · ${Math.round(dur)}s`;
          return (
            <div
              key={i}
              title={tooltipText}
              className={`segment-animate absolute top-0 h-full cursor-grab active:cursor-grabbing ${
                r.included
                  ? "bg-[var(--accent)]"
                  : "bg-[var(--muted)]/30"
              }`}
              style={{ left: `${left}%`, width: `${width}%`, minWidth: "6px" }}
              onPointerDown={(e) => onPointerDown(e, i, "body")}
              onClick={() => onPreview(r.start)}
            >
              {/* Start handle */}
              <div
                onPointerDown={(e) => onPointerDown(e, i, "start")}
                onPointerUp={endDrag}
                onPointerCancel={endDrag}
                onLostPointerCapture={endDrag}
                className="absolute left-0 top-0 h-full w-2 cursor-ew-resize bg-[var(--accent-ink)]/20 hover:bg-[var(--accent-ink)]/40 transition-colors"
              />
              {/* Rally number + duration label on wider segments */}
              {labelText && (
                <span className={`pointer-events-none absolute inset-0 flex items-center justify-center font-mono text-[10px] font-bold select-none ${
                  r.included ? "text-[var(--accent-ink)]" : "text-[var(--ink)]"
                }`}>
                  {labelText}
                </span>
              )}
              {/* End handle */}
              <div
                onPointerDown={(e) => onPointerDown(e, i, "end")}
                onPointerUp={endDrag}
                onPointerCancel={endDrag}
                onLostPointerCapture={endDrag}
                className="absolute right-0 top-0 h-full w-2 cursor-ew-resize bg-[var(--accent-ink)]/20 hover:bg-[var(--accent-ink)]/40 transition-colors"
              />
            </div>
          );
        })}
      </div>
      {/* Axis labels: 0:00, minute ticks, total */}
      {duration > 0 && (() => {
        const ticks: number[] = [];
        for (let t = 60; t < duration; t += 60) ticks.push(t);
        return (
          <div className="relative h-4 w-full font-mono text-[10px] text-[var(--muted)] px-0.5">
            <span className="absolute left-0">{fmtTime(0)}</span>
            {ticks.map((t) => (
              <span
                key={t}
                className="absolute"
                style={{ left: `${(100 * t) / duration}%`, transform: "translateX(-50%)" }}
              >
                {fmtTime(t)}
              </span>
            ))}
            <span className="absolute right-0">{fmtTime(duration)}</span>
          </div>
        );
      })()}
    </div>
  );
}
