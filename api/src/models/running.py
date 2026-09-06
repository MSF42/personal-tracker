from pydantic import BaseModel, Field


class RunningActivityInDB(BaseModel):
    id: int
    date: str
    duration_seconds: int
    distance_km: float
    notes: str | None
    has_gpx: int = 0
    title: str | None = None
    source: str = "manual"  # manual | gpx | fit
    start_time: str | None = None
    elapsed_seconds: int | None = None
    is_indoor: int = 0
    avg_hr: int | None = None
    max_hr: int | None = None
    avg_cadence: int | None = None
    max_cadence: int | None = None
    calories: int | None = None
    total_ascent_m: float | None = None
    total_descent_m: float | None = None
    avg_power: int | None = None
    max_power: int | None = None
    avg_temperature_c: float | None = None
    created_at: str
    updated_at: str


class RunningActivityResponse(BaseModel):
    id: int
    date: str
    duration_seconds: int
    distance_km: float
    notes: str | None = None
    has_gpx: bool = False
    title: str | None = None
    source: str = "manual"
    start_time: str | None = None
    elapsed_seconds: int | None = None
    is_indoor: bool = False
    avg_hr: int | None = None
    max_hr: int | None = None
    avg_cadence: int | None = None
    max_cadence: int | None = None
    calories: int | None = None
    total_ascent_m: float | None = None
    total_descent_m: float | None = None
    avg_power: int | None = None
    max_power: int | None = None
    avg_temperature_c: float | None = None
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
    title: str | None = None


class UpdateRunningActivityRequest(BaseModel):
    date: str | None = None
    duration_seconds: int | None = Field(default=None, gt=0)
    distance_km: float | None = Field(default=None, gt=0)
    notes: str | None = None
    title: str | None = None


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
        **{k: v for k, v in row.model_dump().items() if k not in ("has_gpx", "is_indoor")},
        has_gpx=bool(row.has_gpx),
        is_indoor=bool(row.is_indoor),
        pace=round(pace, 2),
        speed=round(speed, 2),
        pace_formatted=pace_formatted,
    )


class GpxSegmentResponse(BaseModel):
    id: int
    segment_name: str
    distance_km: float
    duration_seconds: int
    pace: float
    pace_formatted: str
    start_seconds: float | None = None  # offsets from the run start, when known
    end_seconds: float | None = None


class RunLapResponse(BaseModel):
    id: int
    lap_index: int
    start_time: str | None = None
    timer_seconds: int
    elapsed_seconds: int | None = None
    distance_km: float
    pace: float | None = None
    avg_hr: int | None = None
    max_hr: int | None = None
    avg_cadence: int | None = None
    avg_power: int | None = None
    total_ascent_m: float | None = None
    trigger: str | None = None


class RunSampleResponse(BaseModel):
    t_seconds: float
    distance_km: float | None = None
    heart_rate: int | None = None
    cadence: int | None = None
    speed_mps: float | None = None
    altitude_m: float | None = None
    power: int | None = None
    lat: float | None = None
    lon: float | None = None


class RunImportResponse(BaseModel):
    activity: RunningActivityResponse
    segments: list[GpxSegmentResponse]
    laps: list[RunLapResponse] = []


# Historical name; the GPX endpoint returns the same shape (with no laps).
GpxImportResponse = RunImportResponse
