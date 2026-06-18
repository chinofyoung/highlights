# macOS Desktop App Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Package the local Highlights app as a self-contained, double-clickable macOS `.app` (native pywebview window, bundled ffmpeg) while keeping the existing browser-based dev workflow completely unchanged.

**Architecture:** Add a separate desktop entry point (`app/desktop.py`) that starts the existing FastAPI app on an ephemeral local port and shows it in a pywebview window — used ONLY by the PyInstaller build. Two small shared changes (`resource_dir()` for locating bundled files, bundled-ffmpeg-first in `deps.py`) both fall back to current behavior when not frozen, so `uvicorn`/`./dev.sh` + browser is untouched. pywebview/PyInstaller live in an optional `desktop` dependency group.

**Tech Stack:** Python 3.10+, FastAPI, uvicorn, pywebview, PyInstaller; arm64 macOS. Test command: `.venv/bin/python -m pytest`.

## Global Constraints

- **Dev stays browser-based and unchanged:** `uvicorn app.main:app` and `./dev.sh` must keep working with no new required dependencies. pywebview/PyInstaller are in an optional `desktop` extra only.
- Target: **macOS arm64 only**. No Windows/Intel/universal, no signing/notarization.
- `resource_dir()` returns `sys._MEIPASS` when frozen, else the repo root — single source of truth for bundled paths; a no-op in dev.
- Bundled ffmpeg/ffprobe (static **arm64**) live under `packaging/bin/` and are bundled into the app; `deps.py` prefers them and prepends their dir to PATH, falling back to `shutil.which` for dev.
- Detection/serve/export logic and data location (`~/Documents/Highlights`) are untouched.
- Git disabled (not a repo): each task ends with a Checkpoint running the suite/build, no commit.
- Baseline before this plan: 104 passed.

---

### Task 1: `resource_dir()` helper + wire `main.py`

**Files:**
- Create: `app/paths.py`
- Modify: `app/main.py` (WEB_DIR)
- Test: `tests/test_paths.py` (create)

