# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Rules

- Never commit or push code unless explicitly requested.

## Project Overview

Personal Tracker — a FastAPI backend with a Vue 3 frontend for tracking tasks, running activities, exercises, and workout routines. The API code lives in `api/`, the frontend in `ui/`.

## Common Commands

Dependencies are managed with [uv](https://docs.astral.sh/uv/); `uv.lock` is the
source of truth and every Python command runs through `uv run`.

```bash
# Run both servers from the repo root (Ctrl-C stops both)
./run.sh

# Run every quality gate (ruff, mypy, pytest, eslint, vue-tsc, vitest)
./check.sh
```

### API (run from `api/` directory)

```bash
# Sync the venv to uv.lock (idempotent)
uv sync

# Run the dev server
uv run python src/main.py
# or: uv run uvicorn src.main:app --reload --host 127.0.0.1 --port 8742

# Lint, format, type-check
uv run ruff check .
uv run ruff check --fix .
uv run ruff format .
uv run mypy src tests

# Run all tests
uv run pytest

# Run a single test file
uv run pytest tests/test_tasks.py

# Run a single test by name
uv run pytest tests/test_tasks.py -k "test_create_task"

# Build standalone executable
uv sync --group build
uv run pyinstaller personal-tracker-api.spec
```

### UI (run from `ui/` directory)

```bash
# Run the dev server (port 3099, proxies /api to localhost:8742)
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
- **Composables** (`composables/api/`) — API layer using native `fetch`. `useApi` provides `getData`, `getDataArray`, `post`, `put`, `remove`. Domain composables (`useTaskApi`, `useRunningApi`) wrap these for each endpoint. The app always talks to the FastAPI backend (dev: Vite proxy; Electron: `VITE_API_BASE_URL` to the bundled API) — the old sql.js offline backend was removed.
- **Types** (`types/`) — TypeScript interfaces matching FastAPI models. Uses snake_case to match the Python API directly.
- **Router** (`router/`) — Vue Router with file-based route generation. Root `/` redirects to `/tasks`.

**Key patterns:**
- `<script setup lang="ts">` with component order: script → template → style
- PrimeVue components registered globally with `App` prefix (e.g., `AppButton`, `AppDataTable`)
- Dev server proxies `/api` to FastAPI backend at `localhost:8000`
- No authentication (personal app)
- API errors parsed from FastAPI format `{error: string, code: string}`
- Run detail page (`pages/running/[id].vue`) draws the route with Leaflet + OpenStreetMap tiles (`components/RouteMap.vue`); when tiles fail or the app is offline it falls back to a pure SVG outline (`components/RouteOutline.vue`, maths in `utils/route.ts`). `run_samples` therefore holds GPS coordinates — mind that when sharing backups or screenshots. Hovering a lap or best-effort row highlights that time span on the map and charts; best efforts store `start_seconds`/`end_seconds` (migration 29) and `backfill_segment_bounds()` recomputes them at startup for runs that have samples but no offsets.

**Section layouts:** `pages/strength.vue` and `pages/running.vue` both render `components/SectionLayout.vue` — a left rail of sub-page links on desktop that collapses to a horizontal tab row below `md`.

**Strength section:** `pages/strength.vue` is a layout (left rail: Logs / Exercises / Routines) wrapping nested routes — `/strength/logs` + `/strength/logs/[id]`, `/strength/exercises`, `/strength/routines` + `/strength/routines/[id]`; `/strength` redirects to `/strength/logs`. The rail renders only for the three section routes; `[id]` detail routes render full-width with their own container + Back button. The section list pages don't set their own `mx-auto max-w-6xl p-6` — the layout provides it.

**Running section:** `pages/running.vue` is a layout (left rail: Progress / Log) wrapping nested routes — `/running/progress` and `/running/log`; `/running` redirects to `/running/progress`. `/running/[id]` renders full-width outside the rail with its own container + Back button, same as Strength's `[id]` routes. Progress holds the stats cards (Past 7/30/365 Days, each with its best-ever window from `utils/running.ts`; the Past 7 Days card carries this Mon–Sun week's goal bar), Recent Achievements (badges from the past 30 days), Fastest by Distance (best efforts), and Weekly Progress — `components/WeeklyProgressList.vue` (planned vs actual per week) or `components/RunningCalendar.vue` (month grid, planned next to actual) — no charts — it always shows the full, unfiltered activity history.

**Training plan:** the plan is the Running tasks (one per planned run, distance only in the title — "Long run 5.0 km"); `utils/plan.ts` parses it (`parseTaskDistanceKm`, `plannedDays`, `planByWeek`) from *all* Running tasks, completed included, since a completed task is still what that week planned. A week's goal is the plan's distance when it has planned runs, otherwise the manual `running_weekly_goal_km` setting (`weeklyGoal`); the API's weekly-goal badge uses the same rule (`run_badges.planned_distance_km` mirrors the title parsing). Strength works the same way with Strength tasks: `utils/strength.ts` gives per-week workouts/volume/planned and the "weeks on plan" streak (a week is on plan with ≥ planned workouts, or ≥1 when none planned; the unfinished current week never breaks it) for the Strength Logs cards; `GET /workout-logs` includes each log's `total_sets`/`total_volume` (reps × weight, kg). Log holds an always-visible date range (presets + pickers, default past 30 days, fetched server-side via `GET /runs?date_from=&date_to=`), the Filters panel (distance/duration/pace, client-side over the loaded range), Add Run / Import GPX+FIT (including drag-and-drop), and the raw runs table; none of it affects Progress.

**Run badges & best efforts:** `services/run_badges.py` computes per-run badges (longest / fastest effort / longest time / most climb "ever" or "since <date>", first 10K/half/marathon, biggest week/month, comeback, negative split (10 km+), weekly 3+-run streak, weekly goal, plan complete — runs in the week reach the number of planned Running tasks, 500 km / 100-run milestones, passing last year's total) on every request from the whole history — badges aren't stored, so edits and back-fills never leave them stale. Only facts intrinsic to one run are stored: `first_half_seconds`/`second_half_seconds` (migration 32, moving time from the samples via `track_segments.half_splits`, set at import and by `backfill_half_splits()` at startup). Climb uses the FIT `total_ascent_m` only, and the weekly goal badge applies the current goal to every week (no goal history). Each run is judged only against earlier runs. "Since" badges need the previous record outside a 30-day window and ≥3 runs in that window. Fastest efforts use the `gpx_segments` best stretches (1K … Marathon, so a fast 5K can sit inside a 10K); runs without a track count only when their whole distance falls in a segment's band. Endpoints: `GET /runs/badges?date_from=&date_to=`, `GET /runs/{id}/badges`, `GET /runs/best-efforts`. The UI phrases badges in `utils/badges.ts`, renders them with `components/RunBadges.vue` (chips, or `compact` icons in the Log), and `useBadgeAnnouncer` toasts new badges after a run is added or imported.

**Page vs. dialog:** an entity gets a routed detail page (own URL, deep-linkable, back/forward) when it has enough content to need multi-section layout, or when a flow needs to land you on it — Running, Workout Routines, and Workout Logs all have this (maps/charts, per-set tables, session history; logging a run/workout from the dashboard redirects to its detail page). An entity stays on a dialog when it's fundamentally one short record, or when its detail view is reached from only one or two places rather than needing a shareable URL — Tasks, Habits, Measurements, and Exercises (whose "detail" is the shared `ExerciseHistoryDialog` lookup). If a dialog's usage pattern grows to need deep-linking, that's the signal to promote it to a page (as Workout Logs was, back to `pages/strength/logs/[id].vue`).

**Page container widths:** list/index pages default to `max-w-6xl`. Detail pages pick from tiers by content shape, not by feel — `max-w-3xl` for a single narrow column (`settings.vue`), `max-w-4xl` for a single column with tables (`strength/routines/[id].vue`, `strength/logs/[id].vue`), `max-w-7xl` for a two-column layout with a map/chart panel (`running/[id].vue`).

## Configuration

**API:** `pyproject.toml` holds everything. Ruff: line length 100, target py312, rules E/F/I/UP/B (ignoring E501), with FastAPI's `Depends`/`File`/etc. in `extend-immutable-calls` so B008 doesn't fire on dependency injection. Mypy runs in `strict` mode over `src` and `tests` and is expected to stay clean (`fitdecode` has no stubs, so it is the one `ignore_missing_imports` override). Pytest uses `asyncio_mode = "auto"`.

The py312 target is deliberate: the release workflow builds the shipped binary on Python 3.12, so targeting anything newer risks emitting syntax that CI cannot parse.

**UI:** ESLint with Vue + TypeScript rules and `simple-import-sort`. Prettier with single quotes, 4-space tabs, 80 char width, and `prettier-plugin-tailwindcss`. TypeScript strict mode targeting ES2023.

## Domains

`scripts/import/` holds a one-off importer (`import_steve2026.py` + JSON snapshot) that replays the Steve2026 training spreadsheet through the API; see its README.

Tasks (with recurring task support: daily/weekly/monthly), Running Activities (with computed pace/speed, yearly stats, and GPX/FIT import — FIT via `fitdecode` adds heart rate, cadence, power, laps and per-second samples in `run_laps`/`run_samples`), Exercises (categorized by muscle group: back/chest/biceps/triceps/shoulders/legs/core), Workout Routines (with routine_exercises junction table), Workout Logs (with per-set tracking), and Countdowns (title + date, shown on the Home page as days until / days since).
