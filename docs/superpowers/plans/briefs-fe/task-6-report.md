# Task 6 Report: API Client + Shared Types

## Files Created

- `frontend/src/types.ts` — `Rally`, `JobRecord`, `DetectParams` interfaces (verbatim from brief)
- `frontend/src/api.ts` — all six exported functions (verbatim from brief)
- `frontend/src/test/api.test.ts` — four unit tests (verbatim from brief)

## Files Modified

- `frontend/tsconfig.json` — added `"exclude": ["src/test"]` (deviation; see below)

## TDD Process

**Step 1–2 (fail):** Test file written first. Running `npx vitest run src/test/api.test.ts` produced:
```
FAIL  src/test/api.test.ts
Error: Failed to resolve import "../api" from "src/test/api.test.ts". Does the file exist?
```

**Step 3–5 (pass):** After creating `types.ts` and `api.ts`, all 4 tests passed:
```
✓ src/test/api.test.ts (4 tests) 4ms
Test Files  1 passed (1)
Tests  4 passed (4)
```

## Checkpoint: `npm run build && npm run test`

**Build:**
```
✓ built in 361ms
dist/assets/index-TzSQA4c3.js   143.84 kB │ gzip: 46.21 kB
```

**Tests:**
```
Test Files  1 passed (1)
Tests  4 passed (4)
```

Both green.

## Deviations

**`tsconfig.json` — added `"exclude": ["src/test"]`**

The brief did not mention this change, but it was required. The main `tsconfig.json` has `"include": ["src"]` which causes `tsc -b` (run during `npm run build`) to type-check test files under the DOM lib. The test file uses `global.fetch = ...` — `global` is a Node.js runtime variable, not present in the DOM lib types, and `@types/node` is not installed. Without the exclusion, build failed with:

```
src/test/api.test.ts(16,5): error TS2304: Cannot find name 'global'.
```

Excluding `src/test` from the main tsconfig is the standard Vite + Vitest pattern: vitest uses its own transform pipeline with appropriate environment globals; `tsc -b` is for app code only. This does not affect test execution or type safety of the tested modules.

## Concerns

None. The deviation is minimal, correct, and standard practice. No pinned npm versions were needed.

---

## Fix Report: globalThis.fetch + Remove exclude

**Problem:** The `"exclude": ["src/test"]` in `tsconfig.json` silently removes all test files from type-checking, preventing future test growth from being checked.

**Solution:** Replace `global.fetch` with `globalThis.fetch` (DOM-typed, no @types/node needed) and remove the exclude entry.

### Exact Changes

#### 1. `frontend/src/test/api.test.ts` — Replace global.fetch with globalThis.fetch (3 occurrences)

**Line 16 (before):**
```typescript
global.fetch = mockFetch(200, { job_id: "abc" }) as any;
```

**Line 16 (after):**
```typescript
globalThis.fetch = mockFetch(200, { job_id: "abc" }) as any;
```

**Line 19 (before):**
```typescript
expect(global.fetch).toHaveBeenCalledWith(
```

**Line 19 (after):**
```typescript
expect(globalThis.fetch).toHaveBeenCalledWith(
```

**Line 26 (before):**
```typescript
global.fetch = mockFetch(400, { detail: "bad video" }) as any;
```

**Line 26 (after):**
```typescript
globalThis.fetch = mockFetch(400, { detail: "bad video" }) as any;
```

**Line 31 (before):**
```typescript
global.fetch = mockFetch(200, { status: "done", progress: 1, result: { rallies: [] }, error: null }) as any;
```

**Line 31 (after):**
```typescript
globalThis.fetch = mockFetch(200, { status: "done", progress: 1, result: { rallies: [] }, error: null }) as any;
```

#### 2. `frontend/tsconfig.json` — Remove exclude entry

**Before:**
```json
  "include": ["src"],
  "exclude": ["src/test"],
  "references": [{ "path": "./tsconfig.node.json" }]
```

**After:**
```json
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
```

### Verification Results

**Build (npm run build):** ✓ 0 TypeScript errors
```
vite v6.4.3 building for production...
✓ 27 modules transformed.
✓ built in 357ms
dist/index.html                   0.41 kB │ gzip:  0.27 kB
dist/assets/index-BeO9odfP.css    7.06 kB │ gzip:  2.07 kB
dist/assets/index-TzSQA4c3.js   143.84 kB │ gzip: 46.21 kB
```

**Tests (npm run test):** ✓ 4/4 passed
```
✓ src/test/api.test.ts (4 tests) 4ms
Test Files  1 passed (1)
Tests  4 passed (4)
```

All tests now type-checked by tsc -b, no test failures.
