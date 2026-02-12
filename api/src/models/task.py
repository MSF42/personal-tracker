from enum import Enum

from pydantic import BaseModel, Field


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
    created_at: str
    updated_at: str

# What clients will send to create a task
class CreateTaskRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    category: str | None = None
    due_date: str | None = None  # Expect ISO 8601 string
    completed: bool = False
    repeat_type: RepeatType | None = None
    repeat_interval: int | None = Field(default=None, ge=1)

# What clients will send to update a task
class UpdateTaskRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    category: str | None = None
    due_date: str | None = None
    completed: bool | None = None
    repeat_type: RepeatType | None = None
    repeat_interval: int | None = Field(default=None, ge=1)

# Conversion Helper Function
def task_from_db(row: TaskInDB) -> TaskResponse:
    data = row.model_dump()
    data["completed"] = bool(data["completed"])
    return TaskResponse(**data)

