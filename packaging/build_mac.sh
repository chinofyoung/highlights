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
.venv/bin/pyinstaller --noconfirm --clean packaging/CherryPickle.spec

echo "==> Zipping app"
ZIP="CherryPickle-mac-arm64${VERSION:+-v$VERSION}.zip"
( cd dist && rm -f "$ZIP" && zip -r -y -q "$ZIP" CherryPickle.app )

echo "Done:"
echo "  dist/CherryPickle.app"
echo "  dist/$ZIP"
