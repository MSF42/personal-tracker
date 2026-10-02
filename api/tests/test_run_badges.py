"""Unit tests for src/services/run_badges.py."""

from datetime import date, timedelta

import pytest

from src.models.running import RunBadge
from src.services.run_badges import (
    RecordBook,
    RunRecord,
    best_efforts,
    compute_badges,
    efforts_for,
    planned_distance_km,
)
from src.services.track_segments import half_splits

START = date(2026, 1, 5)  # a Monday


def run(
    id: int,
    day: int,
    km: float,
    seconds: int | None = None,
    efforts: dict[str, int] | None = None,
) -> RunRecord:
    """Run `id` on START + `day` days; defaults to 6:00/km."""
    duration = seconds if seconds is not None else round(km * 360)
    return RunRecord(
        id=id,
        date=(START + timedelta(days=day)).isoformat(),
        distance_km=km,
        duration_seconds=duration,
        efforts=efforts if efforts is not None else efforts_for(km, duration, {}),
    )


def kinds(badges: list[RunBadge]) -> list[str]:
    return [b.kind for b in badges]


def find(badges: list[RunBadge], kind: str) -> RunBadge | None:
    return next((b for b in badges if b.kind == kind), None)


def test_record_book_returns_most_recent_at_least_as_good() -> None:
    book = RecordBook[str]()
    for value, key in [(5, "a"), (3, "b"), (4, "c"), (2, "d")]:
        book.add(value, key)
    assert book.query(4) == "c"  # c (4) is newer than a (5)
    assert book.query(4.5) == "a"
    assert book.query(1) == "d"
    assert book.query(6) is None
    assert book.count == 4


def test_longest_since_needs_previous_record_outside_window_and_busy_window() -> None:
    runs = [
        run(1, 0, 10.0),
        *[run(10 + i, 40 + i, 3.0) for i in range(3)],  # three short runs, days 40-42
        run(2, 43, 8.0),  # longest in 30 days; last >= 8 km was run 1 on day 0
    ]
    badge = find(compute_badges(runs).get(2, []), "longest")
    assert badge is not None
    assert badge.since == START.isoformat()
    assert not badge.ever


def test_no_since_badge_with_fewer_than_three_runs_in_window() -> None:
    runs = [run(1, 0, 10.0), run(2, 1, 3.0), run(3, 2, 3.0), run(4, 3, 3.0), run(5, 60, 6.0)]
    # Run 5 is the only run in its 30-day window.
    assert find(compute_badges(runs).get(5, []), "longest") is None


def test_longest_ever_needs_some_history_first() -> None:
    runs = [run(1, 0, 3.0), run(2, 1, 4.0), run(3, 2, 5.0), run(4, 3, 6.0)]
    badges = compute_badges(runs)
    assert find(badges.get(3, []), "longest") is None  # only 2 earlier runs
    assert find(badges.get(4, []), "longest") == RunBadge(kind="longest", ever=True, value=6.0)


def test_a_tie_does_not_count_as_a_new_record() -> None:
    runs = [run(1, 0, 3.0), run(2, 1, 3.0), run(3, 2, 3.0), run(4, 3, 5.0), run(5, 4, 5.0)]
    assert find(compute_badges(runs).get(5, []), "longest") is None


def test_time_on_feet_badge_only_without_a_distance_badge() -> None:
    runs = [
        run(1, 0, 10.0, 3600),
        run(2, 1, 3.0),
        run(3, 2, 3.0),
        run(4, 3, 3.0),
        run(5, 4, 9.0, 4000),  # shorter than run 1, but longer in time
    ]
    badges = compute_badges(runs)[5]
    assert find(badges, "longest") is None
    assert find(badges, "longest_time") == RunBadge(kind="longest_time", ever=True, value=4000)


def test_fastest_uses_efforts_inside_longer_runs_and_keeps_the_largest() -> None:
    history = [run(i, i, 5.0, 1800, efforts={"1K": 330, "5K": 1800}) for i in range(1, 4)]
    # A 10 km run whose best 5 km stretch and best 1 km both beat history.
    ten_k = run(9, 5, 10.0, 3500, efforts={"1K": 300, "5K": 1700, "10K": 3500})
    fastest = [b for b in compute_badges([*history, ten_k])[9] if b.kind == "fastest"]
    # 10K has no history yet (no "ever" without 3 earlier efforts), so the
    # largest distance that earns a badge is 5K — and only one is shown.
    assert fastest == [RunBadge(kind="fastest", ever=True, effort="5K", value=1700)]


def test_untracked_run_is_an_effort_only_inside_a_distance_band() -> None:
    assert efforts_for(5.05, 1500, {}) == {"5K": 1500}
    assert efforts_for(5.6, 1700, {}) == {}
    assert efforts_for(42.2, 17937, {}) == {"Marathon": 17937}
    assert efforts_for(10.0, 3000, {"5K": 1400}) == {"5K": 1400}  # track wins


