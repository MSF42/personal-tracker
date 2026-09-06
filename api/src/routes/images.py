import os
import uuid
from pathlib import Path

from fastapi import APIRouter, File, UploadFile

from src.config.settings import get_settings
from src.errors import AppValidationError
from src.models.image import ImageUploadResponse

router = APIRouter(prefix="/api/v1/images", tags=["Images"])

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


@router.post("", status_code=201, response_model=ImageUploadResponse)
async def upload_image(file: UploadFile = File(...)) -> ImageUploadResponse:
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
        raise AppValidationError(f"File content does not match declared type {file.content_type}")

    ext = EXTENSION_MAP.get(file.content_type, ".bin")
    filename = f"{uuid.uuid4()}{ext}"
    settings = get_settings()
    filepath = os.path.join(settings.uploads_path, filename)

    Path(filepath).write_bytes(content)

    return ImageUploadResponse(url=f"/uploads/{filename}", filename=filename)
