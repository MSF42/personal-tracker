from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta

from src.models.task import RepeatType


def calculate_next_due_date(
    current_due: str,
    repeat_type: RepeatType,
    interval: int = 1,
) -> str:
    """Calculate the next due date based on recurrence settings."""
    due_date = datetime.fromisoformat(current_due.replace("Z", "+00:00"))

    match repeat_type:
        case RepeatType.daily:
            next_date = due_date + timedelta(days=interval)
        case RepeatType.weekly:
            next_date = due_date + timedelta(weeks=interval)
        case RepeatType.monthly:
            next_date = due_date + relativedelta(months=interval)
        case _:
            return current_due

    return next_date.isoformat()
