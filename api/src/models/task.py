from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator


# ENUMS
class RepeatType(StrEnum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"


class Priority(StrEnum):
    high = "high"
    medium = "medium"
    low = "low"


class TaskLinkType(StrEnum):
    """What a task represents, so acting on it can jump straight into
    performing/logging that thing instead of just marking it done."""

    workout_routine = "workout_routine"
    run = "run"


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
    priority: str = "medium"
    link_type: str | None = None
    link_routine_id: int | None = None
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
    priority: str = "medium"
    link_type: TaskLinkType | None = None
    link_routine_id: int | None = None
    created_at: str
    updated_at: str


def _validate_repeat_days(v: list[int] | None) -> list[int] | None:
    if v is None:
        return None
    for day in v:
        if day < 0 or day > 6:
            raise ValueError("repeat_days values must be 0-6 (Mon=0 through Sun=6)")
    return sorted(set(v))


def _validate_link(link_type: TaskLinkType | None, link_routine_id: int | None) -> None:
    if link_type == TaskLinkType.workout_routine and link_routine_id is None:
        raise ValueError("link_routine_id is required when link_type is workout_routine")
    if link_type != TaskLinkType.workout_routine and link_routine_id is not None:
        raise ValueError("link_routine_id may only be set when link_type is workout_routine")


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
    priority: Priority = Priority.medium
    link_type: TaskLinkType | None = None
    link_routine_id: int | None = None

    @field_validator("repeat_days")
    @classmethod
    def validate_repeat_days(cls, v: list[int] | None) -> list[int] | None:
        return _validate_repeat_days(v)

    @model_validator(mode="after")
    def validate_link(self) -> "CreateTaskRequest":
        _validate_link(self.link_type, self.link_routine_id)
        return self


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
    priority: Priority | None = None
    link_type: TaskLinkType | None = None
    link_routine_id: int | None = None

    @field_validator("repeat_days")
    @classmethod
    def validate_repeat_days(cls, v: list[int] | None) -> list[int] | None:
        return _validate_repeat_days(v)

    @model_validator(mode="after")
    def validate_link(self) -> "UpdateTaskRequest":
        # Only meaningful when both fields are actually part of this partial
        # update — the app always sends them together (see
        # AddEditTaskDialog.vue), but a request that only ever touches one
        # (e.g. the plain `{completed: true}` completion call) leaves both
        # unset here and this trivially passes.
        if "link_type" in self.model_fields_set or "link_routine_id" in self.model_fields_set:
            _validate_link(self.link_type, self.link_routine_id)
        return self


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