def test_first_distance_reports_the_largest_and_the_previous_date() -> None:
    runs = [run(1, 0, 21.2), run(2, 40, 5.0), run(3, 41, 5.0), run(4, 42, 22.0)]
    badge = find(compute_badges(runs)[4], "first_distance")
    assert badge == RunBadge(kind="first_distance", effort="Half Marathon", since=START.isoformat())
    first_ever = find(compute_badges([run(1, 0, 10.1)])[1], "first_distance")
    assert first_ever == RunBadge(kind="first_distance", effort="10K", ever=True)


def test_biggest_week_credits_the_run_that_pushes_it_back() -> None:
    runs = [
        run(1, 0, 20.0),  # week 0: 20 km
        *[run(10 + w, 7 * w, 5.0) for w in range(1, 6)],  # weeks 1-5: 5 km each
        run(2, 42, 15.0),  # week 6: 15 km — biggest since week 0
        run(3, 43, 10.0),  # week 6: 25 km — biggest ever
    ]
    badges = compute_badges(runs)
    assert find(badges[2], "biggest_week") == RunBadge(
        kind="biggest_week", since=START.isoformat(), value=15.0
    )
    assert find(badges[3], "biggest_week") == RunBadge(kind="biggest_week", ever=True, value=25.0)


def test_biggest_week_must_beat_the_last_four_weeks() -> None:
    runs = [run(1, 0, 20.0), run(2, 7, 5.0), run(3, 14, 10.0)]
    # Week 2 beats week 1, but the last bigger week (week 0) is too recent.
    assert find(compute_badges(runs).get(3, []), "biggest_week") is None


def test_no_biggest_week_or_month_for_the_first_run_after_a_break() -> None:
    runs = [
        *[run(i, i * 2, 5.0) for i in range(1, 30)],  # ~2 months of runs
        run(99, 250, 0.5),  # first run in ~6 months
    ]
    badges = compute_badges(runs)[99]
    assert find(badges, "biggest_week") is None
    assert find(badges, "biggest_month") is None
    assert find(badges, "comeback") is not None


def test_biggest_month_since() -> None:
    runs = [
        run(1, 0, 50.0),  # Jan 2026: 50 km
        run(2, 31, 10.0),  # Feb
        run(3, 60, 10.0),  # Mar
        run(4, 91, 10.0),  # Apr
        run(5, 117, 10.0),  # May, with Apr's run making a busy window:
        run(6, 119, 10.0),  # 20 km beats every month since January
        run(7, 121, 10.0),  # 30 km, but still not past January
    ]
    badges = compute_badges(runs)
    assert find(badges[6], "biggest_month") == RunBadge(
        kind="biggest_month", since="2026-01-01", value=20.0
    )
    assert find(badges.get(7, []), "biggest_month") is None


def test_comeback_after_two_weeks_off() -> None:
    badges = compute_badges([run(1, 0, 5.0), run(2, 13, 5.0), run(3, 30, 5.0)])
    assert find(badges.get(2, []), "comeback") is None
    assert find(badges[3], "comeback") == RunBadge(kind="comeback", value=17)


def test_badges_only_look_backwards() -> None:
    early = [run(1, 0, 3.0), run(2, 1, 3.0), run(3, 2, 3.0), run(4, 3, 8.0)]
    before = compute_badges(early)[4]
    after = compute_badges([*early, run(5, 4, 20.0)])[4]
    assert before == after


def test_best_efforts_picks_fastest_and_earliest_on_tie() -> None:
    runs = [
        run(1, 0, 5.0, efforts={"5K": 1500}),
        run(2, 1, 10.0, efforts={"5K": 1400, "10K": 3000}),
        run(3, 2, 5.0, efforts={"5K": 1400}),
    ]
    by_name = {e["name"]: e for e in best_efforts(runs)}
    assert by_name["5K"]["run_id"] == 2
    assert by_name["10K"]["duration_seconds"] == 3000
    assert list(by_name) == ["5K", "10K"]  # standard-distance order


# --- Phase 2 -----------------------------------------------------------------


def test_most_climb_only_counts_recorded_ascent() -> None:
    runs = [run(i, i, 5.0) for i in range(1, 4)]
    for r, ascent in zip(runs, (40.0, 30.0, 50.0), strict=True):
        r.ascent_m = ascent
    hilly = run(9, 10, 5.0)
    hilly.ascent_m = 80.0
    no_data = run(10, 11, 5.0)  # untracked: no climb badge either way
    badges = compute_badges([*runs, hilly, no_data])
    assert find(badges[9], "most_climb") == RunBadge(kind="most_climb", ever=True, value=80.0)
    assert find(badges.get(10, []), "most_climb") is None


