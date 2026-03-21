#!/bin/bash
set -e

RAW_ARCH=$(uname -m)
if [ "$RAW_ARCH" = "arm64" ]; then
    ARCH="aarch64-apple-darwin"
elif [ "$RAW_ARCH" = "x86_64" ]; then
    ARCH="x86_64-apple-darwin"
else
    echo "Unsupported architecture: $RAW_ARCH" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
UI_DIR="$SCRIPT_DIR/.."
API_DIR="$UI_DIR/../api"
BINARY_SRC="$API_DIR/dist/personal-tracker-api"
BINARY_DEST="$UI_DIR/electron/binaries/personal-tracker-api"

echo "==> Building PyInstaller binary (arch: $ARCH)..."
cd "$API_DIR"
source .venv/bin/activate
pyinstaller personal-tracker-api.spec

echo "==> Staging binary for electron-builder..."
mkdir -p "$UI_DIR/electron/binaries"
cp "$BINARY_SRC" "$BINARY_DEST"
chmod +x "$BINARY_DEST"

echo "==> Building Vue frontend..."
cd "$UI_DIR"
VITE_API_BASE_URL=http://127.0.0.1:8743 npm run build-only

echo "==> Packaging with electron-builder..."
npm run electron:build

echo ""
echo "Done! App bundle at: $UI_DIR/dist-electron/"
