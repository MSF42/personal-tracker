import hashlib
import xml.etree.ElementTree as ET
from dataclasses import asdict
from typing import Any

from aiosqlite import Connection
from fastapi import APIRouter, Depends, File, Query, UploadFile

from src.db.database import get_db
from src.errors import AppValidationError, ConflictError, NotFoundError
from src.models.running import (
    CreateRunningActivityRequest,
    GpxSegmentResponse,
    RunImportResponse,
    RunLapResponse,
    RunningActivityResponse,
    RunSampleResponse,
    UpdateRunningActivityRequest,
)
from src.repositories.running_repository import SQLiteRunningRepository
from src.services.fit_parser import parse_fit
from src.services.gpx_parser import parse_gpx
from src.services.track_segments import SegmentResult

router = APIRouter(prefix="/api/v1/runs", tags=["Running"])


async def get_running_repository(db: Connection = Depends(get_db)) -> SQLiteRunningRepository:
    return SQLiteRunningRepository(db)


@router.post("", status_code=201, response_model=RunningActivityResponse)
async def create_run(
    activity: CreateRunningActivityRequest,
    repo: SQLiteRunningRepository = Depends(get_running_repository),
) -> RunningActivityResponse:
    return await repo.create(activity)


@router.get("", response_model=list[RunningActivityResponse])
async def list_runs(
    repo: SQLiteRunningRepository = Depends(get_running_repository),
) -> list[RunningActivityResponse]:
    return await repo.find_all()


@router.get("/stats/{year}")
async def get_yearly_stats(
    year: int,
    repo: SQLiteRunningRepository = Depends(get_running_repository),
) -> list[dict[str, Any]]:
    return await repo.get_stats_by_month(year)


@router.get("/personal-bests")
async def get_personal_bests(
    repo: SQLiteRunningRepository = Depends(get_running_repository),
) -> dict[str, Any]:
    return await repo.get_personal_bests()


def _reject_duplicate(duplicate: RunningActivityResponse | None) -> None:
    if duplicate is not None:
        raise ConflictError(
            f"Already imported as run #{duplicate.id} on {duplicate.date}"
            f" ({duplicate.distance_km:.2f} km)"
        )


def _segment_dicts(segments: list[SegmentResult]) -> list[dict[str, object]]:
    return [
        {
            "name": s.name,
            "distance_km": s.distance_km,
            "duration_seconds": s.duration_seconds,
            "pace": s.pace,
            "pace_formatted": s.pace_formatted,
            "start_seconds": s.start_seconds,
            "end_seconds": s.end_seconds,
        }
        for s in segments
    ]


@router.post("/import-gpx", status_code=201, response_model=RunImportResponse)
async def import_gpx(
    file: UploadFile = File(...),
    repo: SQLiteRunningRepository = Depends(get_running_repository),
) -> RunImportResponse:
    if not file.filename or not file.filename.lower().endswith(".gpx"):
        raise AppValidationError("File must have a .gpx extension")

    xml_bytes = await file.read()
    try:
        result = parse_gpx(xml_bytes)
    except ET.ParseError as exc:
        raise AppValidationError("GPX file contains invalid XML") from exc
    except ValueError as exc:
        raise AppValidationError(str(exc)) from exc

    sha256 = hashlib.sha256(xml_bytes).hexdigest()
    _reject_duplicate(
        await repo.find_import_duplicate(
            sha256,
            result.date,
            result.distance_km,
            result.duration_seconds,
            start_time=result.start_time,
        )
    )

    activity = await repo.create_from_import(
        source="gpx",
        import_sha256=sha256,
        date=result.date,
        distance_km=result.distance_km,
        duration_seconds=result.duration_seconds,
        title=result.title,
        start_time=result.start_time,
        elapsed_seconds=result.duration_seconds,
    )
    saved_segments = await repo.save_segments(activity.id, _segment_dicts(result.segments))
    await repo.save_samples(activity.id, [asdict(s) for s in result.samples])
    return RunImportResponse(
        activity=activity,
        segments=[GpxSegmentResponse.model_validate(seg) for seg in saved_segments],
    )


