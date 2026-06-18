# UI Fix Report — 2026-06-18

## Files Changed

- `src/components/BallLoader.tsx`
- `src/index.css`
- `src/App.tsx`

---

## Change 1: Ball Loader Fix

### BallLoader.tsx
- Inner container: `h-10` → `h-12` (40px → 48px) to give the 18px arc vertical room
- Ball: `h-10 w-10` → `h-6 w-6` (40px → 24px)
- Shadow: `w-10 h-10` → `w-6 h-6` (Tailwind sizing classes on the shadow div; actual rendered shadow dimensions are controlled in CSS)

### index.css
- Replaced `@keyframes ball-rally` with 9-stop version doing 2 bounces right then 2 bounces back (0 → 50px → 100px → 150px → 200px → 150px → 100px → 50px → 0), each apex at `translateY(-18px)`, each ground touch at `translateY(0px)`.
- Horizontal range is 0–200px (container 224px − ball 24px = 200px max), so the ball never clips horizontally.
- Replaced `@keyframes ball-rally-shadow` with matching 9-stop version (translateX mirrors the ball; scaleX alternates 1.0 at ground / 0.6 at apex; opacity 0.18 at ground / 0.08 at apex).
- `.ball-rally-shadow` rule: `width: 40px` → `width: 24px` to match smaller ball.
- `@media (prefers-reduced-motion: reduce)` blocks left exactly as-is.

---

## Change 2: Full-Width Container

`<main>` class changed from:
```
mx-auto flex max-w-3xl flex-col gap-6 px-4 pb-16 pt-8 sm:px-8
```
to:
```
mx-auto w-full max-w-[1600px] px-4 pb-16 pt-8 sm:px-8
```
`flex flex-col gap-6` removed from `<main>`; each view manages its own wrapper.

---

## Change 3: Narrow Wrappers for Simple Views

Each simple view block now wrapped in `<div className="mx-auto flex w-full max-w-3xl flex-col gap-6">`:
- View 1 (no file / no video): UploadView + DraftsSection + LibrarySection
- View 2 (file selected, not uploading): SelectedVideo
- View 3 (analyzing / detectJob): BallLoader + ProgressBar + Cancel button
- detect error block: error paragraph

View 4a (libraryView) also wrapped identically: Back/Re-edit row + HighlightsView.

---

## Change 4: Two-Column Review View (View 4)

View 4 (`videoId && !libraryView && !detectJob && !analyzing`) restructured to:

```
<>
  <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
    <div className="flex min-w-0 flex-col gap-6">
      Player / Timeline / Controls
    </div>
    <div className="lg:sticky lg:top-6 lg:max-h-[calc(100vh-7rem)] lg:overflow-y-auto self-start">
      RallyList
    </div>
  </div>
  ProgressBar (exportJob running)
  export error paragraph
  HighlightsView (export done)
</>
```

- On < lg viewports: single column, stacked as before.
- On lg+: Player/Timeline/Controls on left, RallyList in a sticky scrollable right column (380px fixed).
- Export progress, export error, and HighlightsView remain full-width below the grid.
- All component props preserved exactly: `onChange`, `onPreview`, `sensitivity`, `onSensitivity`, `onExport`, `exportDisabled`, `view`, `onViewChange`, `onToggle`, `onJump`, `onPlay`.

---

## Build Result

```
> tsc -b && vite build

vite v6.4.3 building for production...
✓ 1587 modules transformed.
dist/index.html                   0.75 kB │ gzip:  0.43 kB
dist/assets/index-C1_pJRRf.css   24.27 kB │ gzip:  5.46 kB
dist/assets/index-BG9YAcnv.js   179.04 kB │ gzip: 54.98 kB
✓ built in 1.19s
```

Zero TypeScript errors. Zero warnings.

---

## Self-Review

**Props preserved?** Yes — every prop on Player, Timeline, Controls, and RallyList is identical to the original. No logic, state, or component files were modified.

**Views that might look wrong?**
- The detect-error block is now wrapped in its own `max-w-3xl` div, giving it a narrow column. If the error appears simultaneously with View 3 content, both will be in separate narrow divs rather than a single flow — but these conditions were already treated as sibling blocks in the original, so no regression.
- View 3 gap-6 wrapper means BallLoader, ProgressBar, and Cancel button now have consistent spacing. Previously they had `mt-2` on the Cancel button; that inline margin is preserved and will add to the gap.

**Concerns:**
- `lg:sticky lg:top-6` on the RallyList column assumes the scroll container is the viewport (not a parent with `overflow: hidden`). The `<main>` has no overflow constraint, so this should work correctly.
- The `lg:max-h-[calc(100vh-7rem)]` accounts for ~112px of chrome (header ~72px + top-6 offset ~24px + buffer). If the header height changes this may need adjustment.
- No backend changes were made or needed.
