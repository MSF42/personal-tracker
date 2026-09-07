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
    completed: bool | None = None


class UpdateSetRequest(BaseModel):
    reps: int | None = None
    weight: float | None = None


class SetLogResponse(BaseModel):
    id: int | None = None
    workout_log_id: int
    exercise_id: int
    set_number: int
    reps: int | None = None
    weight: float | None = None
    created_at: str | None = None
    exercise_name: str | None = None


class SetHistoryEntry(BaseModel):
    set_number: int
    reps: int | None = None
    weight: float | None = None
    workout_log_id: int
    date: str
    routine_name: str | None = None


class WorkoutLogResponse(BaseModel):
    id: int
    routine_id: int
    routine_name: str | None = None
    date: str
    notes: str | None = None
    created_at: str | None = None
    completed: bool
    sets: list[SetLogResponse] = []


class RoutineLogSummaryResponse(BaseModel):
    """One past session against a routine, with aggregates for a history view."""

    id: int
    date: str
    notes: str | None = None
    created_at: str | None = None
    completed: bool
    total_sets: int = 0
    total_volume: float = 0
