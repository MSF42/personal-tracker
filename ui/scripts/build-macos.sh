#!/bin/bash
set -e

# Detect architecture and map to Tauri's expected triple
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
BINARY_DEST="$UI_DIR/src-tauri/binaries/personal-tracker-api-${ARCH}"

echo "==> Building PyInstaller binary (arch: $ARCH)..."
cd "$API_DIR"
pyinstaller personal-tracker-api.spec

echo "==> Copying binary to src-tauri/binaries/..."
cp "dist/personal-tracker-api" "$BINARY_DEST"
chmod +x "$BINARY_DEST"

echo "==> Building Tauri app..."
cd "$UI_DIR"
VITE_API_BASE_URL=http://localhost:8743 npm run tauri build

echo ""
echo "Done! App bundle at: $UI_DIR/src-tauri/target/release/bundle/"
