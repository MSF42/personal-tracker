from __future__ import annotations

from pydantic import BaseModel, Field


class NoteInDB(BaseModel):
    id: int
    parent_id: int | None
    content: str
    sort_order: int
    collapsed: int  # 0 or 1
    created_at: str
    updated_at: str


class NoteResponse(BaseModel):
    id: int
    parent_id: int | None = None
    content: str
    sort_order: int
    collapsed: bool
    created_at: str
    updated_at: str


class NoteTreeNode(NoteResponse):
    children: list[NoteTreeNode] = []


class CreateNoteRequest(BaseModel):
    parent_id: int | None = None
    content: str = ""
    sort_order: int = 0


class UpdateNoteRequest(BaseModel):
    content: str | None = None
    collapsed: bool | None = None


class MoveNoteRequest(BaseModel):
    parent_id: int | None = Field(default=None)
    sort_order: int


class ImageUploadResponse(BaseModel):
    url: str
    filename: str


def note_from_db(row: NoteInDB) -> NoteResponse:
    data = row.model_dump()
    data["collapsed"] = bool(data["collapsed"])
    return NoteResponse(**data)
