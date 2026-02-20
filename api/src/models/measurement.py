from pydantic import BaseModel, Field


class MeasurementInDB(BaseModel):
    id: int
    name: str
    unit: str
    sort_order: int
    created_at: str
    updated_at: str


class MeasurementResponse(BaseModel):
    id: int
    name: str
    unit: str
    sort_order: int
    created_at: str
    updated_at: str


class CreateMeasurementRequest(BaseModel):
    name: str = Field(min_length=1)
    unit: str = ""


class UpdateMeasurementRequest(BaseModel):
    name: str | None = None
    unit: str | None = None


class MeasurementEntryInDB(BaseModel):
    id: int
    measurement_id: int
    date: str
    value: float
    notes: str | None
    created_at: str
    updated_at: str


class MeasurementEntryResponse(BaseModel):
    id: int
    measurement_id: int
    date: str
    value: float
    notes: str | None = None
    created_at: str
    updated_at: str


class CreateMeasurementEntryRequest(BaseModel):
    date: str
    value: float
    notes: str | None = None


class UpdateMeasurementEntryRequest(BaseModel):
    date: str | None = None
    value: float | None = None
    notes: str | None = None


def measurement_from_db(row: MeasurementInDB) -> MeasurementResponse:
    return MeasurementResponse(**row.model_dump())


def entry_from_db(row: MeasurementEntryInDB) -> MeasurementEntryResponse:
    return MeasurementEntryResponse(**row.model_dump())
