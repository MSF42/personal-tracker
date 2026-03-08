# Electron Desktop App Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace Tauri + Capacitor iOS with Electron + electron-builder, producing a single bundled macOS `.app` containing the Vue 3 frontend and FastAPI backend.

**Architecture:** Electron main process spawns the PyInstaller-built FastAPI binary as a child process on port 8743, then loads the built Vue `dist/` via `file://`. electron-builder packages everything into a `.dmg`.

**Tech Stack:** Electron 36+, electron-builder, Vue 3, FastAPI (PyInstaller binary)

---

### Task 1: Remove Tauri and Capacitor packages and files

**Files:**
- Delete: `ui/src-tauri/`
- Delete: `ui/ios/`
- Delete: `ui/capacitor.config.ts`
- Modify: `ui/package.json`

**Step 1: Uninstall Tauri and Capacitor npm packages**

Run from `ui/`:
```bash
npm uninstall @tauri-apps/api @tauri-apps/cli @capacitor/core @capacitor/cli @capacitor/ios @capacitor/filesystem @capacitor-community/sqlite
```

Expected: packages removed, no errors.

**Step 2: Delete Tauri and Capacitor directories and config**

```bash
rm -rf src-tauri ios capacitor.config.ts
```

**Step 3: Remove old scripts from package.json**

In `ui/package.json`, remove these scripts:
```json
"build-ios": "VITE_BACKEND=local npm run build && npx cap sync ios",
"tauri": "tauri",
"build-macos": "bash scripts/build-macos.sh"
```

**Step 4: Verify no Tauri/Capacitor references remain in source**

```bash
grep -r "@tauri-apps\|@capacitor" src/ --include="*.ts" --include="*.vue"
```

Expected: no output (the only Capacitor reference — a dynamic import in `src/composables/api/backends/local/useNoteApi.ts` — is in the local/iOS backend which is not used in the Electron build, so leave it alone).

**Step 5: Commit**

```bash
git add -A
git commit -m "chore: remove Tauri and Capacitor iOS setup"
```

---

### Task 2: Install Electron and electron-builder

**Files:**
- Modify: `ui/package.json`

**Step 1: Install packages**

Run from `ui/`:
```bash
npm install --save-dev electron electron-builder
```

Expected: installs without errors. Electron 36+ should install.

**Step 2: Verify install**

```bash
./node_modules/.bin/electron --version
./node_modules/.bin/electron-builder --version
```

Expected: version strings printed (e.g. `v36.x.x`).

**Step 3: Commit**

```bash
git add package.json package-lock.json
git commit -m "chore: install electron and electron-builder"
```

---

### Task 3: Create Electron main process

**Files:**
- Create: `ui/electron/main.js`
- Create: `ui/electron/preload.js`

**Step 1: Create the preload script**

Create `ui/electron/preload.js`:
```js
// No Node APIs exposed to renderer — contextIsolation is on
```

**Step 2: Create the main process**

