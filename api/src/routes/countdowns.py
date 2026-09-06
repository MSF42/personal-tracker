from aiosqlite import Connection
from fastapi import APIRouter, Depends

from src.db.database import get_db
from src.errors import NotFoundError
from src.models.countdown import CountdownResponse, CreateCountdownRequest, UpdateCountdownRequest
from src.repositories.countdown_repository import SQLiteCountdownRepository

router = APIRouter(prefix="/api/v1/countdowns", tags=["Countdowns"])


async def get_countdown_repository(db: Connection = Depends(get_db)) -> SQLiteCountdownRepository:
    return SQLiteCountdownRepository(db)


@router.post("", status_code=201, response_model=CountdownResponse)
async def create_countdown(
    data: CreateCountdownRequest,
    repo: SQLiteCountdownRepository = Depends(get_countdown_repository),
) -> CountdownResponse:
    return await repo.create(data)


@router.get("", response_model=list[CountdownResponse])
async def list_countdowns(
    repo: SQLiteCountdownRepository = Depends(get_countdown_repository),
) -> list[CountdownResponse]:
    return await repo.find_all()


@router.put("/{countdown_id}", response_model=CountdownResponse)
async def update_countdown(
    countdown_id: int,
    data: UpdateCountdownRequest,
    repo: SQLiteCountdownRepository = Depends(get_countdown_repository),
) -> CountdownResponse:
    countdown = await repo.update(countdown_id, data)
    if countdown is None:
        raise NotFoundError("Countdown not found")
    return countdown


@router.delete("/{countdown_id}", status_code=204)
async def delete_countdown(
    countdown_id: int,
    repo: SQLiteCountdownRepository = Depends(get_countdown_repository),
) -> None:
    if not await repo.delete(countdown_id):
        raise NotFoundError("Countdown not found")
