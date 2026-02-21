from pydantic import BaseModel, Field


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
