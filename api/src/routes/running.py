from fastapi import APIRouter, Depends

from src.db.database import get_db
from src.errors import NotFoundError
from src.models.running import (
    CreateRunningActivityRequest,
    RunningActivityResponse,
    UpdateRunningActivityRequest,
)
from src.repositories.running_repository import SQLiteRunningRepository

router = APIRouter(prefix="/api/v1/runs", tags=["Running"])


async def get_running_repository(db=Depends(get_db)):
    return SQLiteRunningRepository(db)


@router.post("", status_code=201, response_model=RunningActivityResponse)
async def create_run(
    activity: CreateRunningActivityRequest,
    repo: SQLiteRunningRepository = Depends(get_running_repository),
):
    return await repo.create(activity)


@router.get("", response_model=list[RunningActivityResponse])
async def list_runs(
    repo: SQLiteRunningRepository = Depends(get_running_repository),
):
    return await repo.find_all()


@router.get("/stats/{year}")
async def get_yearly_stats(
    year: int,
    repo: SQLiteRunningRepository = Depends(get_running_repository),
):
    return await repo.get_stats_by_month(year)


@router.get("/personal-bests")
async def get_personal_bests(
    repo: SQLiteRunningRepository = Depends(get_running_repository),
):
    return await repo.get_personal_bests()


@router.get("/{run_id}", response_model=RunningActivityResponse)
async def get_run(
    run_id: int,
    repo: SQLiteRunningRepository = Depends(get_running_repository),
):
    run = await repo.find_by_id(run_id)
    if run is None:
        raise NotFoundError("Running activity not found")
    return run


@router.put("/{run_id}", response_model=RunningActivityResponse)
async def update_run(
    run_id: int,
    data: UpdateRunningActivityRequest,
    repo: SQLiteRunningRepository = Depends(get_running_repository),
):
    run = await repo.update(run_id, data)
    if run is None:
        raise NotFoundError("Running activity not found")
    return run


@router.delete("/{run_id}", status_code=204)
async def delete_run(
    run_id: int,
    repo: SQLiteRunningRepository = Depends(get_running_repository),
):
    deleted = await repo.delete(run_id)
    if not deleted:
        raise NotFoundError("Running activity not found")
