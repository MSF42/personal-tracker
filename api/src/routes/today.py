from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from src.db.database import get_db
from src.repositories.note_repository import SQLiteNoteRepository
from src.repositories.task_repository import SQLiteTaskRepository

router = APIRouter(prefix="/api/v1/today", tags=["Today"])


async def _get_deps(db=Depends(get_db)):
    return SQLiteTaskRepository(db), SQLiteNoteRepository(db)


@router.get("")
async def get_today(repos: tuple = Depends(_get_deps)):
    task_repo, note_repo = repos
    today = datetime.now(timezone.utc).date().isoformat()

    all_tasks, _ = await task_repo.find_with_filters(completed=False, limit=500, offset=0)
    tasks_due = [
        t for t in all_tasks if t.due_date and t.due_date <= today
    ]
    tasks_overdue = [
        t for t in all_tasks if t.due_date and t.due_date < today
    ]

    notes_due = await note_repo.get_due(today)

    return {
        "date": today,
        "tasks_due": [t.model_dump() for t in tasks_due],
        "tasks_overdue": [t.model_dump() for t in tasks_overdue],
        "notes_due": [n.model_dump() for n in notes_due],
    }
