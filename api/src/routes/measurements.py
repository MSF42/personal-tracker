from fastapi import APIRouter, Depends

from src.db.database import get_db
from src.errors import NotFoundError
from src.models.measurement import (
    CreateMeasurementEntryRequest,
    CreateMeasurementRequest,
    MeasurementEntryResponse,
    MeasurementResponse,
    UpdateMeasurementEntryRequest,
    UpdateMeasurementRequest,
)
from src.repositories.measurement_repository import SQLiteMeasurementRepository

router = APIRouter(prefix="/api/v1/measurements", tags=["Measurements"])


async def get_measurement_repository(db=Depends(get_db)):
    return SQLiteMeasurementRepository(db)


@router.post("", status_code=201, response_model=MeasurementResponse)
async def create_measurement(
    data: CreateMeasurementRequest,
    repo: SQLiteMeasurementRepository = Depends(get_measurement_repository),
):
    return await repo.create_measurement(data)


@router.get("", response_model=list[MeasurementResponse])
async def list_measurements(
    repo: SQLiteMeasurementRepository = Depends(get_measurement_repository),
):
    return await repo.find_all_measurements()


@router.put("/{measurement_id}", response_model=MeasurementResponse)
async def update_measurement(
    measurement_id: int,
    data: UpdateMeasurementRequest,
    repo: SQLiteMeasurementRepository = Depends(get_measurement_repository),
):
    measurement = await repo.update_measurement(measurement_id, data)
    if measurement is None:
        raise NotFoundError("Measurement not found")
    return measurement


@router.delete("/{measurement_id}", status_code=204)
async def delete_measurement(
    measurement_id: int,
    repo: SQLiteMeasurementRepository = Depends(get_measurement_repository),
):
    deleted = await repo.delete_measurement(measurement_id)
    if not deleted:
        raise NotFoundError("Measurement not found")


@router.post("/{measurement_id}/entries", status_code=201, response_model=MeasurementEntryResponse)
async def create_entry(
    measurement_id: int,
    data: CreateMeasurementEntryRequest,
    repo: SQLiteMeasurementRepository = Depends(get_measurement_repository),
):
    measurement = await repo.find_measurement_by_id(measurement_id)
    if measurement is None:
        raise NotFoundError("Measurement not found")
    return await repo.create_entry(measurement_id, data)


@router.get("/{measurement_id}/entries", response_model=list[MeasurementEntryResponse])
async def list_entries(
    measurement_id: int,
    repo: SQLiteMeasurementRepository = Depends(get_measurement_repository),
):
    measurement = await repo.find_measurement_by_id(measurement_id)
    if measurement is None:
        raise NotFoundError("Measurement not found")
    return await repo.find_entries(measurement_id)


@router.put("/entries/{entry_id}", response_model=MeasurementEntryResponse)
async def update_entry(
    entry_id: int,
    data: UpdateMeasurementEntryRequest,
    repo: SQLiteMeasurementRepository = Depends(get_measurement_repository),
):
    entry = await repo.update_entry(entry_id, data)
    if entry is None:
        raise NotFoundError("Measurement entry not found")
    return entry


@router.delete("/entries/{entry_id}", status_code=204)
async def delete_entry(
    entry_id: int,
    repo: SQLiteMeasurementRepository = Depends(get_measurement_repository),
):
    deleted = await repo.delete_entry(entry_id)
    if not deleted:
        raise NotFoundError("Measurement entry not found")
