from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


def _validate_repeat_days(v: list[int] | None) -> list[int] | None:
    if v is None:
        return None
    for day in v:
        if day < 0 or day > 6:
            raise ValueError("repeat_days values must be 0-6 (Mon=0 through Sun=6)")
    return sorted(set(v))


class NoteInDB(BaseModel):
    id: int
    parent_id: int | None
    content: str
    sort_order: int
    collapsed: int  # 0 or 1
    created_at: str
    updated_at: str
    # Added in migration 23
    due_date: str | None = None
    recurrence_type: str | None = None
    recurrence_interval: int | None = None
    repeat_days: str | None = None  # comma-separated string in the DB
    archived: int = 0


class NoteResponse(BaseModel):
    id: int
    parent_id: int | None = None
    content: str
    sort_order: int
    collapsed: bool
    created_at: str
    updated_at: str
    due_date: str | None = None
    recurrence_type: str | None = None
    recurrence_interval: int | None = None
    repeat_days: list[int] | None = None
    archived: bool = False


class NoteTreeNode(NoteResponse):
    children: list[NoteTreeNode] = []


class CreateNoteRequest(BaseModel):
    parent_id: int | None = None
    content: str = ""
    sort_order: int = 0


class UpdateNoteRequest(BaseModel):
    content: str | None = None
    collapsed: bool | None = None
    due_date: str | None = None
    recurrence_type: str | None = None  # 'daily' | 'weekly' | 'monthly' | None
    recurrence_interval: int | None = Field(default=None, ge=1)
    repeat_days: list[int] | None = None
    archived: bool | None = None

    @field_validator("repeat_days")
    @classmethod
    def validate_repeat_days(cls, v: list[int] | None) -> list[int] | None:
        return _validate_repeat_days(v)


class MoveNoteRequest(BaseModel):
    parent_id: int | None = Field(default=None)
    sort_order: int


class ImageUploadResponse(BaseModel):
    url: str
    filename: str


def note_from_db(row: NoteInDB) -> NoteResponse:
    data = row.model_dump()
    data["collapsed"] = bool(data["collapsed"])
    data["archived"] = bool(data.get("archived", 0))
    raw_days = data.get("repeat_days")
    if raw_days:
        try:
            data["repeat_days"] = [int(d) for d in raw_days.split(",") if d != ""]
        except ValueError:
            data["repeat_days"] = None
    else:
        data["repeat_days"] = None
    return NoteResponse(**data)