@router.post("/import-fit", status_code=201, response_model=RunImportResponse)
async def import_fit(
    file: UploadFile = File(...),
    repo: SQLiteRunningRepository = Depends(get_running_repository),
) -> RunImportResponse:
    if not file.filename or not file.filename.lower().endswith(".fit"):
        raise AppValidationError("File must have a .fit extension")

    data = await file.read()
    try:
        result = parse_fit(data)
    except ValueError as exc:
        raise AppValidationError(str(exc)) from exc

    sha256 = hashlib.sha256(data).hexdigest()
    _reject_duplicate(
        await repo.find_import_duplicate(
            sha256,
            result.date,
            result.distance_km,
            result.duration_seconds,
            source_uuid=result.source_uuid,
            start_time=result.start_time,
        )
    )

    activity = await repo.create_from_import(
        source="fit",
        import_sha256=sha256,
        date=result.date,
        distance_km=result.distance_km,
        duration_seconds=result.duration_seconds,
        title=result.title,
        start_time=result.start_time,
        source_uuid=result.source_uuid,
        elapsed_seconds=result.elapsed_seconds,
        is_indoor=result.is_indoor,
        metrics={
            "avg_hr": result.avg_hr,
            "max_hr": result.max_hr,
            "avg_cadence": result.avg_cadence,
            "max_cadence": result.max_cadence,
            "calories": result.calories,
            "total_ascent_m": result.total_ascent_m,
            "total_descent_m": result.total_descent_m,
            "avg_power": result.avg_power,
            "max_power": result.max_power,
            "avg_temperature_c": result.avg_temperature_c,
        },
    )
    saved_segments = await repo.save_segments(activity.id, _segment_dicts(result.segments))
    saved_laps = await repo.save_laps(
        activity.id,
        [
            {
                "lap_index": lap.index,
                "start_time": lap.start_time,
                "timer_seconds": lap.timer_seconds,
                "elapsed_seconds": lap.elapsed_seconds,
                "distance_km": lap.distance_km,
                "pace": lap.pace,
                "avg_hr": lap.avg_hr,
                "max_hr": lap.max_hr,
                "avg_cadence": lap.avg_cadence,
                "avg_power": lap.avg_power,
                "total_ascent_m": lap.total_ascent_m,
                "trigger": lap.trigger,
            }
            for lap in result.laps
        ],
    )
    await repo.save_samples(activity.id, [asdict(s) for s in result.samples])

    return RunImportResponse(
        activity=activity,
        segments=[GpxSegmentResponse.model_validate(seg) for seg in saved_segments],
        laps=[RunLapResponse.model_validate(lap) for lap in saved_laps],
    )


@router.get("/{run_id}/laps", response_model=list[RunLapResponse])
async def get_laps(
    run_id: int,
    repo: SQLiteRunningRepository = Depends(get_running_repository),
) -> list[RunLapResponse]:
    if await repo.find_by_id(run_id) is None:
        raise NotFoundError("Running activity not found")
    return [RunLapResponse.model_validate(lap) for lap in await repo.get_laps(run_id)]


@router.get("/{run_id}/samples", response_model=list[RunSampleResponse])
async def get_samples(
    run_id: int,
    max_points: int = Query(600, ge=2, le=20000),
    repo: SQLiteRunningRepository = Depends(get_running_repository),
) -> list[RunSampleResponse]:
    if await repo.find_by_id(run_id) is None:
        raise NotFoundError("Running activity not found")
    return [RunSampleResponse.model_validate(s) for s in await repo.get_samples(run_id, max_points)]


@router.get("/{run_id}/segments", response_model=list[GpxSegmentResponse])
async def get_segments(
    run_id: int,
    repo: SQLiteRunningRepository = Depends(get_running_repository),
) -> list[GpxSegmentResponse]:
    run = await repo.find_by_id(run_id)
    if run is None:
        raise NotFoundError("Running activity not found")
    return [GpxSegmentResponse(**seg) for seg in await repo.get_segments(run_id)]


@router.get("/{run_id}", response_model=RunningActivityResponse)
async def get_run(
    run_id: int,
    repo: SQLiteRunningRepository = Depends(get_running_repository),
) -> RunningActivityResponse:
    run = await repo.find_by_id(run_id)
    if run is None:
        raise NotFoundError("Running activity not found")
    return run


@router.put("/{run_id}", response_model=RunningActivityResponse)
async def update_run(
    run_id: int,
    data: UpdateRunningActivityRequest,
    repo: SQLiteRunningRepository = Depends(get_running_repository),
) -> RunningActivityResponse:
    run = await repo.update(run_id, data)
    if run is None:
        raise NotFoundError("Running activity not found")
    return run


@router.delete("/{run_id}", status_code=204)
async def delete_run(
    run_id: int,
    repo: SQLiteRunningRepository = Depends(get_running_repository),
) -> None:
    deleted = await repo.delete(run_id)
    if not deleted:
        raise NotFoundError("Running activity not found")
