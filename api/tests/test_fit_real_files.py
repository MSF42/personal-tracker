"""Optional: parse real device exports. Run with FIT_SAMPLES_DIR=~/Downloads."""

import os
from pathlib import Path

import pytest

from src.services.fit_parser import parse_fit

SAMPLES_DIR = os.environ.get("FIT_SAMPLES_DIR")
FILES = sorted(Path(SAMPLES_DIR).expanduser().glob("*.fit")) if SAMPLES_DIR else []


@pytest.mark.skipif(not FILES, reason="set FIT_SAMPLES_DIR to a folder of .fit files")
@pytest.mark.parametrize("path", FILES, ids=[p.name for p in FILES])
def test_real_fit_file_parses(path: Path) -> None:
    result = parse_fit(path.read_bytes())
    assert 0.1 < result.distance_km < 100
    assert 60 < result.duration_seconds < 6 * 3600
    assert result.elapsed_seconds >= result.duration_seconds
    assert len(result.samples) > 10
    assert result.samples[-1].t_seconds > 0
    assert result.avg_hr is None or 40 < result.avg_hr < 220
    assert result.avg_cadence is None or 100 < result.avg_cadence < 240
    assert result.date.startswith("20")
    assert result.laps, "device exports carry at least one lap"
