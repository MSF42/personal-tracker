#!/usr/bin/env bash
#
# Double-clickable launcher — Finder opens .command files in Terminal.
#
# Starts the dev stack via run.sh and opens the UI once Vite answers.
# Ctrl-C, or closing the Terminal window, stops both servers.
#
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

UI_URL="http://localhost:3099"

# Finder does not source your interactive shell profile, so what we get here is
# the bare login PATH. Two things are wrong with it:
#   - uv lives in ~/.local/bin, which is not on it at all.
#   - `npm` resolves to Homebrew's Node, not the nvm version used for
#     development, so the UI would build under a different toolchain.
#   - a non-login shell's default PATH omits /usr/sbin, where lsof lives.
export PATH="$HOME/.local/bin:$PATH:/usr/sbin:/sbin"

if [ -s "$HOME/.nvm/nvm.sh" ]; then
    export NVM_DIR="$HOME/.nvm"
    # shellcheck source=/dev/null
    . "$NVM_DIR/nvm.sh" >/dev/null 2>&1
    nvm use default >/dev/null 2>&1 || true
fi

NODE_V="$(node --version 2>/dev/null || echo 'not found')"
UV_V="$(uv --version 2>/dev/null || echo 'not found')"
printf '\033[36m==>\033[0m %s\n' "$ROOT"
printf '\033[36m==>\033[0m node %s   %s\n' "$NODE_V" "$UV_V"

# Open the browser once the UI answers; give up quietly if it never does.
(
    for _ in $(seq 1 60); do
        if curl -fsS -o /dev/null "$UI_URL" 2>/dev/null; then
            open "$UI_URL"
            exit 0
        fi
        sleep 1
    done
) &
OPENER=$!

# Run run.sh as a child rather than exec'ing it, so the failure message below
# still gets a chance to print — which means signals have to be passed along by
# hand. Ctrl-C and closing the window signal the whole process group anyway;
# this covers a kill aimed at this script alone.
./run.sh &
RUN_PID=$!

cleanup() { kill "$OPENER" 2>/dev/null; }
forward() { kill -TERM "$RUN_PID" 2>/dev/null; }
trap cleanup EXIT
trap forward INT TERM HUP

wait "$RUN_PID"
status=$?
if [ "$status" -gt 128 ]; then
    # wait was interrupted by a signal; give run.sh its moment to tear down.
    wait "$RUN_PID" 2>/dev/null
    status=$?
fi

# Terminal may be set to close the window when the shell exits. On failure,
# hold it open so the error is readable.
if [ "$status" -ne 0 ]; then
    printf '\n\033[31mExited with status %s.\033[0m\n' "$status"
    read -r -n 1 -s -p "Press any key to close this window."
    printf '\n'
fi

exit "$status"
