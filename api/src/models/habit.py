from datetime import date, timedelta

from pydantic import BaseModel


class HabitInDB(BaseModel):
    id: int
    name: str
    description: str | None
    frequency: str
    frequency_days: str | None
    color: str
    archived: int
    created_at: str
    updated_at: str


class HabitResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    frequency: str
    frequency_days: list[int] | None = None
    color: str
    archived: bool
    current_streak: int
    longest_streak: int
    completed_today: bool
    created_at: str
    updated_at: str


class HabitCreate(BaseModel):
    name: str
    description: str | None = None
    frequency: str = "daily"
    frequency_days: list[int] | None = None
    color: str = "#3b82f6"


class HabitUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    frequency: str | None = None
    frequency_days: list[int] | None = None
    color: str | None = None
    archived: bool | None = None


def _calc_current_streak(dates: list[str], today: str) -> int:
    if not dates:
        return 0
    sorted_dates = sorted(dates, reverse=True)
    today_date = date.fromisoformat(today)
    streak = 0
    expected = today_date
    for d in sorted_dates:
        current = date.fromisoformat(d)
        if current == expected:
            streak += 1
            expected = expected - timedelta(days=1)
        elif current == today_date - timedelta(days=1) and streak == 0:
            # Allow streak starting from yesterday
            streak += 1
            expected = current - timedelta(days=1)
        else:
            break
    return streak


def _calc_longest_streak(dates: list[str]) -> int:
    if not dates:
        return 0
    sorted_dates = sorted(set(dates))
    longest = 1
    current = 1
    for i in range(1, len(sorted_dates)):
        prev = date.fromisoformat(sorted_dates[i - 1])
        curr = date.fromisoformat(sorted_dates[i])
        if curr - prev == timedelta(days=1):
            current += 1
            longest = max(longest, current)
        else:
            current = 1
    return longest


def habit_from_db(row: HabitInDB, completions: list[str], today: str) -> HabitResponse:
    frequency_days = None
    if row.frequency_days:
        frequency_days = [int(d) for d in row.frequency_days.split(",")]

    return HabitResponse(
        id=row.id,
        name=row.name,
        description=row.description,
        frequency=row.frequency,
        frequency_days=frequency_days,
        color=row.color,
        archived=bool(row.archived),
        current_streak=_calc_current_streak(completions, today),
        longest_streak=_calc_longest_streak(completions),
        completed_today=today in completions,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
