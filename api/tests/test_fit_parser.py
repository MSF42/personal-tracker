"""Unit tests for api/src/services/fit_parser.py using the synthetic FIT encoder."""

from datetime import UTC, datetime

import pytest

from src.services.fit_parser import parse_fit
from tests.fit_builder import FitRecord, FitSpec, build_fit, simple_run

UUID_BYTES = bytes(range(16))


def test_parses_totals_and_summary() -> None:
    result = parse_fit(simple_run(seconds=720, distance_m=2000, hr=150, uuid_bytes=UUID_BYTES))
    assert result.distance_km == 2.0
    assert result.duration_seconds == 720
    assert result.elapsed_seconds == 720
    assert result.date == "2026-03-01"
    assert result.start_time == "2026-03-01T09:00:00+00:00"
    assert result.title == "Run"
    assert result.is_indoor is False
    assert result.avg_hr == 150
    assert result.max_hr == 154
    assert result.avg_cadence == 160  # 80 strides/min -> 160 steps/min
    assert result.calories == 170
    assert result.total_ascent_m == 10
    assert result.avg_power == 250
    assert result.source_uuid == "00010203-0405-0607-0809-0a0b0c0d0e0f"


def test_local_date_comes_from_activity_local_timestamp() -> None:
    # 01:30 UTC with a -4 h local offset is still the previous evening locally.
    start = datetime(2026, 3, 2, 1, 30, tzinfo=UTC)
    result = parse_fit(simple_run(start=start, seconds=600, distance_m=1500))
    assert result.date == "2026-03-01"
    assert result.start_time.startswith("2026-03-02T01:30")


def test_samples_laps_and_segments() -> None:
    result = parse_fit(simple_run(seconds=720, distance_m=2000))
    assert len(result.samples) == 73
    first, last = result.samples[0], result.samples[-1]
    assert first.t_seconds == 0 and last.t_seconds == 720
    assert last.distance_km == pytest.approx(2.0)
    assert first.cadence == 160
    assert first.lat == pytest.approx(51.5, abs=1e-6)
    assert first.altitude_m == pytest.approx(300, abs=0.2)
    assert [lap.index for lap in result.laps] == [0, 1]
    assert result.laps[0].distance_km == 1.0
    assert result.laps[0].timer_seconds == 360
    assert result.laps[0].pace == 6.0
    assert result.laps[0].avg_cadence == 160
    names = [s.name for s in result.segments]
    assert "1K" in names and "1 Mile" in names
    one_k = next(s for s in result.segments if s.name == "1K")
    assert one_k.pace == pytest.approx(6.0, abs=0.1)


def test_indoor_flag_prefixes_title() -> None:
    result = parse_fit(simple_run(indoor=True))
    assert result.is_indoor is True
    assert result.title == "Indoor Run"


def test_invalid_bytes_raise_value_error() -> None:
    with pytest.raises(ValueError, match="Invalid FIT"):
        parse_fit(b"definitely not a fit file")


def test_missing_session_raises() -> None:
    spec = FitSpec(
        start=datetime(2026, 3, 1, 9, 0, tzinfo=UTC),
        records=[FitRecord(offset_s=0, distance_m=0), FitRecord(offset_s=60, distance_m=200)],
        include_session=False,
    )
    with pytest.raises(ValueError, match="no session"):
        parse_fit(build_fit(spec))
