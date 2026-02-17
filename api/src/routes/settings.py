from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.db.database import get_db
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