**Interfaces:**
- Produces: `paths.resource_dir() -> Path` — `Path(sys._MEIPASS)` when frozen, else repo root (`app/`'s parent).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_paths.py
import sys
from pathlib import Path
from app.paths import resource_dir


def test_resource_dir_dev_is_repo_root():
    d = resource_dir()
    assert (d / "app").is_dir()           # repo root contains app/
    assert (d / "frontend").exists()


def test_resource_dir_frozen_uses_meipass(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert resource_dir() == Path(str(tmp_path))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_paths.py -v`
Expected: FAIL — `ModuleNotFoundError: app.paths`.

- [ ] **Step 3: Create `app/paths.py`**

```python
import sys
from pathlib import Path


def resource_dir() -> Path:
    """Root for bundled resources.

    When frozen by PyInstaller, files are unpacked under sys._MEIPASS.
    In dev (and tests) we use the repository root (app/'s parent).
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent
```

- [ ] **Step 4: Wire `main.py` to use it**

In `app/main.py`, replace the `WEB_DIR` line. Current:
```python
WEB_DIR = Path(__file__).parent.parent / "frontend" / "dist"
```
New (add the import near the top with the others):
```python
from app.paths import resource_dir
...
WEB_DIR = resource_dir() / "frontend" / "dist"
```
(The `from pathlib import Path` import may become unused in `main.py`; remove it only if nothing else uses it.)

- [ ] **Step 5: Run tests**

Run: `.venv/bin/python -m pytest tests/test_paths.py -v`
Expected: PASS (2).

- [ ] **Step 6: Checkpoint**

Run: `.venv/bin/python -m pytest -q`
Expected: fully green (dev path unchanged — `resource_dir()` returns repo root, so `WEB_DIR` resolves exactly as before).

---

### Task 2: Bundled-ffmpeg resolution in `deps.py`

**Files:**
- Modify: `app/deps.py`
- Test: `tests/test_deps_ffmpeg.py` (create)

**Interfaces:**
- Consumes: `paths.resource_dir()` (Task 1).
- Produces: `deps.ensure_ffmpeg_on_path() -> None` (idempotently prepends `resource_dir()/bin` to `PATH` when bundled binaries exist). `ffmpeg_available()` calls it first.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_deps_ffmpeg.py
import os
import stat
from pathlib import Path
from app import deps, paths


def _make_exec(p: Path):
    p.write_text("#!/bin/sh\n")
    p.chmod(p.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def test_ensure_ffmpeg_prepends_bundled_dir(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _make_exec(bin_dir / "ffmpeg")
    _make_exec(bin_dir / "ffprobe")
    monkeypatch.setattr(paths, "resource_dir", lambda: tmp_path)
    monkeypatch.setattr(deps, "resource_dir", lambda: tmp_path)
    monkeypatch.setenv("PATH", "/usr/bin")
    deps.ensure_ffmpeg_on_path()
    assert os.environ["PATH"].split(os.pathsep)[0] == str(bin_dir)
    # idempotent: calling again doesn't double-prepend
    deps.ensure_ffmpeg_on_path()
    assert os.environ["PATH"].split(os.pathsep).count(str(bin_dir)) == 1


def test_ensure_ffmpeg_noop_without_bundle(tmp_path, monkeypatch):
    monkeypatch.setattr(deps, "resource_dir", lambda: tmp_path)  # no bin/ here
    monkeypatch.setenv("PATH", "/usr/bin")
    deps.ensure_ffmpeg_on_path()
    assert os.environ["PATH"] == "/usr/bin"   # unchanged → dev falls back to which()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_deps_ffmpeg.py -v`
Expected: FAIL — `ensure_ffmpeg_on_path` not defined.

- [ ] **Step 3: Update `app/deps.py`**

Replace the top of `app/deps.py` (imports + `ffmpeg_available`) with:

```python
import json
import os
import shutil
import subprocess
from app.paths import resource_dir


def ensure_ffmpeg_on_path() -> None:
    """If bundled ffmpeg/ffprobe exist (packaged app), prepend their dir to PATH.
    No-op in dev, where they aren't present and shutil.which finds system ffmpeg."""
    bin_dir = resource_dir() / "bin"
    if (bin_dir / "ffmpeg").exists() and (bin_dir / "ffprobe").exists():
        parts = os.environ.get("PATH", "").split(os.pathsep)
        if str(bin_dir) not in parts:
            os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")


def ffmpeg_available() -> bool:
    ensure_ffmpeg_on_path()
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
```

Leave `require_ffmpeg()` and `probe_duration()` unchanged — `require_ffmpeg()` already calls `ffmpeg_available()` (which now prepends the bundled dir), and `probe_duration()` invokes `ffprobe` via PATH.

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_deps_ffmpeg.py -v`
Expected: PASS (2).

- [ ] **Step 5: Checkpoint**

Run: `.venv/bin/python -m pytest -q`
Expected: fully green (dev: no `bin/`, PATH untouched, system ffmpeg still found).

---

### Task 3: Desktop launcher + `desktop` optional deps

**Files:**
- Create: `app/desktop.py`
- Modify: `pyproject.toml` (add `desktop` optional-dependency group)
- Test: `tests/test_desktop.py` (create)

**Interfaces:**
- Consumes: `app.main.app` (the FastAPI instance).
- Produces: `desktop._free_port() -> int`, `desktop._wait_until_up(port: int, timeout: float = 15.0) -> bool`, `desktop.main() -> None`.

- [ ] **Step 1: Write the failing test (port helpers only — not the window)**

```python
# tests/test_desktop.py
import socket
from app import desktop


def test_free_port_is_usable():
    port = desktop._free_port()
    assert isinstance(port, int) and 1024 < port < 65536
    # the returned port should be bindable
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", port))
    s.close()


def test_wait_until_up_false_for_closed_port():
    port = desktop._free_port()  # nothing listening
    assert desktop._wait_until_up(port, timeout=0.5) is False


def test_wait_until_up_true_when_listening():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    s.listen(1)
    port = s.getsockname()[1]
    try:
        assert desktop._wait_until_up(port, timeout=2.0) is True
    finally:
        s.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_desktop.py -v`
Expected: FAIL — `ModuleNotFoundError: app.desktop`.

- [ ] **Step 3: Create `app/desktop.py`**

```python
"""Desktop entry point for the packaged macOS app.

NOT used in dev — dev runs `uvicorn app.main:app` and a browser. This module
starts the same FastAPI app on a local ephemeral port and shows it in a native
pywebview window. It is the PyInstaller entry script.
"""
import socket
import threading
import time

import uvicorn

from app.main import app


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _wait_until_up(port: int, timeout: float = 15.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def main() -> None:
    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    if not _wait_until_up(port):
        raise RuntimeError("Highlights server failed to start")

    import webview  # imported lazily; only present with the `desktop` extra
    webview.create_window("Highlights", f"http://127.0.0.1:{port}/",
                          width=1280, height=860)
    webview.start()           # blocks until the window is closed
    server.should_exit = True


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Add the `desktop` optional-dependency group to `pyproject.toml`**

In `pyproject.toml`, under `[project.optional-dependencies]`, add the `desktop` line (keep `dev` as-is):

```toml
[project.optional-dependencies]
dev = ["pytest>=8.0", "httpx>=0.27"]
desktop = ["pywebview>=5", "pyinstaller>=6"]
```

- [ ] **Step 5: Run tests**

Run: `.venv/bin/python -m pytest tests/test_desktop.py -v`
Expected: PASS (3). (`import webview` is inside `main()`, so importing `app.desktop` and testing the port helpers does NOT require pywebview installed.)

- [ ] **Step 6: Checkpoint**

Run: `.venv/bin/python -m pytest -q`
Expected: fully green. Dev workflow is unaffected (this module is never imported by `app.main`).

---

### Task 4: ffmpeg binary acquisition gate (`packaging/fetch_ffmpeg.sh`)

**Files:**
- Create: `packaging/fetch_ffmpeg.sh`
- Create: `packaging/bin/.gitkeep` (empty placeholder so the dir exists)

**Interfaces:**
- Produces: a script that guarantees `packaging/bin/ffmpeg` and `packaging/bin/ffprobe` exist and are arm64 (or fails with instructions). Consumed by the build script (Task 5).

- [ ] **Step 1: Create `packaging/fetch_ffmpeg.sh`**

```bash
#!/usr/bin/env bash
# Ensures static arm64 ffmpeg + ffprobe are present in packaging/bin/.
# These are bundled into the .app so end users need no Homebrew/ffmpeg install.
set -euo pipefail

BIN="$(cd "$(dirname "$0")" && pwd)/bin"
mkdir -p "$BIN"

missing=0
for tool in ffmpeg ffprobe; do
  if [[ ! -x "$BIN/$tool" ]]; then
    missing=1
  fi
done

if [[ "$missing" -eq 1 ]]; then
  cat <<EOF
ERROR: static arm64 ffmpeg/ffprobe not found in:
  $BIN
Download static macOS arm64 builds of BOTH 'ffmpeg' and 'ffprobe', place them
there, and mark them executable:
  chmod +x "$BIN/ffmpeg" "$BIN/ffprobe"
(Static arm64 builds are available from e.g. https://www.osxexperts.net .)
EOF
  exit 1
fi

for tool in ffmpeg ffprobe; do
  desc="$(file -b "$BIN/$tool")"
  echo "$tool: $desc"
  if ! echo "$desc" | grep -qi "arm64"; then
    echo "ERROR: $BIN/$tool is not an arm64 binary."
    exit 1
  fi
done
echo "OK: arm64 ffmpeg + ffprobe present in $BIN"
```

- [ ] **Step 2: Make it executable and run the failure path**

Run:
```bash
chmod +x packaging/fetch_ffmpeg.sh
bash packaging/fetch_ffmpeg.sh; echo "exit=$?"
```
Expected: prints the ERROR with download instructions and `exit=1` (binaries not placed yet). This confirms the gate works. NOTE for the human operator: to actually build the app you must place static arm64 `ffmpeg`/`ffprobe` in `packaging/bin/` so this script exits 0.

- [ ] **Step 3: Checkpoint**

Run: `.venv/bin/python -m pytest -q`
Expected: fully green (no Python changed this task).

---

### Task 5: PyInstaller spec + build script + INSTALL.md (+ manual smoke test)

**Files:**
- Create: `packaging/Highlights.spec`
- Create: `packaging/build_mac.sh`
- Create: `INSTALL.md`

**Interfaces:**
- Consumes: `app/desktop.py` (entry), `frontend/dist` (built UI), `packaging/bin/{ffmpeg,ffprobe}` (Task 4), `resource_dir()` layout (`bin/`, `frontend/dist` relative to `_MEIPASS`).

- [ ] **Step 1: Create `packaging/Highlights.spec`**

```python
# PyInstaller spec — build from repo root: `.venv/bin/pyinstaller packaging/Highlights.spec`
import os

ROOT = os.path.abspath(os.getcwd())

a = Analysis(
    [os.path.join(ROOT, 'app', 'desktop.py')],
    pathex=[ROOT],
    binaries=[
        (os.path.join(ROOT, 'packaging', 'bin', 'ffmpeg'), 'bin'),
        (os.path.join(ROOT, 'packaging', 'bin', 'ffprobe'), 'bin'),
    ],
    datas=[
        (os.path.join(ROOT, 'frontend', 'dist'), 'frontend/dist'),
    ],
    hiddenimports=[
        'uvicorn.logging',
        'uvicorn.loops.auto',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan.on',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name='Highlights', console=False, target_arch='arm64',
)
coll = COLLECT(exe, a.binaries, a.datas, name='Highlights')
app = BUNDLE(
    coll,
    name='Highlights.app',
    icon=None,
    bundle_identifier='com.local.highlights',
)
```

- [ ] **Step 2: Create `packaging/build_mac.sh`**

```bash
#!/usr/bin/env bash
# Build the macOS .app. Requires: .venv with `pip install -e '.[desktop]'`,
# Node/npm, and static arm64 ffmpeg/ffprobe placed in packaging/bin/.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Building frontend"
( cd frontend && npm ci && npm run build )

echo "==> Checking bundled ffmpeg"
bash packaging/fetch_ffmpeg.sh

echo "==> Running PyInstaller"
.venv/bin/pyinstaller --noconfirm --clean packaging/Highlights.spec

echo "==> Zipping app"
( cd dist && rm -f Highlights-mac-arm64.zip && zip -r -y -q Highlights-mac-arm64.zip Highlights.app )

echo "Done:"
echo "  dist/Highlights.app"
echo "  dist/Highlights-mac-arm64.zip"
```

- [ ] **Step 3: Create `INSTALL.md`**

```markdown
# Installing Highlights (macOS, Apple Silicon)

1. Unzip `Highlights-mac-arm64.zip`.
2. Drag **Highlights.app** into your **Applications** folder.
3. First launch only: **right-click** the app → **Open** → **Open**.
   (It's unsigned, so a normal double-click shows an "unidentified developer"
   warning the first time. Right-click → Open bypasses it once.)
   Alternatively, in Terminal:
   `xattr -dr com.apple.quarantine /Applications/Highlights.app`
4. The app opens in its own window. Your videos and exported clips are saved in
   **~/Documents/Highlights**.

Requires an Apple Silicon (M-series) Mac.
```

- [ ] **Step 4: Make scripts executable**

Run:
```bash
chmod +x packaging/build_mac.sh packaging/fetch_ffmpeg.sh
```

- [ ] **Step 5: MANUAL smoke test (operator, not unit-testable)**

This step requires a one-time local setup and is verified by hand — there is no
automated test for a PyInstaller bundle.
```bash
.venv/bin/pip install -e '.[desktop]'      # installs pywebview + pyinstaller
# place static arm64 ffmpeg & ffprobe in packaging/bin/ (see Task 4)
bash packaging/build_mac.sh
open dist/Highlights.app
```
Verify by hand: the window opens; upload a short clip; Detect produces rallies
(proves bundled ffmpeg works); Export writes clips; files appear under
`~/Documents/Highlights`. If PyInstaller misses a module at runtime, add it to
`hiddenimports` in `Highlights.spec` and rebuild. Record the outcome.

- [ ] **Step 6: Checkpoint**

Run: `.venv/bin/python -m pytest -q`
Expected: fully green (no app code changed this task; dev workflow unaffected).

---

## Self-Review

**Spec coverage:**
- Base location & dev-unchanged → Global Constraints + Tasks 1–3 fall back when not frozen. ✅
- `resource_dir()` → Task 1. ✅
- Bundled-ffmpeg-first in deps → Task 2. ✅
- `app/desktop.py` threaded uvicorn + pywebview + port probe + shutdown → Task 3. ✅
- `desktop` optional deps (dev install unaffected) → Task 3 Step 4. ✅
- `main.py` WEB_DIR via resource_dir → Task 1 Step 4. ✅
- ffmpeg bundling (arm64, packaging/bin) → Task 4. ✅
- PyInstaller spec + build script + zip → Task 5 Steps 1–2. ✅
- INSTALL.md (unsigned right-click-Open) → Task 5 Step 3. ✅
- Manual smoke test w/ hidden-import budget → Task 5 Step 5. ✅
- arm64-only → spec target_arch='arm64' + fetch_ffmpeg arch gate. ✅

**Placeholder scan:** No TBD/TODO in code/steps. The only intentional placeholder is `packaging/bin/.gitkeep` (empty dir marker) and the operator-supplied ffmpeg binaries — both are explicit, documented requirements, not unfinished plan content. Task 5's verification is an explicit manual smoke test because a PyInstaller bundle cannot be unit-tested.

**Type/name consistency:** `resource_dir()` (Task 1) is imported in `main.py` (Task 1) and `deps.py` (Task 2). `ensure_ffmpeg_on_path()` defined/used in Task 2. `_free_port`/`_wait_until_up`/`main` in `app/desktop.py` (Task 3) match the spec entry used by `Highlights.spec` (Task 5). Bundled paths (`bin/`, `frontend/dist`) are consistent between the spec's `datas`/`binaries` targets and `resource_dir()`-relative lookups in `deps.py`/`main.py`.