def test_negative_split_needs_a_faster_second_half_over_ten_km() -> None:
    fast_finish = run(1, 0, 10.0)
    fast_finish.first_half_seconds, fast_finish.second_half_seconds = 1800.0, 1770.0
    even = run(2, 1, 10.0)
    even.first_half_seconds, even.second_half_seconds = 1800.0, 1790.0  # < 1% faster
    short = run(3, 2, 9.9)
    short.first_half_seconds, short.second_half_seconds = 1800.0, 1700.0
    badges = compute_badges([fast_finish, even, short])
    assert find(badges[1], "negative_split") == RunBadge(kind="negative_split", value=30)
    assert find(badges.get(2, []), "negative_split") is None
    assert find(badges.get(3, []), "negative_split") is None


def test_weekly_streak_every_four_weeks_of_three_runs() -> None:
    runs = [run(w * 10 + d, w * 7 + d, 3.0) for w in range(8) for d in range(3)]
    badges = compute_badges(runs)
    streaks = {
        rid: find(b, "weekly_streak") for rid, b in badges.items() if find(b, "weekly_streak")
    }
    # The 3rd run of week 4 (id 32) and week 8 (id 72) — streaks of 4 and 8.
    assert streaks == {
        32: RunBadge(kind="weekly_streak", value=4),
        72: RunBadge(kind="weekly_streak", value=8),
    }


def test_weekly_goal_is_credited_to_the_run_that_crosses_it() -> None:
    runs = [run(1, 0, 8.0), run(2, 1, 8.0), run(3, 2, 8.0)]
    badges = compute_badges(runs, weekly_goal_km=15.0)
    assert find(badges.get(1, []), "weekly_goal") is None
    assert find(badges[2], "weekly_goal") == RunBadge(kind="weekly_goal", value=15.0)
    assert find(badges.get(3, []), "weekly_goal") is None


def test_weekly_goal_comes_from_the_plan_when_the_week_has_one() -> None:
    planned = [((START + timedelta(days=d)).isoformat(), "Run 5.0 km") for d in (0, 2)]
    runs = [run(1, 0, 6.0), run(2, 2, 6.0), run(3, 8, 6.0), run(4, 9, 6.0)]
    # Week 1 plans 10 km, which replaces the 12 km manual goal; week 2 has no plan.
    badges = compute_badges(runs, planned_runs=planned, weekly_goal_km=12.0)
    assert find(badges[2], "weekly_goal") == RunBadge(kind="weekly_goal", value=10.0)
    assert find(badges[4], "weekly_goal") == RunBadge(kind="weekly_goal", value=12.0)


def test_planned_distance_reads_the_last_km_in_the_title() -> None:
    assert planned_distance_km("Run 2.0 km") == 2.0
    assert planned_distance_km("Race: Fall Creek Falls Half (21.1 km)") == 21.1
    assert planned_distance_km("Rest") is None


def test_plan_complete_when_the_week_has_as_many_runs_as_planned() -> None:
    planned = [(START + timedelta(days=d)).isoformat() for d in (0, 2, 4)]
    runs = [run(1, 0, 3.0), run(2, 1, 3.0), run(3, 3, 3.0), run(4, 5, 3.0)]
    badges = compute_badges(runs, planned_runs=[(d, "Run 3.0 km") for d in planned])
    assert find(badges[3], "plan_complete") == RunBadge(kind="plan_complete", value=3)
    assert find(badges.get(4, []), "plan_complete") is None


def test_running_total_milestones() -> None:
    runs = [run(i, i, 6.0) for i in range(1, 101)]  # 600 km over 100 runs
    badges = compute_badges(runs)
    km = {rid for rid, b in badges.items() if find(b, "distance_milestone")}
    assert km == {84}  # 84 x 6 = 504 km crosses 500
    assert find(badges[100], "run_milestone") == RunBadge(kind="run_milestone", value=100)


def test_beat_last_year() -> None:
    last_year = [run(1, -300, 10.0), run(2, -200, 10.0)]  # 2025: 20 km
    this_year = [run(3, 0, 12.0), run(4, 5, 9.0), run(5, 9, 5.0)]
    badges = compute_badges([*last_year, *this_year])
    assert find(badges[4], "beat_last_year") == RunBadge(kind="beat_last_year", value=20.0)
    assert find(badges.get(5, []), "beat_last_year") is None


def test_half_splits_skip_pauses_and_interpolate_halfway() -> None:
    # 2 km: first km in 100 s, a 40 s stop (no distance), second km in 90 s.
    dist = [0.0, 0.5, 1.0, 1.0, 1.5, 2.0]
    time = [0.0, 50.0, 100.0, 140.0, 185.0, 230.0]
    assert half_splits(dist, time) == (100.0, 90.0)
    # The halfway point falls mid-interval.
    # Halfway (0.3 km) is 3/4 through the first 40 s interval: 30 s + (10 + 10) s.
    assert half_splits([0.0, 0.4, 0.6], [0.0, 40.0, 50.0]) == pytest.approx((30.0, 20.0))
    # A gap over a minute is a pause, not running.
    assert half_splits([0.0, 1.0, 2.0], [0.0, 30.0, 400.0]) is None
    assert half_splits([0.0], [0.0]) is None
