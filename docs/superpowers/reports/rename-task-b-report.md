# Rename Task B Report — Highlights → Cherry.Pickle

**Status: DONE**

## Files Changed

| File | Change |
|------|--------|
| `packaging/CherryPickle.spec` | NEW — PyInstaller spec for Cherry.Pickle brand |
| `packaging/Highlights.spec` | DELETED |
| `packaging/build_mac.sh` | Updated spec reference, ZIP name, app dir name, echo line |
| `packaging/release.sh` | Updated brand name in echo, zip path, drag-to-Applications message |
| `INSTALL.md` | Updated title, zip filename, app name (x2), quarantine path |

## Verification Summary

- `ls packaging/*.spec` → only `CherryPickle.spec` (no stray Highlights refs)
- `grep -rn "Highlights" packaging/ | grep -v /bin/` → zero results
- `bash packaging/release.sh` → `Usage: ... exit=2` (correct no-args behavior)
- `bash packaging/fetch_ffmpeg.sh` → `exit=0` (untouched, still works)
- `.venv/bin/python -m pytest -q` → `111 passed, 3 warnings` (no regressions)

## Preserved

- `~/Documents/Highlights` data-location line in INSTALL.md left unchanged (step 5 constraint)
- `packaging/fetch_ffmpeg.sh`, `packaging/bin/`, `app/`, `pyproject.toml`, `frontend/` untouched

## Concerns

None. All changes are straightforward string substitutions with no logic impact. The `fetch_ffmpeg.sh` exit=0 confirms binaries are present and checksums match. Tests confirm app logic is unaffected.
