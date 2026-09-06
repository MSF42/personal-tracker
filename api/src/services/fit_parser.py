"""Parse a Garmin FIT activity file (as exported by HealthFit, Garmin, Coros…).

Everything the app keeps from a FIT file comes out of here: the session summary,
the watch's laps, the per-second record stream, and best-effort segments computed
from that stream with the same algorithm the GPX importer uses.
"""

from __future__ import annotations

import io
import struct
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import fitdecode

from src.services.track_segments import SegmentResult, compute_best_segments

SEMICIRCLES_TO_DEGREES = 180 / 2**31


@dataclass
class FitLap:
    index: int
    start_time: str | None
    timer_seconds: int
    elapsed_seconds: int | None
    distance_km: float
    pace: float | None  # min/km
    avg_hr: int | None
    max_hr: int | None
    avg_cadence: int | None  # steps/min
    avg_power: int | None
    total_ascent_m: float | None
    trigger: str | None


@dataclass
class FitSample:
    t_seconds: float
    distance_km: float | None
    heart_rate: int | None
    cadence: int | None  # steps/min
    speed_mps: float | None
    altitude_m: float | None
    power: int | None
    lat: float | None
    lon: float | None


@dataclass
class FitParseResult:
    date: str
    start_time: str
    title: str
    distance_km: float
    duration_seconds: int  # moving (timer) time
    elapsed_seconds: int
    is_indoor: bool
    source_uuid: str | None
    avg_hr: int | None
    max_hr: int | None
    avg_cadence: int | None
    max_cadence: int | None
    calories: int | None
    total_ascent_m: float | None
    total_descent_m: float | None
    avg_power: int | None
    max_power: int | None
    avg_temperature_c: float | None
    laps: list[FitLap] = field(default_factory=list)
    samples: list[FitSample] = field(default_factory=list)
    segments: list[SegmentResult] = field(default_factory=list)


def _value(frame: fitdecode.FitDataMessage, *names: str) -> Any:
    """First non-null value among alternative field names (e.g. enhanced_speed, speed)."""
    for name in names:
        if frame.has_field(name):
            value = frame.get_value(name, fallback=None)
            if value is not None:
                return value
    return None


def _as_int(value: Any) -> int | None:
    return None if value is None else int(round(float(value)))


def _as_float(value: Any) -> float | None:
    return None if value is None else float(value)


def _steps_per_minute(cadence: Any, fractional: Any) -> int | None:
    """FIT running cadence is strides/min (one foot); the app shows steps/min."""
    if cadence is None:
        return None
    return int(round((float(cadence) + float(fractional or 0)) * 2))


def _degrees(semicircles: Any) -> float | None:
    return None if semicircles is None else float(semicircles) * SEMICIRCLES_TO_DEGREES


def _iso(value: Any) -> str | None:
    if not isinstance(value, datetime):
        return None
    aware: datetime = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    text: str = aware.astimezone(UTC).isoformat()
    return text


def _uuid(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (tuple, list, bytes, bytearray)):
        raw: bytes = bytes(value)
        if len(raw) == 16:
            return str(uuid.UUID(bytes=raw))
        hex_value: str = raw.hex()
        return hex_value or None
    text: str = str(value)
    return text


