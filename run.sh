#!/usr/bin/env bash
#
# Start the Personal Tracker API and UI dev servers together.
#
#   ./run.sh          start both (Ctrl-C stops both)
#   ./run.sh api      start only the API
#   ./run.sh ui       start only the UI
#
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_DIR="$ROOT/api"
UI_DIR="$ROOT/ui"

UI_PORT=3099
DEFAULT_API_PORT=8742 # what ui/vite.config.ts proxies /api and /uploads to

RED=$'\033[31m'
GREEN=$'\033[32m'
YELLOW=$'\033[33m'
CYAN=$'\033[36m'
DIM=$'\033[2m'
RESET=$'\033[0m'

log() { printf '%s==>%s %s\n' "$CYAN" "$RESET" "$1"; }
warn() { printf '%swarn:%s %s\n' "$YELLOW" "$RESET" "$1" >&2; }
die() {
    printf '%serror:%s %s\n' "$RED" "$RESET" "$1" >&2
    exit 1
}

# --- what to run -------------------------------------------------------------

RUN_API=1
RUN_UI=1
case "${1:-both}" in
both) ;;
api) RUN_UI=0 ;;
ui) RUN_API=0 ;;
-h | --help)
    sed -n '2,8p' "$ROOT/run.sh" | sed 's/^# \{0,1\}//'
    exit 0
    ;;
*) die "unknown argument '${1}' (expected: api, ui, or nothing)" ;;
esac

# --- API port ----------------------------------------------------------------
# src/config/settings.py defaults to 8000, but the Vite proxy expects 8742.
# Respect an explicit PORT or an api/.env, otherwise force the port the UI wants.

if [ -f "$API_DIR/.env" ] && grep -qE '^[[:space:]]*PORT=' "$API_DIR/.env"; then
    API_PORT="$(grep -E '^[[:space:]]*PORT=' "$API_DIR/.env" | tail -1 |
        cut -d= -f2 | tr -d " \"'")"
elif [ -n "${PORT:-}" ]; then
    API_PORT="$PORT"
    export PORT
else
    API_PORT="$DEFAULT_API_PORT"
    export PORT="$API_PORT"
fi

if [ "$API_PORT" != "$DEFAULT_API_PORT" ]; then
    warn "API is on port $API_PORT but the Vite proxy targets $DEFAULT_API_PORT — /api calls will fail."
fi

# --- python environment ------------------------------------------------------
# uv owns the venv and resolves from uv.lock, so there is no interpreter hunting
# or pip bootstrapping to do here.

# Importing the app is the honest check — it catches every missing runtime
# dependency, not just the handful we might think to name.
app_imports() { (cd "$API_DIR" && uv run python -c 'import src.main' 2>&1); }

# --- process management ------------------------------------------------------

API_PID=""
UI_PID=""

# npm spawns vite and uvicorn --reload spawns a worker; walk the tree so nothing
# is left holding a port after Ctrl-C.
kill_tree() {
    local pid="$1" child
    for child in $(pgrep -P "$pid" 2>/dev/null); do
        kill_tree "$child"
    done
    kill "$pid" 2>/dev/null || true
}

alive() { [ -n "$1" ] && kill -0 "$1" 2>/dev/null; }

cleanup() {
    trap '' INT TERM
    # Nothing was ever started (e.g. a failed preflight) — no teardown to report.
    [ -z "$API_PID$UI_PID" ] && return 0
    printf '\n'
    log "shutting down..."
    alive "$UI_PID" && kill_tree "$UI_PID"
    alive "$API_PID" && kill_tree "$API_PID"

    # Give them a moment to close their sockets, then stop asking nicely.
    local waited=0
    while [ "$waited" -lt 50 ] && { alive "$UI_PID" || alive "$API_PID"; }; do
        sleep 0.1
        waited=$((waited + 1))
    done
    alive "$UI_PID" && kill -9 "$UI_PID" 2>/dev/null
    alive "$API_PID" && kill -9 "$API_PID" 2>/dev/null
    return 0
}
# Ctrl-C signals the whole process group, so the servers may die a beat before
# this handler runs — the flag keeps that from being reported as a crash.
SHUTDOWN=0
on_signal() {
    SHUTDOWN=1
    exit 0
}
trap cleanup EXIT
# HUP matters for the .command launcher: closing the Terminal window sends it,
# and without a handler the servers would outlive the window.
trap on_signal INT TERM HUP

