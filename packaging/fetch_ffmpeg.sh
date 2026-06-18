#!/usr/bin/env bash
# Ensures static arm64 ffmpeg + ffprobe are present in packaging/bin/.
# Auto-downloads pinned builds (osxexperts.net) and verifies SHA-256, so any
# machine self-provisions reproducibly. Bundled into the .app so end users need
# no Homebrew/ffmpeg install.
#
# NOTE: the osxexperts URLs are not version-immutable. If the upstream zip is
# rebuilt, the SHA-256 check below will FAIL (by design) — update the pins
# intentionally rather than silently bundling an unexpected binary.
set -euo pipefail

BIN="$(cd "$(dirname "$0")" && pwd)/bin"
mkdir -p "$BIN"

FFMPEG_URL="https://www.osxexperts.net/ffmpeg71arm.zip"
FFPROBE_URL="https://www.osxexperts.net/ffprobe71arm.zip"
FFMPEG_SHA="6d175a4743ca50256e89a8cdd731100f9cee33bd79aeea46894d209410dc6617"
FFPROBE_SHA="df2684842eca145bd72f4724ce9cecbf38558a4d64b2aef7846680f877702baa"

fetch() {
  local tool="$1" url="$2"
  [[ -x "$BIN/$tool" ]] && return 0
  echo "Downloading $tool from $url"
  local tmp; tmp="$(mktemp -d)"
  curl -fsSL --max-time 300 -o "$tmp/$tool.zip" "$url"
  unzip -o -q "$tmp/$tool.zip" -d "$tmp"
  if [[ ! -f "$tmp/$tool" ]]; then
    echo "ERROR: '$tool' not found inside $url"; rm -rf "$tmp"; exit 1
  fi
  mv "$tmp/$tool" "$BIN/$tool"
  chmod +x "$BIN/$tool"
  rm -rf "$tmp"
}

verify() {
  local tool="$1" sha="$2"
  local got; got="$(shasum -a 256 "$BIN/$tool" | awk '{print $1}')"
  if [[ "$got" != "$sha" ]]; then
    echo "ERROR: $tool SHA-256 mismatch."
    echo "  expected $sha"
    echo "  got      $got"
    echo "Refusing to use an unverified binary. Delete $BIN/$tool and retry, or update the pin."
    exit 1
  fi
  local desc; desc="$(file -b "$BIN/$tool")"
  if ! echo "$desc" | grep -qi "arm64"; then
    echo "ERROR: $BIN/$tool is not arm64 ($desc)"; exit 1
  fi
  echo "OK: $tool ($desc), sha256 verified"
}

fetch  ffmpeg  "$FFMPEG_URL"
fetch  ffprobe "$FFPROBE_URL"
verify ffmpeg  "$FFMPEG_SHA"
verify ffprobe "$FFPROBE_SHA"
echo "ffmpeg + ffprobe ready in $BIN"
