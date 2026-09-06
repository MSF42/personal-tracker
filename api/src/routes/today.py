from datetime import UTC, datetime
from typing import Any

from aiosqlite import Connection
from fastapi import APIRouter, Depends

from src.db.database import get_db
from src.repositories.task_repository import SQLiteTaskRepository

router = APIRouter(prefix="/api/v1/today", tags=["Today"])


async def get_task_repository(db: Connection = Depends(get_db)) -> SQLiteTaskRepository:
    return SQLiteTaskRepository(db)


@router.get("")
async def get_today(
    task_repo: SQLiteTaskRepository = Depends(get_task_repository),
) -> dict[str, Any]:
    today = datetime.now(UTC).date().isoformat()

    all_tasks, _ = await task_repo.find_with_filters(completed=False, limit=500, offset=0)
    tasks_due = [t for t in all_tasks if t.due_date and t.due_date <= today]
    tasks_overdue = [t for t in all_tasks if t.due_date and t.due_date < today]

    return {
        "date": today,
        "tasks_due": [t.model_dump() for t in tasks_due],
        "tasks_overdue": [t.model_dump() for t in tasks_overdue],
    }
