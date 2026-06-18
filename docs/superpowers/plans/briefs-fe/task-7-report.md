# Task 7 Report: useJob polling hook

## Files Created

- `frontend/src/useJob.ts` — the polling hook
- `frontend/src/test/useJob.test.ts` — Vitest tests (verbatim from brief)

## Files Modified

- `frontend/src/test/setup.ts` — added `globalThis.jest = globalThis.vi` alias
- `frontend/package.json` — added `@testing-library/dom@^10.4.1` dev dependency (missing peer dep)

## Final Test Output

```
 RUN  v3.2.6 /Users/chinoyoung/Code/highlights/frontend

 ✓ src/test/api.test.ts (4 tests) 6ms
 ✓ src/test/useJob.test.ts (2 tests) 21ms

 Test Files  2 passed (2)
      Tests  6 passed (6)
   Duration  787ms
```

## Build Result

`npm run build && npm run test` — both green.

```
vite v6.4.3 building for production...
✓ 27 modules transformed.
dist/assets/index-TzSQA4c3.js   143.84 kB │ gzip: 46.21 kB
✓ built in 396ms
```

## Deviations from Brief

### 1. Removed immediate `tick()` call from `useJob.ts`

**Brief's exact implementation:**
```ts
const id = setInterval(tick, 500);
tick();
return () => { active = false; clearInterval(id); };
```

**Actual implementation:**
```ts
const id = setInterval(tick, 500);
return () => { active = false; clearInterval(id); };
```

**Reason:** The brief's test and implementation are mutually inconsistent when run under
`vi.advanceTimersByTimeAsync`. The test expects status to be `"running"` after the first
600ms advance, then `"done"` after the second. With an immediate `tick()`, the async mock
promise resolves in the microtask queue before `tickAsync(600)` even starts (because
`tickAsync` wraps itself in `originalSetTimeout`, a macro-task). By the time the test
resumes after `await vi.advanceTimersByTimeAsync(600)`, BOTH seq[0] (running) and seq[1]
(done) have been consumed — status is `"done"` not `"running"`, causing the first waitFor
to fail immediately. Removing the immediate call makes each advance fire exactly one
interval tick as the test expects.

### 2. Added `globalThis.jest = globalThis.vi` in `setup.ts`

**Reason:** `@testing-library/dom`'s `waitFor` checks `typeof jest !== 'undefined'` to
decide whether to use its fake-timer code path (loop calling `jest.advanceTimersByTime`)
or its real-timer code path (setInterval). Vitest does not expose `jest` as a global, so
`waitFor` used real setInterval — which fake timers intercept, causing `waitFor` to hang
indefinitely (5s timeout). Setting `jest = vi` enables the fake-timer path. This alias
must be set at module load time in setup.ts so it is available for all tests.

### 3. Installed `@testing-library/dom@^10.4.1`

**Reason:** `@testing-library/react` v16 requires `@testing-library/dom` as a peer
dependency but it was not installed. Added as a devDependency.

## Concerns

1. **act() warnings** — Two React `act()` warnings appear in test output during the
   polling test. These are cosmetic (tests pass), caused by `setRec(...)` calls happening
   outside React's `act()` wrapper. Since the test uses `vi.advanceTimersByTimeAsync` (not
   wrapped in `act()`), React cannot batch-wrap the state updates. This is a known
   limitation of testing async state updates with fake timers + `renderHook`. The warnings
   do not affect correctness.

2. **Initial poll latency** — By removing the immediate `tick()`, the first status poll
   now happens at 500ms after mount (not immediately). In production use, this means the
   UI won't reflect job status until 500ms after the job starts. If zero-latency first-poll
   is desired in production, the implementation should be revisited (while adjusting the
   test accordingly).

3. **Brief inconsistency** — The brief specified both the test AND the implementation as
   verbatim, but they are mutually incompatible under vitest's `advanceTimersByTimeAsync`
   semantics. The deviation above is the minimum change required to reconcile them.

---

## Task 7 Fix (2026-06-17)

### What Changed

**`frontend/src/useJob.ts`:** Restored the immediate `tick()` call after `setInterval`.
```ts
const id = setInterval(tick, 500);
tick();  // ← restored: first poll fires immediately on mount
return () => { active = false; clearInterval(id); };
```

**`frontend/src/test/useJob.test.ts`:** Rewrote "polls until done" test to work with the immediate tick:
- Mock uses a call counter (not `Array.shift`) so it never goes empty: call 1 → `running`, call 2+ → `done`.
- Added `act` import from `@testing-library/react`.
- After `renderHook`, flushes the immediate tick with `act(async () => { await vi.advanceTimersByTimeAsync(0); })` then asserts `status === "running"`.
- Then `act(async () => { await vi.advanceTimersByTimeAsync(500); })` fires the interval tick and asserts `status === "done"` with `result: { rallies: [] }`.
- Timer-advancing calls wrapped in `act()` to silence React act() warnings.

### Build + Test Output

```
npm run build → ✓ built in 420ms (0 TS errors)
npm run test  → 2 test files, 6 tests, all passed
```
