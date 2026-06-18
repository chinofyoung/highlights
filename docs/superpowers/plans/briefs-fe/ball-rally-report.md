# Ball Rally Animation — Implementation Report

## New Keyframes

### `ball-rally`
Moves the ball across a 224px track in a gentle arc, bouncing back to the start:

| Keyframe | translateX | translateY |
|----------|-----------|-----------|
| 0%       | 0px       | 0px       |
| 25%      | 92px      | -16px     |
| 50%      | 184px     | 0px       |
| 75%      | 92px      | -16px     |
| 100%     | 0px       | 0px       |

Timing: `1.6s ease-in-out infinite`

### `ball-rally-shadow`
Tracks the ball's X position and shrinks/fades at peak arc to simulate depth:

| Keyframe   | translateX | scaleX | opacity |
|------------|-----------|--------|---------|
| 0%, 100%   | 0px       | 1      | 0.18    |
| 25%        | 92px      | 0.65   | 0.08    |
| 50%        | 184px     | 1      | 0.18    |
| 75%        | 92px      | 0.65   | 0.08    |

Timing: `1.6s ease-in-out infinite`. Uses `transform-origin: center center` so `scaleX` collapses symmetrically.

## BallLoader Markup

```
<div>                          flex justify-center py-2 overflow-x-hidden
  <div>                        relative w-56 h-10  (224×40px track)
    <div ball-rally-shadow />  absolute bottom-0 left-0 w-10 h-10
                               rendered as 6px-tall blurred ellipse via CSS
    <div ball-rally />         absolute bottom-0 left-0 h-10 w-10 rounded-full
                               filled with var(--accent)
  </div>
</div>
```

Both the ball and shadow start at bottom-left of the track (`absolute bottom-0 left-0`). The shadow's visual dimensions (6px height, 40px width, `blur(3px)`) are defined entirely in CSS — the div itself is w-10 h-10 for positioning purposes only.

## Reduced-Motion Handling

When `prefers-reduced-motion: reduce` is active:
- `.ball-rally` falls back to `ball-pulse` (1.2s opacity fade, already defined)
- `.ball-rally-shadow` gets `animation: none; opacity: 0` — completely hidden since the pulsing ball alone communicates the loading state

The `ball-pulse` keyframe is declared inside `@media (prefers-reduced-motion: reduce)` so it only exists when needed.

## Build Result

**Exit code: 0** — no TypeScript errors, no warnings.

Output: `dist/assets/index-tKebf0Zn.css` (20.47 kB gzip: 4.80 kB), `dist/assets/index-BvS4K1vU.js` (163.16 kB gzip: 52.00 kB)

## Test Result

**21/21 tests passed** across 5 test files:
- `timeline-math.test.ts` — 7 tests
- `api.test.ts` — 4 tests
- `useJob.test.ts` — 2 tests
- `SelectedVideo.test.tsx` — 4 tests
- `App.test.tsx` — 4 tests
