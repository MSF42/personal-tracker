from pydantic import BaseModel


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
