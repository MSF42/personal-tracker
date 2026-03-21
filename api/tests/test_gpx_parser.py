"""Unit tests for api/src/services/gpx_parser.py."""

import math
import textwrap

import pytest

from src.services.gpx_parser import GpxParseResult, haversine_km, parse_gpx

# ---------------------------------------------------------------------------
# haversine_km
# ---------------------------------------------------------------------------


def test_haversine_same_point_is_zero():
    assert haversine_km(51.5074, -0.1278, 51.5074, -0.1278) == 0.0


def test_haversine_nyc_to_london():
    # New York City → London is well-known at roughly 5,570 km.
    nyc_lat, nyc_lon = 40.7128, -74.0060
    lon_lat, lon_lon = 51.5074, -0.1278
    d = haversine_km(nyc_lat, nyc_lon, lon_lat, lon_lon)
    assert 5500 < d < 5650, f"Expected ~5570 km, got {d:.1f} km"


def test_haversine_close_points_small_distance():
    # Two points on the equator separated by 0.001 degree longitude ≈ 0.069 km.
    d = haversine_km(0.0, 0.0, 0.0, 0.001)
    assert 0.05 < d < 0.12, f"Expected small distance ~0.069 km, got {d:.4f} km"


def test_haversine_symmetry():
    # Distance A→B should equal distance B→A.
    d_ab = haversine_km(48.8566, 2.3522, 41.9028, 12.4964)  # Paris → Rome
    d_ba = haversine_km(41.9028, 12.4964, 48.8566, 2.3522)  # Rome → Paris
    assert math.isclose(d_ab, d_ba, rel_tol=1e-9)


def test_haversine_paris_to_rome():
    # Paris (48.8566, 2.3522) → Rome (41.9028, 12.4964) ≈ 1105 km.
    d = haversine_km(48.8566, 2.3522, 41.9028, 12.4964)
    assert 1050 < d < 1160, f"Expected ~1105 km, got {d:.1f} km"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_GPX_TEMPLATE = """\
<?xml version="1.0"?>
<gpx xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    {name_element}
    <trkseg>
      {trackpoints}
    </trkseg>
  </trk>
</gpx>"""


def _make_trkpt(lat: float, lon: float, time_str: str) -> str:
    return (
        f'<trkpt lat="{lat}" lon="{lon}">'
        f"<time>{time_str}</time>"
        f"</trkpt>"
    )


def _build_gpx(trackpoints: list[tuple[float, float, str]], title: str | None = None) -> bytes:
    name_el = f"<name>{title}</name>" if title else ""
    trkpts = "\n      ".join(
        _make_trkpt(lat, lon, ts) for lat, lon, ts in trackpoints
    )
    xml = _GPX_TEMPLATE.format(name_element=name_el, trackpoints=trkpts)
    return xml.encode()


# ---------------------------------------------------------------------------
# parse_gpx — basic parsing
# ---------------------------------------------------------------------------


def test_parse_gpx_returns_gpx_parse_result():
    gpx = _build_gpx([
        (51.5074, -0.1278, "2024-01-01T10:00:00Z"),
        (51.5074, -0.1268, "2024-01-01T10:05:00Z"),
    ])
    result = parse_gpx(gpx)
    assert isinstance(result, GpxParseResult)


def test_parse_gpx_date():
    gpx = _build_gpx([
        (51.5074, -0.1278, "2024-03-15T08:00:00Z"),
        (51.5074, -0.1268, "2024-03-15T08:05:00Z"),
    ])
    result = parse_gpx(gpx)
    assert result.date == "2024-03-15"


def test_parse_gpx_title_from_trk_name():
    gpx = _build_gpx(
        [
            (51.5074, -0.1278, "2024-01-01T10:00:00Z"),
            (51.5074, -0.1268, "2024-01-01T10:05:00Z"),
        ],
        title="Morning Run",
    )
    result = parse_gpx(gpx)
    assert result.title == "Morning Run"


def test_parse_gpx_no_title_is_none():
    gpx = _build_gpx([
        (51.5074, -0.1278, "2024-01-01T10:00:00Z"),
        (51.5074, -0.1268, "2024-01-01T10:05:00Z"),
    ])
    result = parse_gpx(gpx)
    assert result.title is None


