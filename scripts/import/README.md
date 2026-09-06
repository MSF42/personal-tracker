# Steve2026 spreadsheet import

`steve2026.json` is a snapshot (taken 2026-09-06) of the Google Sheet
"Steve2026": the 58-week marathon comeback running plan, the three-day
strength program, and the strength sessions logged so far. It is the input to
`import_steve2026.py`, which replays it into a running API.

```bash
# from the repo root, with ./run.sh up
uv run --project api python scripts/import/import_steve2026.py --dry-run
uv run --project api python scripts/import/import_steve2026.py --reset
```

What it creates: the exercises and routines, a workout log per completed
strength session (weights converted lb → kg), a "Workout A/B/C" task per
planned strength session, and a "Run N km" / "Long run N km" / "Race: …" task
per future planned run. Completed runs are left for GPX import through the UI.

`--reset` wipes runs, workout logs, routines and exercises first. Tasks are
never deleted. Without `--reset` the script is idempotent and skips anything
already present.
