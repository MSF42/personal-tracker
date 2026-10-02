"""Run badges: per-run achievements ("Longest run since 7 May 2019", ...).

Every badge is judged as of the run itself, against earlier runs only, so later
runs never change it. Badges aren't stored: one chronological pass over the
whole history is cheap (each record lookup is a binary search), and computing
means they're always right after a run is edited, deleted or back-filled. Only
facts intrinsic to one run (its half splits) are stored, on the run itself.

Runs are ordered by (date, start_time, id); a manual run with no start time
sorts before a recorded run on the same day.
"""

import re
from bisect import bisect_right
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from src.models.running import BadgeKind, RunBadge
from src.services.track_segments import SEGMENT_DEFS

# RunRecord has a `date` field, which shadows the type inside the class body.
Day = date

# A "since" badge needs the previous record to be outside this trailing
# window (so the run is the best in at least the last 30 days) ...
WINDOW_DAYS = 30
# ... and needs this many runs inside the window, counting the run itself, so
# the first runs after a break don't trivially "beat" an empty month.
MIN_RUNS_IN_WINDOW = 3
# An "ever" badge needs this much earlier history to compare against.
MIN_EARLIER_FOR_EVER = 3
# "First run in N days" from this gap upwards.
COMEBACK_DAYS = 14
# Biggest week/month must beat at least this many preceding periods.
WEEK_LOOKBACK = 4
MONTH_LOOKBACK = 3
# First-of-distance badges, largest first; thresholds are the race distances.
FIRST_OF = ("Marathon", "Half Marathon", "10K")
# Climb counts only from a recorded ascent of at least this much.
MIN_CLIMB_M = 20
# Negative split: second half faster by at least this fraction, on runs of at
# least this distance (shorter runs mostly split negative just from warming up).
NEGATIVE_SPLIT_MARGIN = 0.01
NEGATIVE_SPLIT_MIN_KM = 10.0
# Weekly streak: consecutive Mon–Sun weeks with at least this many runs,
# celebrated every STREAK_STEP weeks.
STREAK_MIN_RUNS = 3
STREAK_STEP = 4
# Running-total milestones.
DISTANCE_MILESTONE_KM = 500
RUN_MILESTONE = 100
_SEGMENT_MIN_KM = {name: lo for name, lo, _ in SEGMENT_DEFS}
_SEGMENT_ORDER = {name: i for i, (name, _, _) in enumerate(SEGMENT_DEFS)}


class RecordBook[K]:
    """Answers "most recent earlier entry with value >= v" in O(log n).

    Entries are kept on a stack whose values strictly decrease from oldest to
    newest: a new entry evicts every older one it ties or beats, since it is
    both more recent and at least as good. For "lower is better" quantities
    (durations), record the negated value.
    """

    def __init__(self) -> None:
        self._neg_values: list[float] = []  # increasing
        self._keys: list[K] = []
        self.count = 0  # every entry ever added, evicted or not

    def query(self, value: float) -> K | None:
        i = bisect_right(self._neg_values, -value) - 1
        return self._keys[i] if i >= 0 else None

    def add(self, value: float, key: K) -> None:
        while self._neg_values and -self._neg_values[-1] <= value:
            self._neg_values.pop()
            self._keys.pop()
        self._neg_values.append(-value)
        self._keys.append(key)
        self.count += 1


@dataclass
class RunRecord:
    id: int
    date: str  # YYYY-MM-DD
    distance_km: float
    duration_seconds: int
    start_time: str | None = None
    # Best effort per standard distance ("5K" -> seconds), see efforts_for().
    efforts: dict[str, int] = field(default_factory=dict)
    ascent_m: float | None = None  # recorded by the watch (FIT) only
    first_half_seconds: float | None = None  # moving time, from the track
    second_half_seconds: float | None = None

    @property
    def day(self) -> Day:
        return Day.fromisoformat(self.date)


