import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import UTC, datetime
from math import asin, cos, radians, sin, sqrt

from src.services.track_segments import (  # noqa: F401 (re-exported)
    SEGMENT_DEFS,
    SegmentResult,
    compute_best_segments,
    format_pace,
)

GPX_NS = "{http://www.topografix.com/GPX/1/1}"


@dataclass
class GpxSample:
    t_seconds: float
    distance_km: float  # cumulative
    lat: float
    lon: float
    altitude_m: float | None = None


@dataclass
class GpxParseResult:
    date: str
    distance_km: float
    duration_seconds: int
    segments: list[SegmentResult]
    title: str | None = None
    start_time: str | None = None  # UTC ISO 8601 of the first trackpoint
    samples: list[GpxSample] = field(default_factory=list)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r_lat1 = radians(lat1)
    r_lat2 = radians(lat2)
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = sin(d_lat / 2) ** 2 + cos(r_lat1) * cos(r_lat2) * sin(d_lon / 2) ** 2
    return 12742 * asin(sqrt(a))


def parse_gpx(xml_bytes: bytes) -> GpxParseResult:
    root = ET.fromstring(xml_bytes)

    # Extract title: try <trk><name> first, then <metadata><name>
    title: str | None = None
    trk_el = root.find(f"{GPX_NS}trk")
    if trk_el is not None:
        name_el = trk_el.find(f"{GPX_NS}name")
        if name_el is not None and name_el.text:
            title = name_el.text.strip()
    if not title:
        metadata_el = root.find(f"{GPX_NS}metadata")
        if metadata_el is not None:
            name_el = metadata_el.find(f"{GPX_NS}name")
            if name_el is not None and name_el.text:
                title = name_el.text.strip()

    trackpoints: list[tuple[float, float, datetime]] = []
    elevations: list[float | None] = []
    for trkpt in root.iter(f"{GPX_NS}trkpt"):
        lat = float(trkpt.attrib["lat"])
        lon = float(trkpt.attrib["lon"])
        time_el = trkpt.find(f"{GPX_NS}time")
        if time_el is None or time_el.text is None:
            continue
        time_str = time_el.text.replace("Z", "+00:00")
        t = datetime.fromisoformat(time_str)
        trackpoints.append((lat, lon, t))
        ele_el = trkpt.find(f"{GPX_NS}ele")
        try:
            elevations.append(float(ele_el.text) if ele_el is not None and ele_el.text else None)
        except ValueError:
            elevations.append(None)

    if len(trackpoints) < 2:
        raise ValueError("GPX file must contain at least 2 trackpoints with time data")

    cum_dist = [0.0]
    cum_time = [0.0]
    start_time = trackpoints[0][2]

    for i in range(1, len(trackpoints)):
        prev_lat, prev_lon, _ = trackpoints[i - 1]
        curr_lat, curr_lon, curr_time = trackpoints[i]
        d = haversine_km(prev_lat, prev_lon, curr_lat, curr_lon)
        cum_dist.append(cum_dist[-1] + d)
        cum_time.append((curr_time - start_time).total_seconds())

    total_distance = cum_dist[-1]
    total_time = cum_time[-1]

    segments = compute_best_segments(cum_dist, cum_time, total_distance)

    samples = [
        GpxSample(
            t_seconds=cum_time[i],
            distance_km=round(cum_dist[i], 4),
            lat=trackpoints[i][0],
            lon=trackpoints[i][1],
            altitude_m=elevations[i],
        )
        for i in range(len(trackpoints))
    ]

    date_str = trackpoints[0][2].strftime("%Y-%m-%d")

    return GpxParseResult(
        date=date_str,
        distance_km=round(total_distance, 2),
        duration_seconds=int(total_time),
        segments=segments,
        title=title,
        start_time=start_time.astimezone(UTC).isoformat(),
        samples=samples,
    )