prefix() { # label color < stdin
    awk -v label="$1" -v color="$2" -v reset="$RESET" \
        '{ printf "%s%s%s %s\n", color, label, reset, $0; fflush() }'
}

# lsof lives in /usr/sbin, which is absent from the minimal PATH a
# non-login shell gets (Finder-launched .command files, launchd agents). Left
# unresolved, port_busy would exit 127 and read as "port free" — a guard that
# silently stops guarding is worse than none, so say so instead.
LSOF="$(command -v lsof || true)"
if [ -z "$LSOF" ] && [ -x /usr/sbin/lsof ]; then
    LSOF=/usr/sbin/lsof
fi
[ -n "$LSOF" ] || warn "lsof not found — cannot check whether the ports are already in use"

port_busy() {
    [ -n "$LSOF" ] || return 1
    "$LSOF" -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

# --- start -------------------------------------------------------------------

if [ "$RUN_API" -eq 1 ]; then
    [ -d "$API_DIR" ] || die "no api/ directory at $API_DIR"
    port_busy "$API_PORT" && die "port $API_PORT is already in use"

    command -v uv >/dev/null ||
        die "uv not found on PATH — install it from https://docs.astral.sh/uv/"

    # create_app() mounts data/uploads as StaticFiles at import time, which is
    # before the lifespan handler that would have created it.
    mkdir -p "$API_DIR/${UPLOADS_PATH:-data/uploads}"

    # Idempotent and quick when the venv already matches uv.lock.
    (cd "$API_DIR" && uv sync --quiet) || die "uv sync failed"

    if ! IMPORT_ERR="$(app_imports)"; then
        die "api failed to import:
$IMPORT_ERR"
    fi

    log "api  ${DIM}$(cd "$API_DIR" && uv run python --version 2>&1)${RESET} -> http://127.0.0.1:$API_PORT"
    (
        cd "$API_DIR" &&
            exec uv run uvicorn src.main:app \
                --host 127.0.0.1 --port "$API_PORT" --reload
    ) > >(prefix "[api]" "$GREEN") 2>&1 &
    API_PID=$! # the subshell exec's uvicorn, so this is the server itself
fi

if [ "$RUN_UI" -eq 1 ]; then
    [ -d "$UI_DIR" ] || die "no ui/ directory at $UI_DIR"
    port_busy "$UI_PORT" && die "port $UI_PORT is already in use"
    command -v npm >/dev/null || die "npm not found on PATH"

    if [ ! -d "$UI_DIR/node_modules" ]; then
        log "ui   installing dependencies (first run)..."
        (cd "$UI_DIR" && npm install) || die "npm install failed"
    fi

    log "ui   -> http://localhost:$UI_PORT"
    (cd "$UI_DIR" && exec npm run dev) > >(prefix "[ui] " "$CYAN") 2>&1 &
    UI_PID=$!
fi

# Stay alive until one of them exits, then let the trap tear down the other.
DIED=""
while [ -z "$DIED" ]; do
    [ -n "$API_PID" ] && ! alive "$API_PID" && DIED="api"
    [ -n "$UI_PID" ] && ! alive "$UI_PID" && DIED="ui"
    [ -z "$DIED" ] && sleep 1
done

[ "$SHUTDOWN" -eq 0 ] && warn "$DIED exited unexpectedly — stopping the other"
exit 1
