"""Import the Steve2026 training spreadsheet into a running Personal Tracker API.

The spreadsheet was snapshotted into ``steve2026.json`` (same directory) on
2026-09-06. This script replays it through the HTTP API so every write goes
through the normal validation and search-index bookkeeping:

* exercises and the three strength routines (Workout A / B / C)
* the completed strength sessions as workout logs with per-set weights
* one task per *planned* strength session ("Workout A", due date) on the
  Mon/Wed/Sat schedule for the whole 58-week plan
* one task per *future* planned run ("Run 3.5 km", due date). Completed runs
  are not imported; import their GPX files through the UI instead.

Usage (from the repo root, with the API running via ./run.sh):

    uv run --project api python scripts/import/import_steve2026.py --dry-run
    uv run --project api python scripts/import/import_steve2026.py --reset

``--reset`` deletes every run, workout log, routine and exercise first. Tasks
are never deleted. Re-running without ``--reset`` is safe: exercises, routines,
logs and tasks that already exist are skipped.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import httpx

LB_TO_KG = 0.45359237
WEEKDAYS = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}
IMPORT_NOTE = "Imported from Steve2026 sheet"


@dataclass
class Importer:
    client: httpx.Client
    fixture: dict[str, Any]
    today: date
    dry_run: bool
    created: Counter[str] = field(default_factory=Counter)
    skipped: Counter[str] = field(default_factory=Counter)

    # -- HTTP helpers -------------------------------------------------------

    def _get(self, path: str, **params: Any) -> Any:
        resp = self.client.get(path, params=params)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, json: dict[str, Any] | None = None, **params: Any) -> Any:
        resp = self.client.post(path, json=json, params=params or None)
        if resp.status_code == 409:
            return None
        resp.raise_for_status()
        return resp.json()

    def _delete(self, path: str) -> None:
        resp = self.client.delete(path)
        if resp.status_code != 404:
            resp.raise_for_status()

    def _all_tasks(self) -> list[dict[str, Any]]:
        tasks: list[dict[str, Any]] = []
        offset = 0
        while True:
            page = self._get("/tasks", limit=100, offset=offset)
            tasks.extend(page["data"])
            if not page["has_more"] or not page["data"]:
                return tasks
            offset += len(page["data"])

    # -- Steps ------------------------------------------------------------

    def reset(self) -> None:
        for label, path in (
            ("runs", "/runs"),
            ("workout logs", "/workout-logs"),
            ("routines", "/workout-routines"),
            ("exercises", "/exercises"),
        ):
            rows = self._get(path)
            print(f"reset: deleting {len(rows)} {label}")
            if self.dry_run:
                continue
            for row in rows:
                self._delete(f"{path}/{row['id']}")

    def import_exercises(self) -> dict[str, int]:
        existing = {e["name"]: e["id"] for e in self._get("/exercises")}
        ids: dict[str, int] = {}
        for ex in self.fixture["exercises"]:
            name = ex["name"]
            if name in existing:
                ids[name] = existing[name]
                self.skipped["exercises"] += 1
                continue
            self.created["exercises"] += 1
            if self.dry_run:
                ids[name] = -1
                continue
            created = self._post("/exercises", json=ex)
            if created is None:  # raced with another writer; look it up
                created = next(e for e in self._get("/exercises") if e["name"] == name)
            ids[name] = created["id"]
        return ids

    def import_routines(self, exercise_ids: dict[str, int]) -> dict[str, int]:
        existing = {r["name"]: r["id"] for r in self._get("/workout-routines")}
        ids: dict[str, int] = {}
        for key, routine in self.fixture["routines"].items():
            name = routine["name"]
            if name in existing:
                ids[key] = existing[name]
                self.skipped["routines"] += 1
                continue
            self.created["routines"] += 1
            if self.dry_run:
                ids[key] = -1
                continue
            created = self._post(
                "/workout-routines",
                json={"name": name, "description": routine["description"]},
            )
            assert created is not None
            ids[key] = created["id"]
            for ex_name, sets, reps in routine["exercises"]:
                # This endpoint takes query parameters, not a JSON body.
                self._post(
                    f"/workout-routines/{ids[key]}/exercises",
                    exercise_id=exercise_ids[ex_name],
                    sets=sets,
                    reps=reps,
                )
                self.created["routine exercises"] += 1
        return ids

    def import_strength_sessions(
        self, routine_ids: dict[str, int], exercise_ids: dict[str, int]
    ) -> set[date]:
        existing = {(log["routine_id"], log["date"]) for log in self._get("/workout-logs")}
        completed: set[date] = set()
        for session in self.fixture["strength_sessions"]:
            when = date.fromisoformat(session["date"])
            completed.add(when)
            routine_id = routine_ids[session["routine"]]
            if (routine_id, session["date"]) in existing:
                self.skipped["workout logs"] += 1
                continue
            self.created["workout logs"] += 1
            n_sets = sum(len(e["sets"]) for e in session["exercises"])
            self.created["sets"] += n_sets
            if self.dry_run:
                continue
            log = self._post(
                "/workout-logs",
                json={"routine_id": routine_id, "date": session["date"], "notes": IMPORT_NOTE},
            )
            assert log is not None
            for ex in session["exercises"]:
                for set_number, (weight_lb, reps) in enumerate(ex["sets"], start=1):
                    self._post(
                        f"/workout-logs/{log['id']}/sets",
                        json={
                            "exercise_id": exercise_ids[ex["name"]],
                            "set_number": set_number,
                            "reps": reps,
                            "weight": to_kg(weight_lb),
                        },
                    )
        return completed

    def import_tasks(self, completed_strength: set[date]) -> None:
        existing = {(t["title"], t["due_date"], t["category"]) for t in self._all_tasks()}
        wanted = self.strength_tasks(completed_strength) + self.run_tasks()
        for task in wanted:
            key = (task["title"], task["due_date"], task["category"])
            label = f"{task['category'].lower()} tasks"
            if key in existing:
                self.skipped[label] += 1
                continue
            self.created[label] += 1
            if not self.dry_run:
                self._post("/tasks", json=task)

    def strength_tasks(self, completed: set[date]) -> list[dict[str, Any]]:
        plan = self.fixture["strength_plan"]
        start = date.fromisoformat(plan["start"])
        tasks = []
        for week in range(plan["weeks"]):
            for day, key in plan["days"].items():
                when = start + timedelta(weeks=week, days=WEEKDAYS[day])
                if when < self.today or when in completed:
                    continue
                routine = self.fixture["routines"][key]["name"]
                desc = [f"Week {week} · {routine}"]
                if week in plan["race_weeks"]:
                    desc.append(
                        "Race week — skip heavy squat/deadlift work; upper body and calf/Achilles only, reduced volume."
                    )
                elif week in plan["taper_weeks"]:
                    desc.append(
                        "Marathon taper — strength is optional; keep it light, short and upper-body only."
                    )
                tasks.append(
                    {
                        "title": f"Workout {key}",
                        "category": "Strength",
                        "due_date": when.isoformat(),
                        "priority": "medium",
                        "description": " ".join(desc),
                    }
                )
        return tasks

    def run_tasks(self) -> list[dict[str, Any]]:
        tasks = []
        for week in self.fixture["run_plan"]:
            status = week["status"]
            for session in week["sessions"]:
                when = date.fromisoformat(session["date"])
                if when < self.today or session["actual_km"]:
                    continue
                km = f"{session['planned_km']:.1f}"
                if session["day"] == "Long run" and status and status.startswith("Race"):
                    race = status.split("—", 1)[1].strip()
                    title = f"Race: {race} ({km} km)"
                elif session["day"] == "Long run":
                    title = f"Long run {km} km"
                else:
                    title = f"Run {km} km"
                desc = [f"Week {week['week']} · Phase {week['phase']}"]
                if status:
                    desc.append(status)
                if week["note"]:
                    desc.append(week["note"])
                tasks.append(
                    {
                        "title": title,
                        "category": "Running",
                        "due_date": when.isoformat(),
                        "priority": "medium",
                        "description": " — ".join(desc),
                    }
                )
        return tasks

    def set_units(self) -> None:
        for key, value in (("unit_weight", "lbs"), ("unit_distance", "km")):
            self.created[f"setting {key}={value}"] += 1
            if not self.dry_run:
                resp = self.client.put(f"/settings/{key}", json={"value": value})
                resp.raise_for_status()

    def run(self, reset: bool) -> None:
        if reset:
            self.reset()
        exercise_ids = self.import_exercises()
        routine_ids = self.import_routines(exercise_ids)
        completed = self.import_strength_sessions(routine_ids, exercise_ids)
        self.import_tasks(completed)
        self.set_units()

    def report(self) -> None:
        verb = "would create" if self.dry_run else "created"
        print(f"\n{verb}:")
        for key, n in sorted(self.created.items()):
            print(f"  {n:>5}  {key}")
        if self.skipped:
            print("skipped (already present):")
            for key, n in sorted(self.skipped.items()):
                print(f"  {n:>5}  {key}")


def to_kg(weight_lb: float) -> float | None:
    """Sheet convention: a weight of 1 means bodyweight, which the app stores as null."""
    if weight_lb <= 1:
        return None
    return round(weight_lb * LB_TO_KG, 2)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8742")
    parser.add_argument("--fixture", type=Path, default=Path(__file__).with_name("steve2026.json"))
    parser.add_argument(
        "--reset",
        action="store_true",
        help="delete all runs, workout logs, routines and exercises first",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="print what would happen without writing"
    )
    parser.add_argument(
        "--today",
        type=date.fromisoformat,
        default=date.today(),
        help="cut-off for 'future' sessions (YYYY-MM-DD)",
    )
    args = parser.parse_args(argv)

    fixture = json.loads(args.fixture.read_text())
    base_url = args.base_url.rstrip("/")
    try:
        httpx.get(f"{base_url}/health", timeout=5).raise_for_status()  # bare path, not /api/v1
    except httpx.HTTPError as exc:
        print(f"API not reachable at {base_url}: {exc}", file=sys.stderr)
        return 1
    with httpx.Client(base_url=f"{base_url}/api/v1", timeout=30) as client:
        importer = Importer(client=client, fixture=fixture, today=args.today, dry_run=args.dry_run)
        importer.run(reset=args.reset)
        importer.report()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
