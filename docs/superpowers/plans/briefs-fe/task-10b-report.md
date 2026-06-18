# Task 10b — Visual Polish Pass Report

Pickleball highlight-extraction frontend (React + TypeScript + Tailwind 4). Visual-only
polish: no behavior, prop contract, App flow, api client, or `timeline-math` changes.

## Final token system (`frontend/src/index.css`)

Kept `@import "tailwindcss";` and `@custom-variant dark (...)`. Added:

```css
@theme {
  --font-display: "Archivo", system-ui, sans-serif;
  --font-body: "Hanken Grotesk", system-ui, sans-serif;
  --font-mono: "Space Mono", ui-monospace, monospace;
}
:root {
  color-scheme: light dark;
  --bg:#F2F5F4; --surface:#FFFFFF; --ink:#0C1A1B; --muted:#5B6B6B; --line:#D7E0DE;
  --accent:#BEF130; --accent-ink:#14210A; --teal:#0E8C8B; --danger:#E4572E;
}
.dark {
  --bg:#0C1517; --surface:#121E20; --ink:#E7EEEC; --muted:#8AA0A0; --line:#20302F;
  --accent:#C7F23A; --teal:#2DD4BF;
}
body { margin:0; background:var(--bg); color:var(--ink); font-family:var(--font-body); }
```

Plus a `segment-in` keyframe (`.segment-animate` fade/scaleX on the timeline blocks) and a
`@media (prefers-reduced-motion: reduce)` block that disables the keyframe and clamps all
transition/animation durations. Components reference tokens via Tailwind arbitrary values
(`bg-[var(--surface)]`, `text-[var(--muted)]`, `border-[var(--line)]`, `text-[var(--danger)]`,
`font-display`, `font-mono`).

Palette discipline: optic-lime `--accent` is used only on the primary CTA, the export icon,
and included rally blocks; `--teal` carries the wordmark dot, links/hovers, and focus rings;
dark mode is teal-tinted charcoal, never pure black.

## Fonts added (`frontend/index.html`)

Google Fonts via `<link>` (with `preconnect`):
- **Archivo** 600/700/800 — wordmark + headings (font-display, tight tracking)
- **Hanken Grotesk** 400/500/600 — body/UI (font-body, default)
- **Space Mono** 400/700 — all timecodes, %, durations, confidence, clip counts/paths (font-mono)

`<title>` → "Pickleball Highlights — find the rallies".

## Timeline signature treatment (`frontend/src/components/Timeline.tsx`)

The track is a `h-14` court strip: `bg-[var(--surface)]` with a `border-[var(--line)]` frame
and a thin `h-px` horizontal **center line** at 50% (pointer-events-none) evoking the court
NVZ divider. Included rallies are bright optic-lime `bg-[var(--accent)]` "volleys"; excluded
rallies go quiet at `bg-[var(--muted)]/30`. Drag handles are flush `w-2` strips
(`bg-[var(--accent-ink)]/20`, hover `/40`). Segments wider than 6% of the timeline show a
Space Mono start timecode centered on the block. Below the strip, `0:00` and total duration
sit in `font-mono text-[10px] text-[var(--muted)]`. Blocks fade/scale in on mount via
`.segment-animate` (gated behind prefers-reduced-motion) for a tasteful detection-complete reveal.

## Pointer-handler bug fix (`Timeline.tsx`)

Original risk: `setPointerCapture` was called on child handle/block elements while only the
track div handled `onPointerUp`, so releasing outside the track could leave `drag.current`
set (ghost drag).

Fix: a single `const endDrag = () => { drag.current = null; };` is now wired to
`onPointerUp`, `onPointerCancel`, **and** `onLostPointerCapture` on both the track div and on
each start/end handle. `onLostPointerCapture` fires on the capturing element whenever capture
ends for any reason (release anywhere on the page, blur, cancel), so drag state is always
cleared. `onPointerMove` still fires during capture. The clamp/move math
(`clampStart`/`clampEnd`/`moveBody`/`pxToTime`/`MIN_GAP`) and the `onChange`/`onPreview`
contract are byte-for-byte unchanged.

## Copy changes

| Location | Before | After |
|---|---|---|
| `<title>` | Pickleball Highlights | Pickleball Highlights — find the rallies |
| Header wordmark | 🎾 Pickleball Highlights | Pickleball.highlights (teal dot, Archivo) |
| Detect progress | Detecting rallies… | Finding rallies… |
| Export progress | Exporting… | Exporting highlights… |
| Export button | Export | Export highlights |
| RallyList empty | No rallies — try raising sensitivity. | No rallies found — nudge sensitivity up. |
| ResultPanel header | Export complete | Highlights ready |
| Errors | text-red-500 | text-[var(--danger)] |
| Upload headline | (none) | Find the rallies. Skip the standing around. |
| Upload subhead | Fixed-camera footage works best | Drop in a match recorded from one fixed angle. We'll spot every rally so you can cut a highlight reel in minutes. |

## Quality floor

Responsive (header/main/controls wrap, full-width timeline, mobile paddings); visible
`focus-visible` rings in `--teal` on interactive elements; `prefers-reduced-motion` honored;
motion kept subtle (segment reveal + hover color shifts only).

## Build + test results

```
npm run build → tsc -b && vite build → ✓ built in ~0.8s, 0 TypeScript errors
                dist/index.html, dist/assets/*.css, dist/assets/*.js emitted
npm run test  → Test Files 3 passed (3) | Tests 13 passed (13)
```

## Deviations

None substantive. New rally handles are flush strips (no rounded-l/r) rather than the
original rounded handles — the parent lime block carries the visual weight; drag logic and
`setPointerCapture` targets are unchanged.

## Files changed (absolute paths)

- /Users/chinoyoung/Code/highlights/frontend/index.html
- /Users/chinoyoung/Code/highlights/frontend/src/index.css
- /Users/chinoyoung/Code/highlights/frontend/src/App.tsx
- /Users/chinoyoung/Code/highlights/frontend/src/components/Timeline.tsx
- /Users/chinoyoung/Code/highlights/frontend/src/components/UploadView.tsx
- /Users/chinoyoung/Code/highlights/frontend/src/components/Controls.tsx
- /Users/chinoyoung/Code/highlights/frontend/src/components/RallyList.tsx
- /Users/chinoyoung/Code/highlights/frontend/src/components/ResultPanel.tsx
- /Users/chinoyoung/Code/highlights/frontend/src/components/ProgressBar.tsx
- /Users/chinoyoung/Code/highlights/frontend/src/components/ThemeToggle.tsx