def parse_fit(data: bytes) -> FitParseResult:
    session: fitdecode.FitDataMessage | None = None
    sport_frame: fitdecode.FitDataMessage | None = None
    activity: fitdecode.FitDataMessage | None = None
    lap_frames: list[fitdecode.FitDataMessage] = []
    record_frames: list[fitdecode.FitDataMessage] = []

    try:
        with fitdecode.FitReader(io.BytesIO(data), check_crc=fitdecode.CrcCheck.RAISE) as reader:
            for frame in reader:
                if not isinstance(frame, fitdecode.FitDataMessage):
                    continue
                if frame.name == "session" and session is None:
                    session = frame
                elif frame.name == "sport" and sport_frame is None:
                    sport_frame = frame
                elif frame.name == "activity" and activity is None:
                    activity = frame
                elif frame.name == "lap":
                    lap_frames.append(frame)
                elif frame.name == "record":
                    record_frames.append(frame)
    except (fitdecode.FitError, struct.error, EOFError, KeyError) as exc:
        raise ValueError("Invalid FIT file") from exc

    if session is None:
        raise ValueError("FIT file has no session message")
    if len(record_frames) < 2:
        raise ValueError("FIT file must contain at least 2 records")

    start_dt = _value(session, "start_time")
    if not isinstance(start_dt, datetime):
        start_dt = _value(record_frames[0], "timestamp")
    if not isinstance(start_dt, datetime):
        raise ValueError("FIT file has no start time")
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=UTC)

    # Local date if the device recorded one, otherwise the UTC date of the start.
    local_dt = _value(activity, "local_timestamp") if activity is not None else None
    date_dt = local_dt if isinstance(local_dt, datetime) else start_dt
    date = date_dt.strftime("%Y-%m-%d")

    # --- samples ---------------------------------------------------------
    samples: list[FitSample] = []
    for rec in record_frames:
        ts = _value(rec, "timestamp")
        if not isinstance(ts, datetime):
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        distance_m = _as_float(_value(rec, "distance"))
        samples.append(
            FitSample(
                t_seconds=(ts - start_dt).total_seconds(),
                distance_km=None if distance_m is None else distance_m / 1000,
                heart_rate=_as_int(_value(rec, "heart_rate")),
                cadence=_steps_per_minute(
                    _value(rec, "cadence"), _value(rec, "fractional_cadence")
                ),
                speed_mps=_as_float(_value(rec, "enhanced_speed", "speed")),
                altitude_m=_as_float(_value(rec, "enhanced_altitude", "altitude")),
                power=_as_int(_value(rec, "power")),
                lat=_degrees(_value(rec, "position_lat")),
                lon=_degrees(_value(rec, "position_long")),
            )
        )
    if len(samples) < 2:
        raise ValueError("FIT file must contain at least 2 timestamped records")

    # --- totals ------------------------------------------------------------
    total_distance_m = _as_float(_value(session, "total_distance"))
    if total_distance_m is None:
        last_with_distance = [s.distance_km for s in samples if s.distance_km is not None]
        total_distance_m = (last_with_distance[-1] * 1000) if last_with_distance else 0.0
    timer = _as_float(_value(session, "total_timer_time"))
    elapsed = _as_float(_value(session, "total_elapsed_time"))
    if timer is None and elapsed is None:
        timer = elapsed = samples[-1].t_seconds
    duration_seconds = int(round(timer if timer is not None else elapsed or 0))
    elapsed_seconds = int(round(elapsed if elapsed is not None else timer or 0))
    if duration_seconds <= 0 or total_distance_m <= 0:
        raise ValueError("FIT file has no distance or duration")

    # --- best-effort segments from the record stream ---------------------
    cum_dist: list[float] = []
    cum_time: list[float] = []
    for s in samples:
        if s.distance_km is None:
            continue
        if cum_dist and s.distance_km < cum_dist[-1]:
            continue  # keep the series monotonic
        cum_dist.append(s.distance_km)
        cum_time.append(s.t_seconds)
    segments = (
        compute_best_segments(cum_dist, cum_time, total_distance_m / 1000)
        if len(cum_dist) >= 2
        else []
    )

    # --- laps -------------------------------------------------------------
    laps: list[FitLap] = []
    for i, lap in enumerate(lap_frames):
        lap_distance_m = _as_float(_value(lap, "total_distance")) or 0.0
        lap_timer = _as_float(_value(lap, "total_timer_time", "total_elapsed_time")) or 0.0
        lap_elapsed = _as_float(_value(lap, "total_elapsed_time"))
        distance_km = lap_distance_m / 1000
        pace = (
            round((lap_timer / 60) / distance_km, 2) if distance_km > 0 and lap_timer > 0 else None
        )
        index = _as_int(_value(lap, "message_index"))
        trigger = _value(lap, "lap_trigger")
        laps.append(
            FitLap(
                index=index if index is not None else i,
                start_time=_iso(_value(lap, "start_time")),
                timer_seconds=int(round(lap_timer)),
                elapsed_seconds=None if lap_elapsed is None else int(round(lap_elapsed)),
                distance_km=round(distance_km, 3),
                pace=pace,
                avg_hr=_as_int(_value(lap, "avg_heart_rate")),
                max_hr=_as_int(_value(lap, "max_heart_rate")),
                avg_cadence=_steps_per_minute(
                    _value(lap, "avg_running_cadence", "avg_cadence"),
                    _value(lap, "avg_fractional_cadence"),
                ),
                avg_power=_as_int(_value(lap, "avg_power")),
                total_ascent_m=_as_float(_value(lap, "total_ascent")),
                trigger=None if trigger is None else str(trigger),
            )
        )
    laps.sort(key=lambda lap: lap.index)

    # --- title / flags -------------------------------------------------------
    indoor_flag = _value(session, "SESSION INDOOR")
    sub_sport = _value(session, "sub_sport") or (
        _value(sport_frame, "sub_sport") if sport_frame is not None else None
    )
    is_indoor = bool(indoor_flag) or str(sub_sport) in {"indoor_running", "treadmill"}
    sport_name = (_value(sport_frame, "name") if sport_frame is not None else None) or "Run"
    title = f"Indoor {sport_name}" if is_indoor else str(sport_name)

    return FitParseResult(
        date=date,
        start_time=start_dt.astimezone(UTC).isoformat(),
        title=title,
        distance_km=round(total_distance_m / 1000, 2),
        duration_seconds=duration_seconds,
        elapsed_seconds=elapsed_seconds,
        is_indoor=is_indoor,
        source_uuid=_uuid(_value(session, "SESSION UUID")),
        avg_hr=_as_int(_value(session, "avg_heart_rate")),
        max_hr=_as_int(_value(session, "max_heart_rate")),
        avg_cadence=_steps_per_minute(
            _value(session, "avg_running_cadence", "avg_cadence"),
            _value(session, "avg_fractional_cadence"),
        ),
        max_cadence=_steps_per_minute(
            _value(session, "max_running_cadence", "max_cadence"),
            _value(session, "max_fractional_cadence"),
        ),
        calories=_as_int(_value(session, "total_calories")),
        total_ascent_m=_as_float(_value(session, "total_ascent")),
        total_descent_m=_as_float(_value(session, "total_descent")),
        avg_power=_as_int(_value(session, "avg_power")),
        max_power=_as_int(_value(session, "max_power")),
        avg_temperature_c=_as_float(_value(session, "avg_temperature")),
        laps=laps,
        samples=samples,
        segments=segments,
    )
