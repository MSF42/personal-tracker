from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.db.database import get_db
from src.errors import NotFoundError
from src.models.habit import HabitCreate, HabitResponse, HabitUpdate
from src.repositories.habit_repository import SQLiteHabitRepository

router = APIRouter(prefix="/api/v1/habits", tags=["Habits"])


async def get_habit_repository(db=Depends(get_db)):
    return SQLiteHabitRepository(db)


class ToggleCompletionRequest(BaseModel):
    date: str


@router.get("", response_model=list[HabitResponse])
async def list_habits(
    include_archived: bool = False,
    repo: SQLiteHabitRepository = Depends(get_habit_repository),
):
    return await repo.find_all(include_archived=include_archived)


@router.post("", status_code=201, response_model=HabitResponse)
async def create_habit(
    data: HabitCreate,
    repo: SQLiteHabitRepository = Depends(get_habit_repository),
):
    return await repo.create(data)


@router.get("/completions", response_model=dict[int, list[str]])
async def get_habit_completions(
    days: int = 28,
    repo: SQLiteHabitRepository = Depends(get_habit_repository),
):
    return await repo.get_completions_recent(days)


@router.get("/{habit_id}", response_model=HabitResponse)
async def get_habit(
    habit_id: int,
    repo: SQLiteHabitRepository = Depends(get_habit_repository),
):
    habit = await repo.find_by_id(habit_id)
    if habit is None:
        raise NotFoundError("Habit not found")
    return habit


@router.put("/{habit_id}", response_model=HabitResponse)
async def update_habit(
    habit_id: int,
    data: HabitUpdate,
    repo: SQLiteHabitRepository = Depends(get_habit_repository),
):
    habit = await repo.update(habit_id, data)
    if habit is None:
        raise NotFoundError("Habit not found")
    return habit


@router.delete("/{habit_id}", status_code=204)
async def delete_habit(
    habit_id: int,
    repo: SQLiteHabitRepository = Depends(get_habit_repository),
):
    deleted = await repo.delete(habit_id)
    if not deleted:
        raise NotFoundError("Habit not found")


@router.post("/{habit_id}/complete", response_model=HabitResponse)
async def toggle_completion(
    habit_id: int,
    data: ToggleCompletionRequest,
    repo: SQLiteHabitRepository = Depends(get_habit_repository),
):
    habit = await repo.toggle_completion(habit_id, data.date)
    if habit is None:
        raise NotFoundError("Habit not found")
    return habit
