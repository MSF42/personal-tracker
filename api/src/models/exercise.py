from enum import Enum

from pydantic import BaseModel, Field


class MuscleGroup(str, Enum):
    back = "back"
    chest = "chest"
    biceps = "biceps"
    triceps = "triceps"
    shoulders = "shoulders"
    legs = "legs"


class ExerciseResponse(BaseModel):
    id: int
    name: str
    description: str | None
    muscle_group: MuscleGroup
    equipment: str | None
    instructions: str | None
    created_at: str
    updated_at: str


class CreateExerciseRequest(BaseModel):
    name: str = Field(min_length=3, max_length=50)
    description: str | None = None
    muscle_group: MuscleGroup
    equipment: str | None = None
    instructions: str | None = None


class UpdateExerciseRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    muscle_group: MuscleGroup | None = None
    equipment: str | None = None
    instructions: str | None = None
