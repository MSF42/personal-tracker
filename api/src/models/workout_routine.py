from pydantic import BaseModel, Field


class WorkoutRoutineInDB(BaseModel):
    id: int
    name: str
    description: str | None = None
    created_at: str
    updated_at: str


class WorkoutRoutineResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    created_at: str
    updated_at: str


class CreateWorkoutRoutineRequest(BaseModel):
    name: str
    description: str | None = None


class UpdateWorkoutRoutineRequest(BaseModel):
    name: str | None = None
    description: str | None = None


def workout_routine_from_db(row: WorkoutRoutineInDB) -> WorkoutRoutineResponse:
    return WorkoutRoutineResponse(**row.model_dump())
