"""Unit tests for api/src/services/task_recurrence.py::calculate_next_due_date()."""

from datetime import datetime

from src.models.task import RepeatType
from src.services.task_recurrence import calculate_next_due_date

# ---------------------------------------------------------------------------
# Daily repeat
# ---------------------------------------------------------------------------


def test_daily_advances_by_one_day():
    result = calculate_next_due_date("2024-03-01T10:00:00Z", RepeatType.daily, interval=1)
    dt = datetime.fromisoformat(result)
    assert dt.date() == datetime(2024, 3, 2).date()


def test_daily_advances_by_interval_days():
    result = calculate_next_due_date("2024-03-01T10:00:00Z", RepeatType.daily, interval=3)
    dt = datetime.fromisoformat(result)
    assert dt.date() == datetime(2024, 3, 4).date()


def test_daily_preserves_time():
    result = calculate_next_due_date("2024-03-01T15:30:00Z", RepeatType.daily, interval=1)
    dt = datetime.fromisoformat(result)
    assert dt.hour == 15
    assert dt.minute == 30


def test_daily_crosses_month_boundary():
    result = calculate_next_due_date("2024-01-31T10:00:00Z", RepeatType.daily, interval=1)
    dt = datetime.fromisoformat(result)
    assert dt.date() == datetime(2024, 2, 1).date()


# ---------------------------------------------------------------------------
# Weekly repeat — no repeat_days (plain weekly advance)
# ---------------------------------------------------------------------------


def test_weekly_no_repeat_days_advances_one_week():
    result = calculate_next_due_date("2024-03-01T10:00:00Z", RepeatType.weekly, interval=1)
    dt = datetime.fromisoformat(result)
    assert dt.date() == datetime(2024, 3, 8).date()


def test_weekly_interval_two_advances_two_weeks():
    result = calculate_next_due_date("2024-03-01T10:00:00Z", RepeatType.weekly, interval=2)
    dt = datetime.fromisoformat(result)
    assert dt.date() == datetime(2024, 3, 15).date()


def test_weekly_empty_repeat_days_falls_back_to_weekly_advance():
    """Empty list is falsy — should follow the plain weekly branch."""
    result_no_days = calculate_next_due_date(
        "2024-03-01T10:00:00Z", RepeatType.weekly, interval=1, repeat_days=[]
    )
    result_none = calculate_next_due_date(
        "2024-03-01T10:00:00Z", RepeatType.weekly, interval=1, repeat_days=None
    )
    assert result_no_days == result_none


# ---------------------------------------------------------------------------
# Weekly repeat — with specific weekdays
# ---------------------------------------------------------------------------


def test_weekly_repeat_days_finds_next_matching_day():
    # 2024-03-01 is a Friday (weekday=4). Ask for Monday (0) and Wednesday (2).
    # Next Monday is 2024-03-04.
    result = calculate_next_due_date(
        "2024-03-01T10:00:00Z",
        RepeatType.weekly,
        interval=1,
        repeat_days=[0, 2],  # Monday=0, Wednesday=2
    )
    dt = datetime.fromisoformat(result)
    assert dt.weekday() in (0, 2), f"Expected Mon or Wed, got weekday {dt.weekday()}"
    assert dt.date() == datetime(2024, 3, 4).date()  # nearest match is Monday 4 Mar


def test_weekly_repeat_days_skips_same_day():
    # 2024-03-04 is a Monday (weekday=0). repeat_days=[0] — next Monday is 11 Mar.
    result = calculate_next_due_date(
        "2024-03-04T10:00:00Z",
        RepeatType.weekly,
        interval=1,
        repeat_days=[0],
    )
    dt = datetime.fromisoformat(result)
    assert dt.date() == datetime(2024, 3, 11).date()


def test_weekly_every_two_weeks_with_repeat_days():
    # 2024-03-01 is a Friday (weekday=4). interval=2, repeat_days=[4] (Friday).
    # Jump (2-1)=1 week to 2024-03-08 (also Friday), then scan next 7 days:
    # 2024-03-09 Sat, 2024-03-10 Sun, 2024-03-11 Mon, 2024-03-12 Tue, 2024-03-13 Wed,
    # 2024-03-14 Thu, 2024-03-15 Fri (weekday=4) ← first match.
    result = calculate_next_due_date(
        "2024-03-01T10:00:00Z",
        RepeatType.weekly,
        interval=2,
        repeat_days=[4],  # Friday
    )
    dt = datetime.fromisoformat(result)
    assert dt.weekday() == 4  # still lands on a Friday
    assert dt.date() == datetime(2024, 3, 15).date()


# ---------------------------------------------------------------------------
# Monthly repeat
# ---------------------------------------------------------------------------


def test_monthly_advances_by_one_month():
    result = calculate_next_due_date("2024-03-15T10:00:00Z", RepeatType.monthly, interval=1)
    dt = datetime.fromisoformat(result)
    assert dt.date() == datetime(2024, 4, 15).date()


def test_monthly_advances_by_interval_months():
    result = calculate_next_due_date("2024-01-15T10:00:00Z", RepeatType.monthly, interval=3)
    dt = datetime.fromisoformat(result)
    assert dt.date() == datetime(2024, 4, 15).date()


def test_monthly_end_of_month_clamps_to_last_day():
    # Jan 31 + 1 month — Feb has no 31st; dateutil clamps to Feb 29 (2024 is leap year).
    result = calculate_next_due_date("2024-01-31T10:00:00Z", RepeatType.monthly, interval=1)
    dt = datetime.fromisoformat(result)
    assert dt.date() == datetime(2024, 2, 29).date()


def test_monthly_end_of_month_non_leap_year():
    # Jan 31, 2023 + 1 month → Feb 28, 2023 (non-leap).
    result = calculate_next_due_date("2023-01-31T10:00:00Z", RepeatType.monthly, interval=1)
    dt = datetime.fromisoformat(result)
    assert dt.date() == datetime(2023, 2, 28).date()


def test_monthly_crosses_year_boundary():
    result = calculate_next_due_date("2024-12-15T10:00:00Z", RepeatType.monthly, interval=1)
    dt = datetime.fromisoformat(result)
    assert dt.date() == datetime(2025, 1, 15).date()


# ---------------------------------------------------------------------------
# Unknown / unsupported repeat type falls back
# ---------------------------------------------------------------------------


def test_unknown_repeat_type_returns_original():
    # Pass a raw string that doesn't match any RepeatType — the match default branch
    # returns current_due unchanged.  We bypass enum validation intentionally.
    current = "2024-03-01T10:00:00+00:00"
    result = calculate_next_due_date(current, "unknown_type", interval=1)  # type: ignore[arg-type]
    assert result == current
