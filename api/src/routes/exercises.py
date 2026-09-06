from aiosqlite import Connection
from fastapi import APIRouter, Depends

from src.db.database import get_db
from src.errors import ConflictError, NotFoundError
from src.models.exercise import CreateExerciseRequest, ExerciseResponse, UpdateExerciseRequest
from src.repositories.exercise_repository import SQLiteExerciseRepository

router = APIRouter(prefix="/api/v1/exercises", tags=["Exercises"])


async def get_exercise_repository(db: Connection = Depends(get_db)) -> SQLiteExerciseRepository:
    return SQLiteExerciseRepository(db)


@router.post("", status_code=201, response_model=ExerciseResponse)
async def create_exercise(
    exercise: CreateExerciseRequest,
    repo: SQLiteExerciseRepository = Depends(get_exercise_repository),
) -> ExerciseResponse:
    try:
        return await repo.create(exercise)
    except ValueError as e:
        raise ConflictError(str(e)) from e


@router.get("", response_model=list[ExerciseResponse])
async def list_exercises(
    repo: SQLiteExerciseRepository = Depends(get_exercise_repository),
) -> list[ExerciseResponse]:
    return await repo.find_all()


@router.get("/{exercise_id}", response_model=ExerciseResponse)
async def get_exercise(
    exercise_id: int, repo: SQLiteExerciseRepository = Depends(get_exercise_repository)
) -> ExerciseResponse:
    exercise = await repo.find_by_id(exercise_id)
    if exercise is None:
        raise NotFoundError("Exercise not found")
    return exercise


@router.put("/{exercise_id}", response_model=ExerciseResponse)
async def update_exercise(
    exercise_id: int,
    exercise: UpdateExerciseRequest,
    repo: SQLiteExerciseRepository = Depends(get_exercise_repository),
) -> ExerciseResponse:
    data = await repo.update(exercise_id, exercise)
    if data is None:
        raise NotFoundError("Exercise not found")
    return data


@router.delete("/{exercise_id}", status_code=204)
async def delete_exercise(
    exercise_id: int, repo: SQLiteExerciseRepository = Depends(get_exercise_repository)
) -> None:
    deleted = await repo.delete(exercise_id)
    if not deleted:
        raise NotFoundError("Exercise not found")