Create `ui/electron/main.js`:
```js
const { app, BrowserWindow } = require('electron')
const path = require('path')
const { spawn } = require('child_process')

let apiProcess = null

function getApiBinaryPath() {
    if (app.isPackaged) {
        // electron-builder places extraResources at process.resourcesPath
        return path.join(process.resourcesPath, 'personal-tracker-api')
    }
    // Dev: binary staged in electron/binaries/
    const arch = process.arch === 'arm64' ? 'aarch64-apple-darwin' : 'x86_64-apple-darwin'
    return path.join(__dirname, 'binaries', `personal-tracker-api-${arch}`)
}

function startApi() {
    const binaryPath = getApiBinaryPath()
    const userDataPath = app.getPath('userData')
    const dbPath = path.join(userDataPath, 'tracker.db')
    const uploadsPath = path.join(userDataPath, 'uploads')

    // Ensure data directories exist
    require('fs').mkdirSync(uploadsPath, { recursive: true })

    apiProcess = spawn(binaryPath, [], {
        env: {
            ...process.env,
            PORT: '8743',
            HOST: '127.0.0.1',
            DATABASE_PATH: dbPath,
            UPLOADS_PATH: uploadsPath,
        },
    })

    apiProcess.stdout.on('data', (d) => console.log('[api]', d.toString()))
    apiProcess.stderr.on('data', (d) => console.error('[api]', d.toString()))
    apiProcess.on('error', (err) => console.error('[api] failed to start:', err))
}

function waitForApi(url, retries, delay, callback) {
    const http = require('http')
    http.get(url, () => callback())
        .on('error', () => {
            if (retries <= 0) {
                console.error('[api] did not become ready in time')
                callback()
                return
            }
            setTimeout(() => waitForApi(url, retries - 1, delay, callback), delay)
        })
}

function createWindow() {
    const win = new BrowserWindow({
        width: 1280,
        height: 800,
        resizable: true,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false,
        },
    })

    if (app.isPackaged) {
        win.loadFile(path.join(__dirname, '..', 'dist', 'index.html'))
    } else {
        win.loadURL('http://localhost:3099')
    }
}

app.whenReady().then(() => {
    startApi()
    // Poll until API is up, then open the window
    waitForApi('http://127.0.0.1:8743/api/v1/health', 30, 500, createWindow)

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) createWindow()
    })
})

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit()
})

app.on('before-quit', () => {
    if (apiProcess) {
        apiProcess.kill()
        apiProcess = null
    }
})
```

Note: `waitForApi` polls `GET /api/v1/health` up to 30 times (500ms apart = 15s max) before giving up and opening the window anyway. If the API doesn't have a `/health` endpoint yet, add one (see Task 4) or change the URL to any fast endpoint like `/api/v1/tasks`.

**Step 3: Commit**

```bash
git add electron/
git commit -m "feat: add electron main process and preload"
```

---

### Task 4: Add a health endpoint to FastAPI (if missing)

**Files:**
- Check: `api/src/routes/`

**Step 1: Check if a health endpoint exists**

```bash
grep -r "health" /Users/stevefurches/Documents/Steve/personal-tracker/api/src/routes/ --include="*.py"
```

If a `/api/v1/health` endpoint exists, skip to Task 5.

**Step 2: Add health route**

In `api/src/app.py`, find where routes are registered and add:
```python
@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}
```

Or add it to an appropriate existing router file if the project uses routers.

**Step 3: Test it**

Start the API locally and verify:
```bash
curl http://127.0.0.1:8000/api/v1/health
```
Expected: `{"status":"ok"}`

**Step 4: Commit**

```bash
git add api/src/
git commit -m "feat: add health check endpoint"
```

---

### Task 5: Switch Vue Router to hash history

**Files:**
- Modify: `ui/src/router/index.ts`

**Why:** When Electron loads `dist/index.html` via `file://`, HTML5 history routing breaks on page reload. Hash history (`#/tasks`) works correctly with `file://` URLs.

**Step 1: Update router**

In `ui/src/router/index.ts`, change:
```ts
import { createRouter, createWebHistory } from 'vue-router';
import { routes } from 'vue-router/auto-routes';

export const router = createRouter({
    history: createWebHistory(),
    routes,
});
```
To:
```ts
import { createRouter, createWebHashHistory } from 'vue-router';
import { routes } from 'vue-router/auto-routes';

export const router = createRouter({
    history: createWebHashHistory(),
    routes,
});
```

**Step 2: Verify dev server still works**

```bash
npm run dev
```

Open `http://localhost:3099` — navigation should still work with `#/` prefix in URLs.

**Step 3: Commit**

```bash
git add src/router/index.ts
git commit -m "fix: switch to hash history for Electron file:// compatibility"
```

---

### Task 6: Configure electron-builder and update package.json

**Files:**
- Modify: `ui/package.json`

**Step 1: Add `main` entry point and scripts**

In `ui/package.json`, add/update:
```json
{
  "main": "electron/main.js",
  "scripts": {
    "electron:dev": "npm run dev",
    "electron:start": "electron .",
    "build-macos": "bash scripts/build-macos.sh"
  }
}
```

Note: `electron:dev` just runs the Vite dev server. In a separate terminal run `npm run electron:start` to open the Electron window pointing at the dev server.

**Step 2: Add electron-builder config**

