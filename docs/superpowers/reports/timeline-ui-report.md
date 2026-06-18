# Timeline UI Improvements Report

## What Changed

### 1. Segment Labels (rally number + duration)
- Replaced the old start-time-only label (`fmtTime(r.start)`) with a rally-number + duration label.
- `dur = r.end - r.start` computed per segment.
- `widthPct = (100 * (r.end - r.start)) / duration` — percentage of timeline width the segment occupies.
- **Width thresholds:**
  - `widthPct > 9` → full label `R{n} M:SS` (e.g. "R3 0:07")
  - `widthPct > 3.5` → short label `R{n}` (e.g. "R3")
  - `widthPct <= 3.5` → no on-segment text (tooltip covers it)
- Color: `text-[var(--accent-ink)]` for included segments; `text-[var(--ink)]` for excluded segments (legible on muted background).

### 2. Tooltip
- Added native `title` attribute to each segment's outer div.
- Format: `Rally {n} · {start}–{end} · {dur}s` (e.g. "Rally 3 · 2:38–2:45 · 7s").
- Uses `fmtTime()` for start/end and `Math.round(dur)` for seconds. Works on any size segment including tiny slivers.

### 3. Minimum Width
- Added `minWidth: "6px"` to each segment's inline `style` object alongside the existing `left` and `width` percentage values.
- Very short rallies remain visible and clickable without distorting the proportional layout.

### 4. Minute Ticks + Axis Labels
- **Tick lines:** Computed inside an IIFE before `rallies.map()` so they render behind segments. For each `t = 60; t < duration; t += 60`, a 1px-wide full-height absolutely-positioned div is placed at `left: (100*t)/duration + "%"` with `bg-[var(--line)]`, `pointer-events-none`, and `aria-hidden`. Guarded by `duration > 0`.
- **Axis row:** Replaced the simple flex row with a `relative h-4 w-full` container. `0:00` is `absolute left-0`, the total is `absolute right-0`, and intermediate minute labels use `absolute` + `style={{ left: ..., transform: "translateX(-50%)" }}` so each is centered on its tick. Same `font-mono text-[10px] text-[var(--muted)]` styling as before.

## Build Result
`tsc -b && vite build` — zero TypeScript errors, built in 1.02s. Output: `dist/assets/index-BFpX0STd.js 180.77 kB (gzip: 55.36 kB)`.

## Self-Review: Drag Behavior Untouched?
Yes. The following were not modified:
- `pxToTime`, `clampStart`, `clampEnd`, `moveBody`, `MIN_GAP` imports
- `onPointerDown` handler and its logic
- `onPointerMove` handler and its delta/clamp math
- `endDrag` and its attachment points (`onPointerUp`, `onPointerCancel`, `onLostPointerCapture`) on both the track and each handle
- Start/end handle divs — their `onPointerDown` calls and class names are identical
- `onPreview(r.start)` on segment click
- Prop signatures (`rallies`, `duration`, `onChange`, `onPreview`)

## Concerns
- The IIFE pattern (`{duration > 0 && (() => { ... })()}`) for both tick rendering and the axis row is slightly unusual JSX; a helper function would be cleaner at the cost of one extra declaration outside JSX. Functionally equivalent.
- The `minWidth: "6px"` can cause segments to visually overlap their neighbors for very short rallies in a dense timeline — this is an inherent trade-off of enforcing a minimum size over a proportional layout. The overlap is purely visual; the drag math is unaffected.
- Intermediate axis labels can collide if the video is short (e.g., 70s would show a single "1:00" tick at ~86% which is fine, but a 125s video would show "1:00" and "2:00" close together near the right edge). No overflow clipping is applied; the labels are allowed to render naturally.
