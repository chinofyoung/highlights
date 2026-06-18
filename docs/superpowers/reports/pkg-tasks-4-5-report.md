# Tasks 4 & 5 — macOS Packaging Scaffolding Report

**Date:** 2026-06-18

---

## Files Created

| File | Purpose |
|---|---|
| `packaging/fetch_ffmpeg.sh` | Task 4 Step 1 — binary acquisition gate |
| `packaging/bin/.gitkeep` | Task 4 Step 1 — empty dir placeholder |
| `packaging/Highlights.spec` | Task 5 Step 1 — PyInstaller spec |
| `packaging/build_mac.sh` | Task 5 Step 2 — orchestrating build script |
| `INSTALL.md` | Task 5 Step 3 — end-user install instructions |

All five files were created verbatim from the plan. `packaging/fetch_ffmpeg.sh` and `packaging/build_mac.sh` were made executable via `chmod +x`.

---

## fetch_ffmpeg.sh Failure-Path Output

```
ERROR: static arm64 ffmpeg/ffprobe not found in:
  /Users/chinoyoung/code/highlights/packaging/bin
Download static macOS arm64 builds of BOTH 'ffmpeg' and 'ffprobe', place them
there, and mark them executable:
  chmod +x "/Users/chinoyoung/code/highlights/packaging/bin/ffmpeg" "/Users/chinoyoung/code/highlights/packaging/bin/ffprobe"
(Static arm64 builds are available from e.g. https://www.osxexperts.net .)
exit=1
```

Gate confirmed working: exits 1 with actionable instructions when binaries are absent.

---

## pytest Result

```
111 passed, 3 warnings in 8.78s
```

Fully green. No Python was modified in Tasks 4 or 5; the test count matches the post-Tasks-1-3 baseline (111 passed, same 3 pre-existing deprecation warnings).

---

## Self-Review: Spec Paths / datas / binaries vs. resource_dir Layout

**`packaging/Highlights.spec` binaries targets:**
- `(ROOT/packaging/bin/ffmpeg, 'bin')` — bundles to `_MEIPASS/bin/ffmpeg`
- `(ROOT/packaging/bin/ffprobe, 'bin')` — bundles to `_MEIPASS/bin/ffprobe`

**`packaging/Highlights.spec` datas targets:**
- `(ROOT/frontend/dist, 'frontend/dist')` — bundles to `_MEIPASS/frontend/dist`

**`resource_dir()` consumers:**
- `deps.py` (`ensure_ffmpeg_on_path`): reads `resource_dir() / "bin"` → resolves to `_MEIPASS/bin/` — matches spec `binaries` target `'bin'`. ✅
- `main.py` (`WEB_DIR`): reads `resource_dir() / "frontend" / "dist"` → resolves to `_MEIPASS/frontend/dist` — matches spec `datas` target `'frontend/dist'`. ✅

Path consistency is verified. The three-layer chain (spec bundles to `_MEIPASS/<subdir>`, `resource_dir()` returns `_MEIPASS` when frozen, consumers use `resource_dir() / <subdir>`) is internally consistent.

---

## Concerns

1. **Case-sensitive working directory path:** When `fetch_ffmpeg.sh` resolves `$(dirname "$0")`, the shell reported the bin path as `/Users/chinoyoung/code/highlights/packaging/bin` (lowercase `c`) because the script was invoked via the `packaging/` relative path from the shell's cwd. The actual files live under `/Users/chinoyoung/Code/highlights/` (uppercase `C`). This is a macOS HFS+ case-insensitive alias — functionally identical on macOS, and the gate still exits 1 correctly. No action needed, but worth noting.

2. **`packaging/bin/` not in `.gitignore`:** The plan only requires `.gitkeep`. If this project is ever initialized as a git repo, the operator should add `packaging/bin/ffmpeg` and `packaging/bin/ffprobe` to `.gitignore` (large binaries should not be committed). Not a blocker for packaging.

3. **PyInstaller not installed yet:** The `desktop` optional dependency group (`pywebview>=5`, `pyinstaller>=6`) must be installed before `build_mac.sh` can run. This is an expected operator step (Task 5 Step 5) and is documented in `build_mac.sh`'s header comment and in the plan's manual smoke-test step.

4. **`frontend/dist` must exist before pyinstaller runs:** `build_mac.sh` runs `npm ci && npm run build` first, which will create `frontend/dist`. If the operator runs `pyinstaller` directly without going through `build_mac.sh`, the datas path will be missing and the bundle will fail. The spec comment directs the operator to use `build_mac.sh`.
