from enum import Enum

from pydantic import BaseModel, Field, field_validator


# ENUMS
class RepeatType(str, Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"


# What the database will store
class TaskInDB(BaseModel):
    id: int
    title: str
    description: str | None
    category: str | None
    due_date: str | None
    completed: int  # 0 or 1 in the database
    repeat_type: str | None
    repeat_interval: int | None
    repeat_days: str | None = None
    created_at: str
    updated_at: str


# What the API will return
class TaskResponse(BaseModel):
    id: int
    title: str
    description: str | None = None
    category: str | None = None
    due_date: str | None = None
    completed: bool  # Boolean for API consumers
    repeat_type: str | None = None
    repeat_interval: int | None = None
    repeat_days: list[int] | None = None
    created_at: str
    updated_at: str


def _validate_repeat_days(v: list[int] | None) -> list[int] | None:
    if v is None:
        return None
    for day in v:
        if day < 0 or day > 6:
            raise ValueError("repeat_days values must be 0-6 (Mon=0 through Sun=6)")
    return sorted(set(v))


# What clients will send to create a task
class CreateTaskRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    category: str | None = None
    due_date: str | None = None  # Expect ISO 8601 string
    completed: bool = False
    repeat_type: RepeatType | None = None
    repeat_interval: int | None = Field(default=None, ge=1)
    repeat_days: list[int] | None = None

    @field_validator("repeat_days")
    @classmethod
    def validate_repeat_days(cls, v: list[int] | None) -> list[int] | None:
        return _validate_repeat_days(v)


# What clients will send to update a task
class UpdateTaskRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    category: str | None = None
    due_date: str | None = None
    completed: bool | None = None
    repeat_type: RepeatType | None = None
    repeat_interval: int | None = Field(default=None, ge=1)
    repeat_days: list[int] | None = None

    @field_validator("repeat_days")
    @classmethod
    def validate_repeat_days(cls, v: list[int] | None) -> list[int] | None:
        return _validate_repeat_days(v)


# Conversion Helper Function
def task_from_db(row: TaskInDB) -> TaskResponse:
    data = row.model_dump()
    data["completed"] = bool(data["completed"])
    # Parse comma-separated repeat_days string to list of ints
    if data["repeat_days"]:
        data["repeat_days"] = [int(d) for d in data["repeat_days"].split(",")]
    else:
        data["repeat_days"] = None
    return TaskResponse(**data)
