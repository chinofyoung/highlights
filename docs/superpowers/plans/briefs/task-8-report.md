# Task 8 Report: Review UI (frontend)

## Files Created

| File | Path |
|------|------|
| `index.html` | `app/web/index.html` |
| `app.js` | `app/web/app.js` |
| `style.css` | `app/web/style.css` |

All three files were created verbatim from the brief — no modifications.

---

## HTTP Verification Results

Server started: `uvicorn app.main:app --port 8000` — clean startup, ffmpeg check passed.

| Check | Command | Expected | Actual |
|-------|---------|----------|--------|
| index.html serves | `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/` | 200 | **200** |
| HTML contains "Pickleball Highlights" | `curl -s http://localhost:8000/ | grep -c "Pickleball Highlights"` | >= 1 | **2** |
| app.js serves | `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/app.js` | 200 | **200** |
| style.css serves | `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/style.css` | 200 | **200** |
| /api routes not shadowed | `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/video/nonexistent` | 404 | **404** |

All 5 checks passed.

---

## pytest -v Summary

```
collected 23 items

tests/test_api.py::test_full_flow PASSED
tests/test_api.py::test_upload_rejects_non_video PASSED
tests/test_api.py::test_params_ignores_unknown_keys PASSED
tests/test_audio.py::test_extract_wav_creates_file PASSED
tests/test_audio.py::test_audio_energy_higher_during_sine PASSED
tests/test_deps.py::test_ffmpeg_available_returns_bool PASSED
tests/test_deps.py::test_probe_duration_reads_length PASSED
tests/test_deps.py::test_probe_duration_rejects_non_video PASSED
tests/test_exporter.py::test_cut_clip_has_expected_duration PASSED
tests/test_exporter.py::test_export_produces_clips_and_stitch PASSED
tests/test_exporter.py::test_export_empty_ranges PASSED
tests/test_motion.py::test_motion_energy_higher_during_movement PASSED
tests/test_pipeline.py::test_save_and_load_signals_roundtrip PASSED
tests/test_pipeline.py::test_analyze_detects_middle_rally PASSED
tests/test_pipeline.py::test_resegment_uses_cache PASSED
tests/test_segment.py::test_normalize_constant_is_zeros PASSED
tests/test_segment.py::test_normalize_scales_to_unit PASSED
tests/test_segment.py::test_combine_takes_max PASSED
tests/test_segment.py::test_segment_finds_single_active_span PASSED
tests/test_segment.py::test_segment_merges_short_gap PASSED
tests/test_segment.py::test_segment_drops_short_span PASSED
tests/test_segment.py::test_segment_applies_padding_and_clamps PASSED
tests/test_segment.py::test_segment_empty_when_all_quiet PASSED

23 passed, 3 warnings in 2.37s
```

Warnings are pre-existing deprecations (FastAPI `on_event`, httpx/starlette compatibility) — not introduced by this task.

---

---

## Robustness Fix (appended 2026-06-17)

### Changes made to `app/web/app.js`

Three minimal fixes, no restructuring:

1. **Upload response.ok check** — split the one-liner fetch/json chain into two steps; added `if (!resp.ok)` guard that extracts `.detail` from the JSON error body (or falls back to `statusText`) and writes it to `#status`, then returns early.

2. **Sensitivity slider try/catch** — wrapped the `postJSON("/api/resegment", …)` call and subsequent `render()` in `try { … } catch (e) { $("status").textContent = "Resegment failed: " + e.message; }`.

3. **Export button try/catch** — wrapped the `postJSON("/api/export", …)` call and result display in `try { … } catch (e) { $("result").textContent = "Export failed: " + e.message; }`.

All existing functions (`postJSON`, `render`, `debounce`) and all other behavior left untouched.

### Verification

| Check | Result |
|-------|--------|
| `curl` HTTP 200 for `/app.js` | 200 |
| `node --check` syntax check | Syntax OK |
| `pytest -v` (23 tests) | 23 passed, 0 failed |

---

## Deviations

None. Code was copied verbatim from the brief.

## Concerns

- **No drag-to-trim yet**: the brief's interface description mentions "drag-to-trim" but the provided code does not implement it (checkboxes only). This matches the code in the brief — drag-to-trim may be intended for a future task.
- **Static mount is conditional**: `app/main.py` only mounts the static directory if `app/web/` exists — now that the directory exists, the mount is active on every server start.
- **Deprecation warnings**: `@app.on_event("startup")` is deprecated in FastAPI. Pre-existing, not introduced here.
- **Manual click-through not done**: no real pickleball video available. Full end-to-end (upload → detect → export) must be verified manually by the user per the brief.
