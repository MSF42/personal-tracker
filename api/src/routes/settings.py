import io
import os
import shutil
import tempfile
import zipfile
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.config.settings import get_settings
from src.db.database import get_db
from src.db.migrations import run_migrations
from src.repositories.settings_repository import SQLiteSettingsRepository

router = APIRouter(prefix="/api/v1/settings", tags=["Settings"])


async def get_settings_repository(db=Depends(get_db)):
    return SQLiteSettingsRepository(db)


class UpdateSettingRequest(BaseModel):
    value: str


@router.get("/{key}")
async def get_setting(
    key: str,
    repo: SQLiteSettingsRepository = Depends(get_settings_repository),
):
    value = await repo.get(key)
    return {"key": key, "value": value}


@router.put("/{key}")
async def update_setting(
    key: str,
    body: UpdateSettingRequest,
    repo: SQLiteSettingsRepository = Depends(get_settings_repository),
):
    await repo.set(key, body.value)
    return {"key": key, "value": body.value}


@router.delete("/{key}")
async def delete_setting(
    key: str,
    repo: SQLiteSettingsRepository = Depends(get_settings_repository),
):
    await repo.delete(key)
    return {"key": key, "value": None}


@router.post("/backup")
async def backup_data():
    settings = get_settings()
    db_path = Path(settings.database_path)
    uploads_path = Path(settings.uploads_path)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        if db_path.exists():
            zf.write(db_path, "tracker.db")
        if uploads_path.exists():
            for root, _dirs, files in os.walk(uploads_path):
                for file in files:
                    file_path = Path(root) / file
                    arcname = "uploads" / file_path.relative_to(uploads_path)
                    zf.write(file_path, str(arcname))

    buffer.seek(0)
    filename = f"personal-tracker-backup-{date.today().isoformat()}.zip"
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/restore")
async def restore_data(file: UploadFile):
    settings = get_settings()
    db_path = Path(settings.database_path)
    uploads_path = Path(settings.uploads_path)

    # Save upload to temp file
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".zip")
    try:
        with os.fdopen(tmp_fd, "wb") as tmp:
            content = await file.read()
            tmp.write(content)

        # Validate zip structure
        with zipfile.ZipFile(tmp_path, "r") as zf:
            names = zf.namelist()
            if "tracker.db" not in names:
                return {"error": "Invalid backup: missing tracker.db", "code": "VALIDATION_ERROR"}

            # Extract tracker.db
            db_path.parent.mkdir(parents=True, exist_ok=True)
            with zf.open("tracker.db") as src, open(db_path, "wb") as dst:
                shutil.copyfileobj(src, dst)

            # Replace uploads directory
            if uploads_path.exists():
                shutil.rmtree(uploads_path)
            uploads_path.mkdir(parents=True, exist_ok=True)

            for name in names:
                if name.startswith("uploads/") and not name.endswith("/"):
                    target = uploads_path / Path(name).relative_to("uploads")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(name) as src, open(target, "wb") as dst:
                        shutil.copyfileobj(src, dst)
    finally:
        os.unlink(tmp_path)

    # Run migrations on restored DB
    await run_migrations(str(db_path))

    return {"message": "Backup restored successfully"}


@router.post("/reset")
async def reset_all_data(
    repo: SQLiteSettingsRepository = Depends(get_settings_repository),
):
    await repo.delete_all_data()
    return {"message": "All data has been deleted"}
