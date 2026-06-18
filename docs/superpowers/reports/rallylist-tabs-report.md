# RallyList: Multi-Select Chips → Single-Select Segmented Control

## What Changed

**File:** `frontend/src/components/RallyList.tsx`

1. **Replaced `toggleChip` with `selectMode`** — the old function toggled membership in the `view` array (multi-select, kept ≥1 active). The new function always calls `onViewChange([mode])`, producing a single-element array.

2. **Replaced the chip filter row with a segmented control** — the `<div>` containing a "Show:" label and two bordered pill buttons was replaced with an `inline-flex` pill container (border + surface background, `p-0.5` inner padding) holding the same two buttons. The active tab gets `bg-[var(--teal)] text-white`; the inactive tab is transparent with muted text. Each button now carries `aria-pressed` for accessibility.

3. **`chips` array unchanged** — `[{label:"Rally",mode:"rally"},{label:"Serve",mode:"serve"}]` kept as-is.

## Single-Select Confirmation

Clicking either tab calls `selectMode(mode)` → `onViewChange([mode])`, which replaces the entire `view` array with a single-element array. It is structurally impossible for both tabs to be active simultaneously. Default ("Rally") is controlled by `App.tsx`'s initial state `["rally"]` — not touched.

The `clipLabel` ternary (`view.includes("serve") && view.includes("rally")`) will always evaluate to `false` under single-select, so it always renders `Rally N` — correct behavior, no modification needed.

## Build Result

```
✓ built in 931ms — 0 TypeScript errors
```

## Concerns

None. The prop contract (`view: ViewMode[]`, `onViewChange: (v: ViewMode[]) => void`) is unchanged, so any parent component passing or reading `view` requires no update. The always-single-element array is a valid subset of the existing type.
