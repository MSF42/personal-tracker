import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Query, UploadFile

from src.config.settings import get_settings
from src.db.database import get_db
from src.errors import AppValidationError, NotFoundError
from src.models.note import (
    CreateNoteRequest,
    ImageUploadResponse,
    MoveNoteRequest,
    NoteResponse,
    NoteTreeNode,
    UpdateNoteRequest,
)
from src.repositories.note_repository import SQLiteNoteRepository

router = APIRouter(prefix="/api/v1/notes", tags=["Notes"])


async def get_note_repository(db=Depends(get_db)):
    return SQLiteNoteRepository(db)


@router.get("", response_model=list[NoteTreeNode])
async def get_notes(
    repo: SQLiteNoteRepository = Depends(get_note_repository),
):
    return await repo.get_tree()


@router.post("", status_code=201, response_model=NoteResponse)
async def create_note(
    data: CreateNoteRequest,
    repo: SQLiteNoteRepository = Depends(get_note_repository),
):
    return await repo.create(data)


@router.get("/search", response_model=list[NoteResponse])
async def search_notes(
    q: str = Query(min_length=1, max_length=200),
    repo: SQLiteNoteRepository = Depends(get_note_repository),
):
    return await repo.search(q)


@router.put("/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: int,
    data: UpdateNoteRequest,
    repo: SQLiteNoteRepository = Depends(get_note_repository),
):
    note = await repo.update(note_id, data)
    if note is None:
        raise NotFoundError("Note not found")
    return note


@router.put("/{note_id}/move", response_model=NoteResponse)
async def move_note(
    note_id: int,
    data: MoveNoteRequest,
    repo: SQLiteNoteRepository = Depends(get_note_repository),
):
    note = await repo.move(note_id, data)
    if note is None:
        raise NotFoundError("Note not found")
    return note


@router.delete("/{note_id}", status_code=204)
async def delete_note(
    note_id: int,
    repo: SQLiteNoteRepository = Depends(get_note_repository),
):
    deleted = await repo.delete(note_id)
    if not deleted:
        raise NotFoundError("Note not found")


ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB

EXTENSION_MAP = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}

# Magic byte signatures per content type (content_type can be spoofed; this is a second layer)
_MAGIC_BYTES: dict[str, list[bytes]] = {
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/gif": [b"GIF87a", b"GIF89a"],
    "image/webp": [],  # checked separately via RIFF header
}


def _validate_magic_bytes(content: bytes, content_type: str) -> bool:
    if content_type == "image/webp":
        return len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP"
    signatures = _MAGIC_BYTES.get(content_type, [])
    if not signatures:
        return False
    return any(content[: len(sig)] == sig for sig in signatures)


@router.post("/images", status_code=201, response_model=ImageUploadResponse)
async def upload_image(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise AppValidationError(
            f"Invalid image type: {file.content_type}. "
            f"Allowed: {', '.join(sorted(ALLOWED_IMAGE_TYPES))}"
        )

    content = await file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise AppValidationError(
            f"File too large. Maximum size is {MAX_IMAGE_SIZE // (1024 * 1024)}MB"
        )

    # Second layer: magic-byte check (content_type is client-supplied and can be spoofed)
    if not _validate_magic_bytes(content, file.content_type):
        raise AppValidationError(
            f"File content does not match declared type {file.content_type}"
        )

    ext = EXTENSION_MAP.get(file.content_type, ".bin")
    filename = f"{uuid.uuid4()}{ext}"
    settings = get_settings()
    filepath = os.path.join(settings.uploads_path, filename)

    Path(filepath).write_bytes(content)

    return ImageUploadResponse(url=f"/uploads/{filename}", filename=filename)
