import xml.etree.ElementTree as ET

from fastapi import APIRouter, Depends, File, UploadFile

from src.db.database import get_db
from src.errors import AppValidationError, NotFoundError
from src.models.running import (
    CreateRunningActivityRequest,
    GpxImportResponse,
    GpxSegmentResponse,
    RunningActivityResponse,
    UpdateRunningActivityRequest,
)
from src.repositories.running_repository import SQLiteRunningRepository
from src.services.gpx_parser import parse_gpx

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


@router.post("/import-gpx", status_code=201, response_model=GpxImportResponse)
async def import_gpx(
    file: UploadFile = File(...),
    repo: SQLiteRunningRepository = Depends(get_running_repository),
):
    if not file.filename or not file.filename.lower().endswith(".gpx"):
        raise AppValidationError("File must have a .gpx extension")

    xml_bytes = await file.read()
    try:
        result = parse_gpx(xml_bytes)
    except ET.ParseError:
        raise AppValidationError("GPX file contains invalid XML")
    except ValueError as exc:
        raise AppValidationError(str(exc))

    activity = await repo.create_with_gpx(
        date=result.date,
        distance_km=result.distance_km,
        duration_seconds=result.duration_seconds,
        notes=None,
        title=result.title,
    )

    segment_dicts = [
        {
            "name": s.name,
            "distance_km": s.distance_km,
            "duration_seconds": s.duration_seconds,
            "pace": s.pace,
            "pace_formatted": s.pace_formatted,
        }
        for s in result.segments
    ]
    saved_segments = await repo.save_segments(activity.id, segment_dicts)

    return GpxImportResponse(
        activity=activity,
        segments=[GpxSegmentResponse(**seg) for seg in saved_segments],
    )


@router.get("/{run_id}/segments", response_model=list[GpxSegmentResponse])
async def get_segments(
    run_id: int,
    repo: SQLiteRunningRepository = Depends(get_running_repository),
):
    run = await repo.find_by_id(run_id)
    if run is None:
        raise NotFoundError("Running activity not found")
    return [GpxSegmentResponse(**seg) for seg in await repo.get_segments(run_id)]


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
