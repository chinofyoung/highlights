# Task 5 Report: Frontend Scaffold (Vite + React + TS + Tailwind)

## Status: COMPLETE

---

## Files Created

| File | Notes |
|------|-------|
| `frontend/package.json` | Exact content from brief (with one version deviation — see below) |
| `frontend/vite.config.ts` | Added `/// <reference types="vitest/config" />` triple-slash directive |
| `frontend/tsconfig.json` | Exact content from brief |
| `frontend/tsconfig.node.json` | Removed `"noEmit": true` (incompatible with `"composite": true`) |
| `frontend/index.html` | Exact content from brief |
| `frontend/src/main.tsx` | Exact content from brief |
| `frontend/src/index.css` | Exact content from brief (Tailwind 4 `@import` + `@custom-variant dark`) |
| `frontend/src/App.tsx` | Exact content from brief |
| `frontend/src/test/setup.ts` | Exact content from brief |

---

## Version Deviations

### 1. `vitest`: `^2.1.0` → `^3.0.0` (installed: 3.2.6)

**Reason:** Vitest 2.x bundles its own copy of Vite 5 as a subdependency. Since we use Vite 6 (installed: 6.4.3), TypeScript's `tsc -b` step failed with type incompatibility errors — the two Vite instances had conflicting `Plugin<any>` types. Using `vitest/config`'s `defineConfig` also failed for the same reason (Vite version mismatch between the two `vite` packages).

Vitest 3.x dropped the bundled Vite copy and now lists Vite 6 as a peer dependency, resolving all conflicts.

---

## Configuration Deviations from Brief

### 1. `vite.config.ts`: Added `/// <reference types="vitest/config" />`

The brief's config uses `defineConfig` from `vite` but includes a `test:` key (which is a Vitest extension). Without the triple-slash directive, TypeScript reports `'test' does not exist in type 'UserConfigExport'`. The directive augments the Vite types with Vitest's `test` field. This is the standard/recommended pattern in Vitest docs.

### 2. `tsconfig.node.json`: Removed `"noEmit": true`

TypeScript forbids combining `"composite": true` with `"noEmit": true` in a project reference — it emits error TS6310: "Referenced project may not disable emit." Removed `noEmit` from tsconfig.node.json while keeping it in tsconfig.json (the main config). This matches standard Vite project scaffolding patterns (e.g., `npm create vite`).

---

## Build Result

```
vite v6.4.3 building for production...
transforming...
✓ 27 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.41 kB │ gzip:  0.27 kB
dist/assets/index-gta8DHat.css    4.68 kB │ gzip:  1.61 kB
dist/assets/index-CDJrTaLA.js   143.84 kB │ gzip: 46.21 kB
✓ built in 370ms
```

`frontend/dist/index.html` confirmed present. No TypeScript errors.

---

## Test Result

```
vitest run

 RUN  v3.2.6 /Users/chinoyoung/Code/highlights/frontend

No test files found, exiting with code 1
```

Exit code 1 with "No test files found" — expected per brief ("0 tests so far is fine; if Vitest errors on no tests, that's acceptable until Task 6 adds tests").

---

## Dev Serving + Proxy Verification

- Backend: `uvicorn app.main:app` started on port 8000.
- Dev server: `npm run dev` started on port 5173.
- `curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/` → **200** ✓
- Proxy verification: `curl -X OPTIONS http://localhost:5173/api/detect` → **204** (OPTIONS handled by backend, forwarded through proxy) ✓
- Both servers stopped after verification.

---

## Concerns / Notes

- npm audit reports 4 high-severity vulnerabilities in dev dependencies (jsdom/whatwg-encoding chain). These are dev-only and do not affect the production build. No `--force` fix applied to avoid breaking changes.
- The backend currently serves a legacy `index.html` at `/` from Starlette's `StaticFiles` mount. This does not conflict with the Vite frontend dev server (separate ports). In production (future task), the FastAPI app will likely need to serve `frontend/dist/` instead.