def efforts_for(
    distance_km: float, duration_seconds: int, segments: dict[str, int]
) -> dict[str, int]:
    """A run's best effort at each standard distance.

    Recorded tracks have their fastest stretches already detected (segments).
    A run with no track counts only where its whole distance falls inside a
    standard distance's band (a 5.0 km manual run is a 5K effort at its full
    time) — anything else would be a guess.
    """
    if segments:
        return dict(segments)
    return {
        name: duration_seconds
        for name, lo, hi in SEGMENT_DEFS
        if lo <= distance_km <= hi and duration_seconds > 0
    }


def build_records(
    run_rows: list[dict[str, Any]], segment_rows: list[dict[str, Any]]
) -> list[RunRecord]:
    """RunRecords from the rows of SQLiteRunningRepository.get_history_for_badges()."""
    segments: dict[int, dict[str, int]] = {}
    for seg in segment_rows:
        segments.setdefault(seg["running_activity_id"], {})[seg["segment_name"]] = seg[
            "duration_seconds"
        ]
    return [
        RunRecord(
            id=row["id"],
            # Manual runs may carry a full ISO timestamp; badges work in days.
            date=row["date"][:10],
            start_time=row["start_time"],
            distance_km=row["distance_km"],
            duration_seconds=row["duration_seconds"],
            efforts=efforts_for(
                row["distance_km"], row["duration_seconds"], segments.get(row["id"], {})
            ),
            ascent_m=row["total_ascent_m"],
            first_half_seconds=row["first_half_seconds"],
            second_half_seconds=row["second_half_seconds"],
        )
        for row in run_rows
    ]


_DISTANCE_IN_TITLE = re.compile(r"(\d+(?:\.\d+)?)\s*km", re.IGNORECASE)


def planned_distance_km(title: str) -> float | None:
    """The last "N km" in a planned run's title ("Long run 5.0 km",
    "Race: ... (21.1 km)") — mirrors parseTaskDistanceKm in ui/src/utils/plan.ts."""
    matches = _DISTANCE_IN_TITLE.findall(title)
    return float(matches[-1]) if matches else None


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _month_index(d: date) -> int:
    return d.year * 12 + d.month - 1


