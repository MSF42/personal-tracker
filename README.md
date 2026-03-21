# Personal Tracker

A desktop app for tracking tasks, running activities, exercises, workout routines, habits, and body measurements. Built with a FastAPI backend and a Vue 3 + PrimeVue frontend, packaged as a native desktop app via Electron.

## Download

Pre-built installers are available on the [Releases](../../releases) page:

| Platform | File |
|----------|------|
| macOS | `.dmg` |
| Windows | `.exe` (installer) |
| Linux | `.AppImage` |

## Features

- **Tasks** — create, categorize, prioritize, and set due dates; supports daily/weekly/monthly recurrence
- **Running** — log runs with distance, duration, and notes; auto-calculates pace and speed; GPX import; weekly goal tracking
- **Exercises** — manage an exercise library categorized by muscle group
- **Workout Routines** — build routines from your exercise library and log sets/reps/weight
- **Habits** — track daily habits with streak counting and a 28-day chain view
- **Measurements** — log any body measurement over time with trend charts
- **Notes** — freeform notes organized in a tree structure
- **Dashboard** — daily summary with a 5-day and monthly calendar view

## Development Setup

### Requirements

- Python 3.12+
- Node.js 22+

### API

```bash
cd api
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run dev server (port 8742)
python src/main.py
```

### UI

```bash
cd ui
npm install

# Run dev server (port 3099, proxies /api to localhost:8742)
npm run dev
```

Open `http://localhost:3099` in your browser.

### Running Tests

```bash
cd api
pytest
```

### Linting & Formatting

```bash
# API
cd api
ruff check .
ruff format .

# UI
cd ui
npm run verify    # runs Prettier + ESLint + vue-tsc
```

## Building the Desktop App

### macOS

```bash
# 1. Build the API binary
cd api
pip install pyinstaller
pyinstaller personal-tracker-api.spec

# 2. Stage the binary
mkdir -p ui/electron/binaries
cp api/dist/personal-tracker-api ui/electron/binaries/personal-tracker-api
chmod +x ui/electron/binaries/personal-tracker-api

# 3. Build and package
cd ui
VITE_API_BASE_URL=http://127.0.0.1:8743 npm run build-only
npm run electron:build
```

The `.dmg` will be in `ui/dist-electron/`.

### Windows / Linux

The same steps apply — use the GitHub Actions release workflow as a reference for the exact commands on each platform (`.github/workflows/release.yml`).

## Release

Releases are automated via GitHub Actions. Push a version tag to build all three platform installers and create a GitHub Release:

```bash
git tag v1.0.0
git push origin v1.0.0
```

Tags containing `-` (e.g. `v1.0.0-beta`) are automatically marked as pre-releases.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, FastAPI, SQLite (aiosqlite) |
| Frontend | Vue 3, PrimeVue, Tailwind CSS, Vite |
| Desktop | Electron |
| Testing | pytest, pytest-asyncio |
| Linting | Ruff (Python), ESLint + Prettier (JS/TS) |
| CI/CD | GitHub Actions |

## Configuration

The API is configured via environment variables (or a `.env` file in `api/`):

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8742` | API listen port |
| `DATABASE_PATH` | `data/tracker.db` | SQLite database path |
| `LOG_LEVEL` | `info` | Logging level |
| `ENABLE_DOCS` | `true` | Enable Swagger UI at `/docs` |
| `ENVIRONMENT` | `development` | Environment name |

## License

MIT — see [LICENSE](LICENSE).
