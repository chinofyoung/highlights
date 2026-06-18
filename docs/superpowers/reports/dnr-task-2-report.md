# Task 2 Report: Frontend — rename adopts the new video_id

## Files Changed

- `frontend/src/components/DraftsSection.tsx`
- `frontend/src/components/LibrarySection.tsx`

## Exact Mapper Changes

### DraftsSection.tsx (line 44)

Before:
```tsx
d.video_id === videoId ? { ...d, original_filename: r.original_filename } : d,
```

After:
```tsx
d.video_id === videoId ? { ...d, video_id: r.video_id, original_filename: r.original_filename } : d,
```

### LibrarySection.tsx (line 61)

Before:
```tsx
p.video_id === videoId ? { ...p, original_filename: r.original_filename } : p,
```

After:
```tsx
p.video_id === videoId ? { ...p, video_id: r.video_id, original_filename: r.original_filename } : p,
```

## Build Result

```
> tsc -b && vite build
✓ 1587 modules transformed.
dist/index.html                   0.75 kB │ gzip:  0.43 kB
dist/assets/index-CgePgvYT.css   24.20 kB │ gzip:  5.45 kB
dist/assets/index-CnreO9ko.js   179.08 kB │ gzip: 54.99 kB
✓ built in 980ms
```

Zero TypeScript errors. Build succeeded.

## Concerns

None. `Draft.video_id` and `Project.video_id` are both `string` in `types.ts`, so adopting `r.video_id` type-checks cleanly. The row key (`key={draft.video_id}` / `key={p.video_id}`) will now reflect the new id after a rename, which is the intended re-keying behavior. No other logic was changed.