def _month_start(index: int) -> date:
    return date(index // 12, index % 12 + 1, 1)


def _record_badge(
    kind: BadgeKind,
    prev: RunRecord | None,
    book_count: int,
    value: float,
    window_start: date,
    busy_window: bool,
) -> RunBadge | None:
    """Ever (no earlier run as good) or since (last as-good run predates the window)."""
    if prev is None:
        if book_count < MIN_EARLIER_FOR_EVER:
            return None
        return RunBadge(kind=kind, ever=True, value=value)
    if prev.day < window_start and busy_window:
        return RunBadge(kind=kind, since=prev.date, value=value)
    return None


def compute_badges(
    runs: list[RunRecord],
    planned_runs: Iterable[tuple[str, str]] = (),
    weekly_goal_km: float | None = None,
) -> dict[int, list[RunBadge]]:
    """Badges for every run, keyed by run id (runs without badges omitted).

    `planned_runs` are the training plan's Running tasks as (due date, title).
    A week's goal is the plan's distance for it when it has planned runs;
    otherwise `weekly_goal_km`, the current manual goal (there is no history of
    past goals, so it applies to every unplanned week).
    """
    planned_per_week: Counter[date] = Counter()
    planned_km_per_week: defaultdict[date, float] = defaultdict(float)
    for due, title in planned_runs:
        week = _week_start(Day.fromisoformat(due[:10]))
        planned_per_week[week] += 1
        planned_km_per_week[week] += planned_distance_km(title) or 0.0
    ordered = sorted(runs, key=lambda r: (r.date, r.start_time or "", r.id))
    result: dict[int, list[RunBadge]] = {}

    longest = RecordBook[RunRecord]()
    longest_time = RecordBook[RunRecord]()
    climb = RecordBook[RunRecord]()
    week_runs: Counter[date] = Counter()
    year_km: defaultdict[int, float] = defaultdict(float)
    total_km = 0.0
    fastest: dict[str, RecordBook[RunRecord]] = {}
    weeks = RecordBook[date]()
    months = RecordBook[int]()
    week_key: date | None = None
    week_total = 0.0
    month_key: int | None = None
    month_total = 0.0
    window_lo = 0

    for i, run in enumerate(ordered):
        day = run.day
        window_start = day - timedelta(days=WINDOW_DAYS - 1)
        while ordered[window_lo].day < window_start:
            window_lo += 1
        busy_window = i - window_lo + 1 >= MIN_RUNS_IN_WINDOW

        badges: list[RunBadge] = []

        # Longest run, or failing that the longest time on feet.
        distance_badge = _record_badge(
            "longest",
            longest.query(run.distance_km),
            longest.count,
            run.distance_km,
            window_start,
            busy_window,
        )
        if distance_badge:
            badges.append(distance_badge)
        else:
            time_badge = _record_badge(
                "longest_time",
                longest_time.query(run.duration_seconds),
                longest_time.count,
                run.duration_seconds,
                window_start,
                busy_window,
            )
            if time_badge:
                badges.append(time_badge)

        # Fastest effort: only the largest standard distance that earns one.
        best_effort: RunBadge | None = None
        for name, seconds in run.efforts.items():
            book = fastest.setdefault(name, RecordBook[RunRecord]())
            badge = _record_badge(
                "fastest", book.query(-seconds), book.count, seconds, window_start, busy_window
            )
            if badge and (
                best_effort is None
                or _SEGMENT_ORDER[name] > _SEGMENT_ORDER[best_effort.effort or ""]
            ):
                badge.effort = name
                best_effort = badge
        if best_effort:
            badges.append(best_effort)

        # First 10K / half / marathon, ever or since.
        for name in FIRST_OF:
            threshold = _SEGMENT_MIN_KM[name]
            if run.distance_km < threshold:
                continue
            prev = longest.query(threshold)
            if prev is None:
                badges.append(RunBadge(kind="first_distance", effort=name, ever=True))
            elif prev.day < window_start:
                badges.append(RunBadge(kind="first_distance", effort=name, since=prev.date))
            break

        # Biggest week / month: awarded when this run pushes the period's total
        # further back in history than it already reached. Like the other
        # "since" badges it needs a busy window, so the first run back after a
        # long break doesn't make a tiny week "the biggest since" the break.
        this_week = _week_start(day)
        if this_week != week_key:
            if week_key is not None:
                weeks.add(week_total, week_key)
            week_key, week_total = this_week, 0.0
        before = weeks.query(week_total) if week_total > 0 else None
        week_total += run.distance_km
        after = weeks.query(week_total)
        cutoff = this_week - timedelta(weeks=WEEK_LOOKBACK)
        if _pushed_back(before, after, week_total > run.distance_km, weeks.count) and (
            after is None or (after < cutoff and busy_window)
        ):
            badges.append(
                RunBadge(
                    kind="biggest_week",
                    ever=after is None,
                    since=after.isoformat() if after else None,
                    value=week_total,
                )
            )

        this_month = _month_index(day)
        if this_month != month_key:
            if month_key is not None:
                months.add(month_total, month_key)
            month_key, month_total = this_month, 0.0
        before_m = months.query(month_total) if month_total > 0 else None
        month_total += run.distance_km
        after_m = months.query(month_total)
        if _pushed_back(before_m, after_m, month_total > run.distance_km, months.count) and (
            after_m is None or (after_m <= this_month - MONTH_LOOKBACK - 1 and busy_window)
        ):
            badges.append(
                RunBadge(
                    kind="biggest_month",
                    ever=after_m is None,
                    since=_month_start(after_m).isoformat() if after_m is not None else None,
                    value=month_total,
                )
            )

        # Most climb (watch runs only) and negative split.
        if run.ascent_m is not None and run.ascent_m >= MIN_CLIMB_M:
            climb_badge = _record_badge(
                "most_climb",
                climb.query(run.ascent_m),
                climb.count,
                run.ascent_m,
                window_start,
                busy_window,
            )
            if climb_badge:
                badges.append(climb_badge)
        first, second = run.first_half_seconds, run.second_half_seconds
        if (
            run.distance_km >= NEGATIVE_SPLIT_MIN_KM
            and first
            and second
            and second < first * (1 - NEGATIVE_SPLIT_MARGIN)
        ):
            badges.append(RunBadge(kind="negative_split", value=round(first - second)))

        # Weekly streak, goal and plan: all keyed off this run's week.
        week_runs[this_week] += 1
        if week_runs[this_week] == STREAK_MIN_RUNS:
            streak = 1
            prior = this_week - timedelta(weeks=1)
            while week_runs[prior] >= STREAK_MIN_RUNS:
                streak += 1
                prior -= timedelta(weeks=1)
            if streak % STREAK_STEP == 0:
                badges.append(RunBadge(kind="weekly_streak", value=streak))
        goal = planned_km_per_week.get(this_week) or weekly_goal_km
        if goal and week_total - run.distance_km < goal <= week_total:
            badges.append(RunBadge(kind="weekly_goal", value=goal))
        planned = planned_per_week[this_week]
        if planned and week_runs[this_week] == planned:
            badges.append(RunBadge(kind="plan_complete", value=planned))

        # Running-total milestones and beating last year's total.
        before_total, total_km = total_km, total_km + run.distance_km
        if int(total_km // DISTANCE_MILESTONE_KM) > int(before_total // DISTANCE_MILESTONE_KM):
            milestone = int(total_km // DISTANCE_MILESTONE_KM) * DISTANCE_MILESTONE_KM
            badges.append(RunBadge(kind="distance_milestone", value=milestone))
        if (i + 1) % RUN_MILESTONE == 0:
            badges.append(RunBadge(kind="run_milestone", value=i + 1))
        last_year = year_km.get(day.year - 1, 0.0)
        before_year = year_km[day.year]
        year_km[day.year] += run.distance_km
        if last_year > 0 and before_year <= last_year < year_km[day.year]:
            badges.append(RunBadge(kind="beat_last_year", value=last_year))

        # Comeback after a break.
        if i > 0:
            gap = (day - ordered[i - 1].day).days
            if gap >= COMEBACK_DAYS:
                badges.append(RunBadge(kind="comeback", value=gap))

        if badges:
            result[run.id] = badges

        longest.add(run.distance_km, run)
        longest_time.add(run.duration_seconds, run)
        if run.ascent_m is not None and run.ascent_m >= MIN_CLIMB_M:
            climb.add(run.ascent_m, run)
        for name, seconds in run.efforts.items():
            fastest[name].add(-seconds, run)

    return result


def _pushed_back[K](
    before: K | None, after: K | None, had_earlier_runs: bool, periods: int
) -> bool:
    """Did this run take the period's "biggest since" further back?

    `before`/`after` are the most recent earlier periods that were at least as
    big as the running total before/after this run. Earlier runs in the same
    period have already been credited with `before`.
    """
    if after is None:
        # Biggest ever: credit the run that first got there, given history.
        if periods < MIN_EARLIER_FOR_EVER:
            return False
        return not had_earlier_runs or before is not None
    if not had_earlier_runs:
        return True
    return before is not None and after != before


def best_efforts(runs: list[RunRecord]) -> list[dict[str, object]]:
    """Fastest effort ever at each standard distance (earliest wins a tie)."""
    best: dict[str, RunRecord] = {}
    for run in sorted(runs, key=lambda r: (r.date, r.start_time or "", r.id)):
        for name, seconds in run.efforts.items():
            current = best.get(name)
            if current is None or seconds < current.efforts[name]:
                best[name] = run
    out: list[dict[str, object]] = []
    for name, lo, _ in SEGMENT_DEFS:
        holder = best.get(name)
        if holder is None:
            continue
        seconds = holder.efforts[name]
        out.append(
            {
                "name": name,
                "distance_km": lo,
                "duration_seconds": seconds,
                "pace": seconds / 60 / lo,
                "run_id": holder.id,
                "date": holder.date,
            }
        )
    return out
