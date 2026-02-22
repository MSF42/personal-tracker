# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Rules

- Never commit or push code unless explicitly requested.

## Project Overview

Personal Tracker — a FastAPI backend with a Vue 3 frontend for tracking tasks, running activities, exercises, and workout routines. The API code lives in `api/`, the frontend in `ui/`.

## Common Commands

### API (run from `api/` directory)

```bash
# Run the dev server
python src/main.py
# or: uvicorn src.main:app --reload --host 127.0.0.1 --port 8000

# Lint and format
ruff check .
ruff check --fix .
ruff format .

# Run all tests
pytest

# Run a single test file
pytest tests/test_tasks.py

# Run a single test by name
pytest tests/test_tasks.py -k "test_create_task"

# Build standalone executable
pyinstaller personal-tracker-api.spec
```

### UI (run from `ui/` directory)

```bash
# Run the dev server (port 3099, proxies /api to localhost:8000)
npm run dev

# Format, lint, and type-check
npm run verify

# Production build
npm run build

# Individual commands
npm run format    # Prettier
npm run lint      # ESLint --fix
npm run type-check # vue-tsc
```

## Architecture

**Layered structure** (`api/src/`):

- **Routes** (`routes/`) — FastAPI route handlers, input validation, HTTP concerns. All API routes prefixed with `/api/v1`.
- **Repositories** (`repositories/`) — Data access layer with raw SQL queries against SQLite. Named `SQLite{Domain}Repository`. Injected into routes via FastAPI's `Depends()`.
- **Services** (`services/`) — Business logic (currently only `task_recurrence.py` for recurring task date calculations).
- **Models** (`models/`) — Pydantic models split by purpose: `*InDB` (database representation, uses int for booleans), `*Create`/`*Update` (request input), and response models (API output with computed fields). Converter functions `{domain}_from_db()` transform DB rows to response models.
- **Database** (`db/`) — `database.py` provides async connection management with `get_db()` dependency. `migrations.py` has a versioned migration system (tracked in `schema_migrations` table) that runs automatically on startup via the app lifespan handler.
- **Config** (`config/settings.py`) — Pydantic `BaseSettings` loading from environment variables (see `.env.example`).
- **App factory** (`app.py`) — `create_app()` configures the FastAPI instance, registers routes, middleware, and exception handlers. Lifespan context manager runs migrations on startup.

**Key patterns:**
- Async throughout — all route handlers, repositories, and DB operations use `async/await`
- SQLite stores booleans as integers and dates as text; model converters handle the translation
- Custom exception hierarchy in `errors.py`: `AppError` → `NotFoundError`, `ConflictError`, `ValidationError` with global exception handlers returning `{error, code}` JSON
- `RequestLoggingMiddleware` adds `X-Request-ID` header and logs request duration

### UI (`ui/src/`)

Vue 3 + PrimeVue + Tailwind CSS application built with Vite.

- **Pages** (`pages/`) — File-based routing via `unplugin-vue-router`. Each `.vue` file becomes a route.
- **Composables** (`composables/api/`) — API layer using native `fetch`. `useApi` provides `getData`, `getDataArray`, `post`, `put`, `remove`. Domain composables (`useTaskApi`, `useRunningApi`) wrap these for each endpoint.
- **Types** (`types/`) — TypeScript interfaces matching FastAPI models. Uses snake_case to match the Python API directly.
- **Router** (`router/`) — Vue Router with file-based route generation. Root `/` redirects to `/tasks`.

**Key patterns:**
- `<script setup lang="ts">` with component order: script → template → style
- PrimeVue components registered globally with `App` prefix (e.g., `AppButton`, `AppDataTable`)
- Dev server proxies `/api` to FastAPI backend at `localhost:8000`
- No authentication (personal app)
- API errors parsed from FastAPI format `{error: string, code: string}`

## Configuration

**API:** Ruff is configured in `pyproject.toml`: line length 100, Python 3.14 target, rules E/F/I (ignoring E501). Pytest uses `asyncio_mode = "auto"` for async test support.

**UI:** ESLint with Vue + TypeScript rules and `simple-import-sort`. Prettier with single quotes, 4-space tabs, 80 char width, and `prettier-plugin-tailwindcss`. TypeScript strict mode targeting ES2023.

## Domains

Tasks (with recurring task support: daily/weekly/monthly), Running Activities (with computed pace/speed and yearly stats), Exercises (categorized by muscle group), Workout Routines (with routine_exercises junction table), and Workout Logs (with per-set tracking).
