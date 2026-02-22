from pydantic import BaseModel


class CreateWorkoutLogRequest(BaseModel):
    routine_id: int
    date: str
    notes: str | None = None


class LogSetRequest(BaseModel):
    exercise_id: int
    set_number: int
    reps: int
    weight: float | None = None


class UpdateWorkoutLogRequest(BaseModel):
    date: str | None = None
    notes: str | None = None
