# Design: Replace Tauri/iOS with Electron Desktop App

Date: 2026-03-08

## Goal

Replace the existing Tauri + Capacitor iOS setup with Electron + electron-builder, producing a single bundled macOS `.app` that includes both the Vue 3 frontend and the FastAPI Python backend.

## What Gets Removed

- `ui/src-tauri/` — Tauri + Rust configuration
- `ui/ios/` — Capacitor iOS project
- `ui/scripts/build-macos.sh` — replaced with new version
- npm packages: `@tauri-apps/api`, `@tauri-apps/cli`, `@capacitor/core`, `@capacitor/cli`, `@capacitor/ios`, `@capacitor-community/sqlite`, `@capacitor/filesystem`
- npm scripts: `tauri`, `build-ios`, `build-macos` (replaced)

## Architecture

### Electron Main Process (`electron/main.js`)

- On app `ready`: spawn the bundled FastAPI binary from `extraResources` on port 8743
- Create a `BrowserWindow` (1280×800, resizable) loading `index.html` from the built `dist/`
- On app `before-quit`: kill the FastAPI child process cleanly

### Electron Preload (`electron/preload.js`)

- Minimal — no Node APIs exposed to renderer needed

### Vue Frontend

- Built with `VITE_API_BASE_URL=http://localhost:8743`
- Loaded via `file://` from the bundled `dist/` directory
- All API calls go to `http://localhost:8743/api/v1`

### FastAPI Binary

- Built with PyInstaller from `api/` using existing `.spec` file
- Bundled as an `extraResource` in the Electron app
- Started as a child process by the main process on launch

## electron-builder Config (in package.json)

```json
{
  "appId": "com.stevefurches.personaltracker",
  "productName": "Personal Tracker",
  "mac": { "target": "dmg", "icon": "src-electron/icons/icon.icns" },
  "extraResources": [
    { "from": "src-electron/binaries/personal-tracker-api", "to": "personal-tracker-api" }
  ],
  "files": ["dist/**", "electron/**"]
}
```

## Updated npm Scripts

| Script | Command |
|---|---|
| `electron:dev` | `VITE_API_BASE_URL=http://localhost:8743 vite && electron .` |
| `build-macos` | `bash scripts/build-macos.sh` |

## Build Script (`scripts/build-macos.sh`)

1. Activate `api/.venv`
2. Run PyInstaller → produces `api/dist/personal-tracker-api`
3. Copy binary to `ui/src-electron/binaries/personal-tracker-api-aarch64-apple-darwin` (or x86_64)
4. Run `VITE_API_BASE_URL=http://localhost:8743 npm run build-only`
5. Run `electron-builder --mac`

## Port

FastAPI runs on port **8743** (same as existing Tauri setup).
