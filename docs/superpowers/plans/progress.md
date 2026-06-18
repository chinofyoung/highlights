# Progress Ledger — Pickleball Highlights

Plan: docs/superpowers/plans/2026-06-17-pickleball-highlights.md
Mode: subagent-driven (no git in this repo; checkpoints = `pytest -v` green)

- Task 1: complete (3 passed; review clean). Minors for final triage: `@app.on_event("startup")` deprecated (migrate to lifespan when Task 7 edits main.py); unused `import numpy` in conftest (used by later tasks).
- Task 2: complete (11 passed; review clean). Minors for final triage: `smooth` uses np.convolve mode="same" → zero-pad suppresses signal in first/last ~window/2 frames (latent missed-detection at video edges); a few segment edge cases untested (end-clamp, unpadded-confidence).
- Task 3: complete (13 passed; review clean). No blocking findings.
- Task 4: complete (14 passed; review clean). No blocking findings.
- Task 5: complete (17 passed; review clean). No blocking findings.
- Task 6: complete (20 passed; review clean). Minors for final triage: concat list-file not cleaned up if ffmpeg fails (use try/finally); single-quote in a clip path would break concat list parsing (escape). Both low-risk, plan-faithful.
- Task 7: complete (22 passed + 1 fix test; review clean after fix). Important finding FIXED: `_params` now filters unknown keys (was TypeError→500). Minors for final triage: rejected-upload file left on disk; in-memory registry unbounded; `on_event` deprecation.
- Task 8: complete (assets serve 200, API not shadowed, 23 tests green; node --check clean). Important finding FIXED: upload now checks resp.ok; slider/export wrapped in try/catch. Minors for final triage: empty-export shows "null" string in result box (cosmetic). NOTE: full real-video click-through still pending USER manual verification (no sample match video).
- Task 9: complete (README created; Python floor corrected to 3.10+; paths/commands verified). Review folded into final whole-branch review.

FINAL whole-branch review: done (opus). No Critical. 2 Important FIXED: (1) empty-signal crash → graceful no-rallies (guard in normalize + smooth); (2) inverted "Sensitivity" slider → now higher = more rallies. All other Minors triaged as DEFER (acceptable for local single-user v1). Full suite: 24 passed, 0 skipped (ffmpeg present).
STILL PENDING: user manual click-through with a real fixed-camera pickleball video (no sample match clip bundled).