def test_parse_gpx_duration_seconds():
    # 5 minutes = 300 seconds
    gpx = _build_gpx([
        (51.5074, -0.1278, "2024-01-01T10:00:00Z"),
        (51.5074, -0.1268, "2024-01-01T10:05:00Z"),
    ])
    result = parse_gpx(gpx)
    assert result.duration_seconds == 300


def test_parse_gpx_distance_positive():
    gpx = _build_gpx([
        (51.5074, -0.1278, "2024-01-01T10:00:00Z"),
        (51.5074, -0.1268, "2024-01-01T10:05:00Z"),
    ])
    result = parse_gpx(gpx)
    assert result.distance_km > 0


def test_parse_gpx_distance_reasonable():
    # Two points ~0.069 km apart on the same latitude.
    gpx = _build_gpx([
        (0.0, 0.0, "2024-01-01T10:00:00Z"),
        (0.0, 0.001, "2024-01-01T10:05:00Z"),
    ])
    result = parse_gpx(gpx)
    assert 0.05 < result.distance_km < 0.12


# ---------------------------------------------------------------------------
# parse_gpx — segment detection
# ---------------------------------------------------------------------------


def test_parse_gpx_1k_segment_detected():
    # A single ~1.0 km hop in 5 minutes should trigger the "1K" segment.
    # At lat=0, lon offset 0.00900 ≈ 1.00075 km, which is in [1.0, 1.05].
    gpx = _build_gpx([
        (0.0, 0.0,    "2024-01-01T10:00:00Z"),
        (0.0, 0.009,  "2024-01-01T10:05:00Z"),
    ])
    result = parse_gpx(gpx)
    assert result.distance_km >= 1.0
    segment_names = [s.name for s in result.segments]
    assert "1K" in segment_names, f"Expected '1K' segment, got: {segment_names}"


def test_parse_gpx_1k_segment_fields():
    gpx = _build_gpx([
        (0.0, 0.0,   "2024-01-01T10:00:00Z"),
        (0.0, 0.009, "2024-01-01T10:05:00Z"),
    ])
    result = parse_gpx(gpx)
    seg = next(s for s in result.segments if s.name == "1K")
    assert seg.distance_km > 0
    assert seg.duration_seconds > 0
    assert seg.pace > 0
    assert ":" in seg.pace_formatted  # e.g. "4:58"


def test_parse_gpx_no_segments_for_short_route():
    # Two very close points — total < 1 km, so no segment should be found.
    gpx = _build_gpx([
        (0.0, 0.0,     "2024-01-01T10:00:00Z"),
        (0.0, 0.0001,  "2024-01-01T10:01:00Z"),
    ])
    result = parse_gpx(gpx)
    assert result.segments == []


# ---------------------------------------------------------------------------
# parse_gpx — error handling
# ---------------------------------------------------------------------------


def test_parse_gpx_raises_for_one_trackpoint():
    gpx = _build_gpx([
        (51.5074, -0.1278, "2024-01-01T10:00:00Z"),
    ])
    with pytest.raises(ValueError, match="at least 2 trackpoints"):
        parse_gpx(gpx)


def test_parse_gpx_raises_for_zero_trackpoints():
    gpx = _build_gpx([])
    with pytest.raises(ValueError, match="at least 2 trackpoints"):
        parse_gpx(gpx)


def test_parse_gpx_malformed_missing_time_skipped():
    # A trkpt without <time> is silently skipped; only the two valid ones count.
    xml = textwrap.dedent("""\
        <?xml version="1.0"?>
        <gpx xmlns="http://www.topografix.com/GPX/1/1">
          <trk>
            <trkseg>
              <trkpt lat="51.5074" lon="-0.1278"><time>2024-01-01T10:00:00Z</time></trkpt>
              <trkpt lat="51.5074" lon="-0.1270"/>
              <trkpt lat="51.5074" lon="-0.1268"><time>2024-01-01T10:05:00Z</time></trkpt>
            </trkseg>
          </trk>
        </gpx>
    """)
    result = parse_gpx(xml.encode())
    assert isinstance(result, GpxParseResult)
    assert result.duration_seconds == 300
