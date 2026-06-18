#!/usr/bin/env bash
# One-command versioned release build of the macOS app.
# Usage: bash packaging/release.sh <version>    e.g. packaging/release.sh 1.2.0
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <version>   (e.g. $0 1.2.0)"
  exit 2
fi
VERSION="$1"
if ! echo "$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'; then
  echo "ERROR: version must be X.Y.Z (got '$VERSION')"
  exit 2
fi
export VERSION

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo "==> Releasing Cherry.Pickle v$VERSION"
bash "$ROOT/packaging/build_mac.sh"

echo ""
echo "Release v$VERSION ready:"
echo "  $ROOT/dist/CherryPickle-mac-arm64-v$VERSION.zip"
echo ""
echo "Next: send that .zip to users. They unzip, drag CherryPickle.app to"
echo "Applications, and right-click -> Open the first time (unsigned)."
