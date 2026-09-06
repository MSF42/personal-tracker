#!/usr/bin/env bash
#
# Run every check the project has, backend then frontend.
#
#   ./check.sh          everything
#   ./check.sh api      ruff + mypy + pytest
#   ./check.sh ui       prettier + eslint + vue-tsc + vitest
#
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

GREEN=$'\033[32m'
RED=$'\033[31m'
CYAN=$'\033[36m'
RESET=$'\033[0m'

FAILED=()

step() { printf '\n%s==> %s%s\n' "$CYAN" "$1" "$RESET"; }

run() { # label, then command
    local label="$1"
    shift
    if "$@"; then
        printf '%s  ok%s  %s\n' "$GREEN" "$RESET" "$label"
    else
        printf '%s  FAIL%s %s\n' "$RED" "$RESET" "$label"
        FAILED+=("$label")
    fi
}

case "${1:-both}" in
both) DO_API=1 DO_UI=1 ;;
api) DO_API=1 DO_UI=0 ;;
ui) DO_API=0 DO_UI=1 ;;
*)
    printf '%serror:%s unknown argument %s (expected: api, ui, or nothing)\n' \
        "$RED" "$RESET" "$1" >&2
    exit 1
    ;;
esac

if [ "$DO_API" -eq 1 ]; then
    step "api"
    cd "$ROOT/api" || exit 1
    run "ruff check" uv run ruff check .
    run "mypy (strict)" uv run mypy src tests
    run "pytest" uv run pytest -q
fi

if [ "$DO_UI" -eq 1 ]; then
    step "ui"
    cd "$ROOT/ui" || exit 1
    run "prettier" npx prettier --check src/
    run "eslint" npx eslint .
    run "vue-tsc" npm run --silent type-check
    run "vitest" npm run --silent test
fi

printf '\n'
if [ ${#FAILED[@]} -eq 0 ]; then
    printf '%sAll checks passed.%s\n' "$GREEN" "$RESET"
    exit 0
fi
printf '%s%d check(s) failed:%s\n' "$RED" "${#FAILED[@]}" "$RESET"
printf '  - %s\n' "${FAILED[@]}"
exit 1
