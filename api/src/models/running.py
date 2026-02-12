from pydantic import BaseModel, Field


class RunningActivityInDB(BaseModel):
    id: int
    date: str
    duration_seconds: int
    distance_km: float
    notes: str | None
    created_at: str
    updated_at: str


class RunningActivityResponse(BaseModel):
    id: int
    date: str
    duration_seconds: int
    distance_km: float
    notes: str | None = None
    created_at: str
    updated_at: str
    # Computed fields
    pace: float  # minutes per km
    speed: float  # km per hour
    pace_formatted: str  # "5:30" format


class CreateRunningActivityRequest(BaseModel):
    date: str  # ISO 8601 format
    duration_seconds: int = Field(gt=0)
    distance_km: float = Field(gt=0)
    notes: str | None = None


class UpdateRunningActivityRequest(BaseModel):
    date: str | None = None
    duration_seconds: int | None = Field(default=None, gt=0)
    distance_km: float | None = Field(default=None, gt=0)
    notes: str | None = None


def running_from_db(row: RunningActivityInDB) -> RunningActivityResponse:
    # Calculate pace (minutes per km)
    if row.distance_km > 0:
        pace = (row.duration_seconds / 60) / row.distance_km
    else:
        pace = 0.0

        # Calculate speed (km per hour)
    if row.duration_seconds > 0:
        speed = row.distance_km / (row.duration_seconds / 3600)
    else:
        speed = 0.0

        # Format pace as "M:SS"
    pace_minutes = int(pace)
    pace_seconds = int((pace - pace_minutes) * 60)
    pace_formatted = f"{pace_minutes}:{pace_seconds:02d}"

    return RunningActivityResponse(
        **row.model_dump(),
        pace=round(pace, 2),
        speed=round(speed, 2),
        pace_formatted=pace_formatted,
    )
