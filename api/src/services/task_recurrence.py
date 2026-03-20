from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta

from src.models.task import RepeatType


def _next_weekday(from_date: datetime, repeat_days: list[int], interval: int) -> datetime:
    """Find the next date after from_date that falls on one of the repeat_days.

    For interval > 1, skip (interval - 1) weeks first, then find the next matching day.
    """
    if interval > 1:
        # Jump forward (interval - 1) weeks, then find the next matching day
        from_date = from_date + timedelta(weeks=interval - 1)

    # Search up to 7 days ahead to find a matching weekday
    for i in range(1, 8):
        candidate = from_date + timedelta(days=i)
        if candidate.weekday() in repeat_days:
            return candidate

    # Should never reach here if repeat_days is valid
    return from_date + timedelta(weeks=interval)


def calculate_next_due_date(
    current_due: str,
    repeat_type: RepeatType,
    interval: int = 1,
    repeat_days: list[int] | None = None,
) -> str:
    """Calculate the next due date based on recurrence settings.

    Weekday convention: Monday = 0, Sunday = 6 (Python's datetime.weekday()).

    NOTE: The TypeScript local-backend counterpart in
    ui/src/composables/api/backends/local/useTaskApi.ts uses JavaScript's
    Date.getDay() convention (Sunday = 0, Saturday = 6). This means weekly
    tasks with repeat_days will calculate incorrect next due dates in the
    local backend for all days except Saturday. This is a known issue —
    fixing it requires aligning the two weekday conventions.
    """
    due_date = datetime.fromisoformat(current_due.replace("Z", "+00:00"))

    match repeat_type:
        case RepeatType.daily:
            next_date = due_date + timedelta(days=interval)
        case RepeatType.weekly:
            if repeat_days:
                next_date = _next_weekday(due_date, repeat_days, interval)
            else:
                next_date = due_date + timedelta(weeks=interval)
        case RepeatType.monthly:
            next_date = due_date + relativedelta(months=interval)
        case _:
            return current_due

    return next_date.isoformat()
