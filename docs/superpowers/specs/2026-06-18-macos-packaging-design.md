# macOS Desktop App Packaging — Design Spec

**Date:** 2026-06-18
**Status:** Approved (implementation PARKED — UI fixes happen first)

## Summary

Package the local Highlights web app as a self-contained macOS desktop `.app`
that non-technical users can double-click. Bundle Python, OpenCV/numpy, FastAPI,
the built React UI, and the ffmpeg/ffprobe binaries. On launch it starts uvicorn
on a local ephemeral port and shows the UI in a native pywebview window. Built
on the developer's Apple Silicon Mac; shipped unsigned with first-launch
instructions.

## Decisions (from brainstorming)

- Distribution: **desktop app** (double-click), not hosted/Docker.
- OS target: **macOS only**, **arm64 (Apple Silicon) only**. Intel/universal is
  out of scope unless a user needs it.
- UI shell: **native window via pywebview** (macOS WKWebView), not a browser tab.
- Signing: **unsigned**; recipients do a one-time right-click → Open (or clear
  the quarantine attribute). No Apple Developer account.

## Goals

- One artifact (`Highlights.app`, zipped) a user unzips and runs.
- No system installs required on the user's machine (ffmpeg bundled).
- Detection/serve/export logic unchanged; data still in `~/Documents/Highlights`.
- Normal dev workflow (`uvicorn app.main:app`, `./dev.sh`) keeps working.

## Non-Goals (YAGNI)

- Windows / Intel / universal2 builds.
- Code signing / notarization / auto-update.
- Hosted multi-user service.

## Architecture

```
Highlights.app/Contents/
  MacOS/Highlights            # PyInstaller launcher executable (entry: app/desktop.py)
  Resources/
    app/ ...                  # Python backend, bundled
    frontend/dist/ ...        # built React UI, bundled
    bin/ffmpeg, bin/ffprobe   # bundled static arm64 binaries
```

Launch sequence (in `app/desktop.py`):
1. Start uvicorn **programmatically** (no `--reload`) on `127.0.0.1:<ephemeral>`
   in a background thread (uvicorn `Server.run` in a thread).
2. Poll the port until the server responds (condition-based wait, short timeout).
3. Open a pywebview window pointed at `http://127.0.0.1:<port>/`.
4. When the window closes, signal uvicorn to stop and exit.

Everything stays on localhost; no footage leaves the machine.

## Component Designs

### `app/paths.py` (new)
`resource_dir() -> Path`: returns `Path(sys._MEIPASS)` when frozen
(`getattr(sys, "frozen", False)` / `_MEIPASS` set by PyInstaller), else the repo
root (`Path(__file__).parent.parent`). Single source of truth for locating
bundled data in both dev and frozen modes.

### `app/deps.py` (modify)
- Resolve `ffmpeg`/`ffprobe` from `resource_dir()/"bin"` first; if present,
  prepend that dir to `os.environ["PATH"]` so all `subprocess` calls (probe +
  exporter) find them. Fall back to `shutil.which` for dev.
- `ffmpeg_available()`/`require_ffmpeg()` consider the bundled binaries.
- `probe_duration` continues to call `ffprobe` (now found via PATH).

### `app/main.py` (modify)
Compute `WEB_DIR = resource_dir() / "frontend" / "dist"` instead of the
`__file__`-relative path, so the mounted static UI resolves inside the bundle.

### `app/desktop.py` (new)
The launcher described in Architecture. PyInstaller's entry script. Imports the
FastAPI `app`, runs it via a threaded uvicorn `Server`, opens pywebview, handles
shutdown. Includes a fixed window title ("Highlights") and a sensible default
size.

### Dependencies
Add a `desktop` optional-dependency group: `pywebview>=5`, `pyinstaller>=6`.
(Kept out of the default install so the normal/dev path is unchanged.)

## ffmpeg Bundling

Static **arm64** `ffmpeg` + `ffprobe` placed in `packaging/bin/`. The build
script downloads them (pinned URL + checksum) if missing, then PyInstaller
bundles them into `Resources/bin/`. They are marked executable. Unsigned bundle
is acceptable for the chosen distribution model.

## Build Pipeline

`packaging/build_mac.sh`:
1. `cd frontend && npm ci && npm run build` (produces `frontend/dist`).
2. Ensure `packaging/bin/ffmpeg` and `ffprobe` exist (download+verify if not).
3. `pyinstaller packaging/Highlights.spec` (committed spec; bundles `app/`,
   `frontend/dist`, `packaging/bin`, hidden imports for uvicorn workers and
   opencv).
4. Output `dist/Highlights.app`; zip to `dist/Highlights-mac-arm64.zip`.

`packaging/Highlights.spec` is committed (not generated) so the bundle is
reproducible.

## Distribution & Install

Ship `Highlights-mac-arm64.zip`. `INSTALL.md` for recipients:
1. Unzip, drag `Highlights.app` to Applications.
2. First launch: right-click → Open → Open (bypasses the unsigned-app warning),
   or `xattr -dr com.apple.quarantine /Applications/Highlights.app`.
3. Data is saved to `~/Documents/Highlights`.

## Error Handling

- Port probe has a timeout; if uvicorn fails to start, show a pywebview error
  dialog / log to a file under `~/Documents/Highlights` rather than dying
  silently.
- If bundled ffmpeg is missing/unexecutable, `require_ffmpeg()` raises a clear
  message at startup.

## Testing

- Existing backend suite stays green (these changes don't touch detection).
- Unit test for `resource_dir()` and ffmpeg resolution: dev mode falls back to
  PATH; frozen mode (simulate by setting `sys.frozen`/`sys._MEIPASS` via
  monkeypatch) resolves the bundled `bin/`.
- **Manual smoke test (required, not unit-testable):** build the `.app`, launch,
  upload a clip, detect, export — confirm bundled ffmpeg works and the window
  renders. Budget a PyInstaller hidden-import/dylib debugging pass here
  (OpenCV/uvicorn sometimes need spec tweaks).

## Risks

- **arm64-only**: will not run on Intel Macs. Accepted per decisions.
- PyInstaller + OpenCV may need `--collect-*`/hidden-import adjustments; covered
  by the manual smoke-test debugging budget.
- Unsigned: first-launch right-click-Open is unavoidable without notarization.
