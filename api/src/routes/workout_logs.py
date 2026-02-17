from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.db.database import get_db
from src.errors import NotFoundError
from src.repositories.workout_log_repository import SQLiteWorkoutLogRepository


class UpdateWorkoutLogRequest(BaseModel):
    date: str | None = None
    notes: str | None = None


router = APIRouter(prefix="/api/v1/workout-logs", tags=["Workout Logs"])


async def get_workout_log_repository(db=Depends(get_db)):
    return SQLiteWorkoutLogRepository(db)


@router.post("", status_code=201)
async def create_workout_log(
    routine_id: int,
    date: str,
    notes: str | None = None,
    repo: SQLiteWorkoutLogRepository = Depends(get_workout_log_repository),
):
    return await repo.create(routine_id, date, notes)


@router.get("")
async def list_workout_logs(
    repo: SQLiteWorkoutLogRepository = Depends(get_workout_log_repository),
):
    return await repo.find_all()


@router.get("/exercise-last-performed")
async def get_exercise_last_performed(
    repo: SQLiteWorkoutLogRepository = Depends(get_workout_log_repository),
):
    return await repo.get_exercise_last_performed()


@router.get("/exercise/{exercise_id}/history")
async def get_exercise_history(
    exercise_id: int,
    repo: SQLiteWorkoutLogRepository = Depends(get_workout_log_repository),
):
    return await repo.get_exercise_history(exercise_id)


@router.get("/{workout_log_id}")
async def get_workout_log(
    workout_log_id: int,
    repo: SQLiteWorkoutLogRepository = Depends(get_workout_log_repository),
):
    log = await repo.get_workout_with_sets(workout_log_id)
    if log is None:
        raise NotFoundError("Workout log not found")
    return log


@router.post("/{workout_log_id}/sets", status_code=201)
async def log_set(
    workout_log_id: int,
    exercise_id: int,
    set_number: int,
    reps: int,
    weight: float | None = None,
    repo: SQLiteWorkoutLogRepository = Depends(get_workout_log_repository),
):
    return await repo.log_set(workout_log_id, exercise_id, set_number, reps, weight)


@router.put("/{workout_log_id}")
async def update_workout_log(
    workout_log_id: int,
    data: UpdateWorkoutLogRequest,
    repo: SQLiteWorkoutLogRepository = Depends(get_workout_log_repository),
):
    log = await repo.update(workout_log_id, date=data.date, notes=data.notes)
    if log is None:
        raise NotFoundError("Workout log not found")
    return log


@router.delete("/{workout_log_id}", status_code=204)
async def delete_workout_log(
    workout_log_id: int,
    repo: SQLiteWorkoutLogRepository = Depends(get_workout_log_repository),
):
    deleted = await repo.delete(workout_log_id)
    if not deleted:
        raise NotFoundError("Workout log not found")


@router.get("/routine/{routine_id}")
async def get_logs_by_routine(
    routine_id: int,
    repo: SQLiteWorkoutLogRepository = Depends(get_workout_log_repository),
):
    return await repo.find_by_routine(routine_id)
