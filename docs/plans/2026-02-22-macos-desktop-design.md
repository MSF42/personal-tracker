# macOS Desktop App — Tauri + Bundled FastAPI Sidecar

## Context

The project is a personal health tracker with a FastAPI backend and Vue 3 frontend. An iOS version using Capacitor (local SQLite) already exists. The goal is a macOS desktop `.app` bundle that:
- Runs fully offline (no browser, no manual server startup)
- Is distributable as a `.dmg` installer
- Maintains full feature parity with the web version

**Chosen approach:** Tauri wraps the Vue 3 frontend in a native macOS WebView. The already-configured PyInstaller binary (`personal-tracker-api.spec`) is bundled as a Tauri "sidecar" — Tauri spawns it on startup and kills it on exit.

---

## Architecture

```
macOS .app bundle
├── ui/src-tauri/                        ← Tauri shell
│   ├── binaries/
│   │   └── personal-tracker-api-{arch} ← PyInstaller binary (gitignored)
│   ├── src/
│   │   ├── main.rs                      ← Tauri entry point (boilerplate)
│   │   └── lib.rs                       ← spawn/kill FastAPI sidecar
│   ├── Cargo.toml
│   ├── tauri.conf.json
│   └── icons/
│
└── Vue 3 frontend (unchanged, uses http backend)
        ↓ HTTP to http://localhost:8743
    FastAPI sidecar
        ↓
    SQLite at ~/Library/Application Support/PersonalTracker/tracker.db
```

**Port:** `8743` (avoids conflict with the dev server on `8000`)

**Startup sequence:**
1. Tauri loads WebView pointing at the bundled Vue build
2. `lib.rs` spawns the FastAPI sidecar with env vars: `PORT=8743`, `HOST=127.0.0.1`, `DATABASE_PATH=<app_data>/tracker.db`, `UPLOADS_PATH=<app_data>/uploads`
3. Vue frontend hits `http://localhost:8743/api/v1/`
4. On quit, Tauri kills the sidecar

---

## Files Created/Modified

### Modified: `api/src/main.py`
Changed hardcoded `host="127.0.0.1", port=8000` to use settings:
```python
from src.config.settings import get_settings

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(app, host=settings.host, port=settings.port)
```

### Modified: `ui/src/composables/api/backends/http/useApi.ts`
Changed `getBaseUrl()` to support `VITE_API_BASE_URL`:
```ts
function getBaseUrl(): string {
    const base = import.meta.env.VITE_API_BASE_URL ?? window.location.origin;
    return `${base}/api/v1/`;
}
```

### New: `ui/src-tauri/` (entire directory)

**`Cargo.toml`** — declares dependencies: `tauri`, `tauri-plugin-shell`, `serde`

**`tauri.conf.json`** — key settings:
- `bundle.identifier`: `com.stevefurches.personaltracker`
- `bundle.externalBin`: `["binaries/personal-tracker-api"]`
- `app.windows[0].title`: `"Personal Tracker"`
- `app.windows[0].width/height`: `1280 / 800`

**`src/main.rs`** — standard Tauri boilerplate (calls `lib::run()`)

**`src/lib.rs`** — sidecar management:
- On app setup: resolve app data dir, set env vars, spawn sidecar via `tauri_plugin_shell`
- On app exit: kill sidecar child process

**`icons/`** — generate from a source image using `tauri icon` CLI

### New: `ui/scripts/build-macos.sh`
Builds PyInstaller binary, places it in `src-tauri/binaries/`, then runs `tauri build`.

### Modified: `ui/package.json`
Added scripts:
```json
"tauri": "tauri",
"build-macos": "bash scripts/build-macos.sh"
```

---

## Dependencies

**Rust toolchain** (one-time, system-level):
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

**npm:**
```bash
cd ui
npm install -D @tauri-apps/cli
npm install @tauri-apps/api
```

**PyInstaller** (if not already installed):
```bash
pip install pyinstaller
```

---

## Known Limitation: `/uploads` Image Paths

Notes with uploaded images use `/uploads/filename.jpg` URLs. In the Tauri build, these need to resolve to `http://localhost:8743/uploads/...`. This should be addressed as a follow-up by configuring a `VITE_UPLOADS_BASE_URL` env var and updating image `src` attributes.

---

## Verification Steps

1. **Build the binary**: `cd api && pyinstaller personal-tracker-api.spec`
2. **Test the binary standalone**: `PORT=8743 ./dist/personal-tracker-api` → curl `http://localhost:8743/api/v1/health`
3. **Run Tauri dev**: `cd ui && VITE_API_BASE_URL=http://localhost:8743 npm run tauri dev`
4. **Full build**: `cd ui && npm run build-macos` → confirm `.app` and `.dmg` in `ui/src-tauri/target/release/bundle/`
5. **Test the app bundle**: Open the `.app`, create a task, restart, confirm data persists
