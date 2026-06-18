# Progress Ledger — Modern Frontend (Vite+React)

Plan: docs/superpowers/plans/2026-06-17-modern-frontend.md
Mode: subagent-driven (no git; checkpoints = pytest/npm test + build green)

- Task 1: complete (29 passed; review clean). No blocking findings.
- Task 2: complete (32 passed; review clean). Minor: motion's own final==1.0 not directly asserted (covered via analyze test) — plan-mandated test code.
- Task 3: complete (34 passed; review clean). No blocking findings.
- Task 4: complete (35 passed; review clean). Minor for final triage: unused `BackgroundTasks` import in routes.py (plan-mandated optional import) — remove in final cleanup.
- Task 5: complete (clean build, dev proxy verified; review clean). Deviations: vitest ^3 (Vite 6 peer-compat), tsconfig.node noEmit removed + vitest/config ref. Notes: strict noUnusedLocals is intentional (every unused prop = build error in later tasks); lucide pinned 0.460.0 (icons used are stable).
- Task 6: complete (4 pass, build clean; review clean after fix). Important FIXED: replaced global.fetch→globalThis.fetch and removed tsconfig exclude(src/test) so tests stay type-checked. Minor for final triage: getJob throws static string instead of server detail (consistency).
- Task 7: complete (6 pass, build clean; review clean after fix). Important FIXED: restored immediate-on-mount poll (was 500ms dead zone), test corrected. Legit deviations kept: globalThis.jest=vi shim + @testing-library/dom dep (standard for vitest fake timers + RTL v16). Minor: IDLE const naming.
- Task 8: complete (13 pass, build clean; review clean). Minor for final triage: pxToTime zero-guard untested; inverted clamp-range behavior implicit (fine for realistic UI inputs).
- Task 9: complete (build clean, 13 pass; review clean). Minors for final triage: UploadView hint text lacks dark: variant; Player missing displayName; Controls slider shows no numeric value. (Most to be addressed by Task 10 design polish.)
- Task 10a: complete (Timeline+App integration; build clean, 13 pass; review clean — spec ✅, setState-in-render converges). Pointer-capture edge cases (E,F: ghost-drag if released outside track) + design polish to be applied in 10b.
- Task 10b: complete (design polish; build clean, 13 pass). Court+optic-ball palette via CSS vars (light/dark swap), Archivo/Hanken/Space Mono fonts, timeline=court-strip signature, copy improved. Pointer ghost-drag FIXED (onLostPointerCapture/onPointerCancel). Verified by direct screenshot inspection (light+dark landing both good). Minor for final triage: favicon 404 (no favicon shipped).
- Task 11: complete (SPA serves at / with id=root, /api/jobs/nope→404, old app/web deleted, 35 backend tests green; verified by curl + pytest). on_event deprecation still present (final-triage minor).
- Task 12: complete (README frontend section + run-note added; verified). Folded into final review.

FINAL whole-branch review: done (opus). No Critical. 2 Important FIXED (one-liners): useJob now resets to IDLE when jobId clears (was stale terminal state); getJob now surfaces server detail. Also removed unused BackgroundTasks import. All other ledger minors triaged DEFER (acceptable for local single-user v1): on_event deprecation, setState-in-render (converges), pxToTime zero-guard untested, favicon 404, Player displayName. Suites: backend 35 passed, frontend 13 passed; build clean. Landing verified by screenshot (light+dark). STILL PENDING: user manual click-through with a real video to exercise the review/timeline/export flow + see the progress bar live.

---

# Cancel + Play Features (2026-06-17)

- CP Task 1 (backend cancel): complete — jobs.py cancel(), routes.py _Cancelled + /cancel endpoint, motion.py finally, 5 new tests. Backend 40 passed.
- CP Task 2 (frontend): complete — cancelJob in api.ts, Cancel button + flash fix in App.tsx, playSegment in Player.tsx, per-rally Play button in RallyList.tsx. Build clean (0 TS errors), frontend 21 passed.
