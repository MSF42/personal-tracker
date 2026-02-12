from fastapi import APIRouter, Depends

from src.db.database import get_db
from src.errors import ConflictError, NotFoundError
from src.models.workout_routine import (
    CreateWorkoutRoutineRequest,
    UpdateWorkoutRoutineRequest,
    WorkoutRoutineResponse,
)
from src.repositories.workout_routine_repository import SQLiteWorkoutRoutineRepository

router = APIRouter(prefix="/api/v1/workout-routines", tags=["Workout Routines"])


async def get_workout_routine_repository(db=Depends(get_db)):
    return SQLiteWorkoutRoutineRepository(db)


@router.post("", status_code=201, response_model=WorkoutRoutineResponse)
async def create_workout_routine(
    workout_routine: CreateWorkoutRoutineRequest,
    repo: SQLiteWorkoutRoutineRepository = Depends(get_workout_routine_repository),
):
    try:
        return await repo.create(workout_routine)
    except ValueError as e:
        raise ConflictError(str(e))


@router.get("", response_model=list[WorkoutRoutineResponse])
async def get_workout_routines(
    repo: SQLiteWorkoutRoutineRepository = Depends(get_workout_routine_repository),
):
    return await repo.find_all()


@router.get("/{workout_routine_id}", response_model=WorkoutRoutineResponse)
async def get_workout_routine(
    workout_routine_id: int,
    repo: SQLiteWorkoutRoutineRepository = Depends(get_workout_routine_repository),
):
    workout_routine = await repo.find_by_id(workout_routine_id)
    if workout_routine is None:
        raise NotFoundError("workout routine not found")
    return workout_routine


@router.put("/{workout_routine_id}", response_model=WorkoutRoutineResponse)
async def update_workout_routine(
    workout_routine_id: int,
    workout_routine: UpdateWorkoutRoutineRequest,
    repo: SQLiteWorkoutRoutineRepository = Depends(get_workout_routine_repository),
):
    data = await repo.update(workout_routine_id, workout_routine)
    if data is None:
        raise NotFoundError("workout routine not found")
    return data


@router.delete("/{workout_routine_id}", status_code=204)
async def delete_workout_routine(
    workout_routine_id: int,
    repo: SQLiteWorkoutRoutineRepository = Depends(get_workout_routine_repository),
):
    deleted = await repo.delete(workout_routine_id)
    if not deleted:
        raise NotFoundError("workout routine not found")