In `ui/package.json`, add a top-level `"build"` key:
```json
"build": {
  "appId": "com.stevefurches.personaltracker",
  "productName": "Personal Tracker",
  "directories": {
    "output": "dist-electron"
  },
  "files": [
    "dist/**",
    "electron/**",
    "!electron/binaries"
  ],
  "extraResources": [
    {
      "from": "electron/binaries/personal-tracker-api",
      "to": "personal-tracker-api"
    }
  ],
  "mac": {
    "target": "dmg",
    "icon": "electron/icons/icon.icns"
  }
}
```

**Step 3: Copy the Tauri icon for Electron**

```bash
mkdir -p electron/icons
```

If you have `src-tauri/icons/icon.icns` still (before deleting in Task 1), copy it now. Otherwise source an `.icns` from `icon.png` at the project root using `iconutil` or sips:
```bash
# Create iconset from the root icon.png
mkdir -p /tmp/icon.iconset
sips -z 1024 1024 ../icon.png --out /tmp/icon.iconset/icon_512x512@2x.png
sips -z 512 512 ../icon.png --out /tmp/icon.iconset/icon_512x512.png
sips -z 256 256 ../icon.png --out /tmp/icon.iconset/icon_256x256.png
sips -z 128 128 ../icon.png --out /tmp/icon.iconset/icon_128x128.png
sips -z 32 32 ../icon.png --out /tmp/icon.iconset/icon_32x32.png
sips -z 16 16 ../icon.png --out /tmp/icon.iconset/icon_16x16.png
iconutil -c icns /tmp/icon.iconset -o electron/icons/icon.icns
```

**Step 4: Commit**

```bash
git add package.json electron/icons/
git commit -m "chore: configure electron-builder"
```

---

### Task 7: Update build-macos.sh

**Files:**
- Modify: `ui/scripts/build-macos.sh`

**Step 1: Rewrite the script**

Replace contents of `ui/scripts/build-macos.sh`:
```bash
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
VITE_API_BASE_URL=http://localhost:8743 npm run build-only

echo "==> Packaging with electron-builder..."
npm run electron:build

echo ""
echo "Done! App bundle at: $UI_DIR/dist-electron/"
```

**Step 2: Add electron:build script to package.json**

```json
"electron:build": "electron-builder --mac"
```

**Step 3: Add electron/binaries/ to .gitignore**

In `ui/.gitignore` (or root `.gitignore`), add:
```
electron/binaries/
```

**Step 4: Commit**

```bash
git add scripts/build-macos.sh package.json .gitignore
git commit -m "chore: update build-macos.sh for Electron"
```

---

### Task 8: Verify dev workflow

**Step 1: Start FastAPI dev server (terminal 1)**

```bash
cd api && source .venv/bin/activate && python src/main.py
```

Expected: API running on port 8000. (Note: for dev, the Electron main.js loads `http://localhost:3099` from the Vite dev server, and the Vue app calls the API via Vite's proxy — so the dev API runs on 8000 via the proxy, not 8743.)

**Step 2: Start Vite dev server (terminal 2)**

```bash
cd ui && npm run dev
```

Expected: Vite serving on `http://localhost:3099`.

**Step 3: Launch Electron (terminal 3)**

```bash
cd ui && npm run electron:start
```

Expected: Electron window opens showing the app. Note: in dev mode, the main process skips starting the API binary and just loads the Vite dev server URL. Navigation and API calls should work.

**Step 4: Verify navigation**

Click through Tasks, Running, Exercises pages — URLs should show `#/tasks`, `#/running`, etc. in the window title bar (or check devtools).

---

### Task 9: Verify production build

**Step 1: Run build-macos**

```bash
cd ui && npm run build-macos
```

Expected: completes without errors, `dist-electron/` contains a `.dmg`.

**Step 2: Install and test the DMG**

- Open `dist-electron/Personal Tracker-*.dmg`
- Drag app to Applications
- Launch the app
- Verify the app opens, data loads, and navigation works

**Step 3: Check API process**

```bash
pgrep -la personal-tracker-api
```

Expected: the FastAPI binary process is running while the app is open, and disappears when you quit the app.
