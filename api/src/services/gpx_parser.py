import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from math import asin, cos, radians, sin, sqrt

GPX_NS = "{http://www.topografix.com/GPX/1/1}"

SEGMENT_DEFS = [
    ("1K", 1.0, 1.05),
    ("1 Mile", 1.60935, 1.7),
    ("5K", 5.0, 5.1),
    ("10K", 10.0, 10.2),
    ("10 Mile", 16.0935, 16.5),
    ("Half Marathon", 21.0975, 21.5),
    ("Marathon", 42.195, 43.0),
]


@dataclass
class SegmentResult:
    name: str
    distance_km: float
    duration_seconds: int
    pace: float
    pace_formatted: str


@dataclass
class GpxParseResult:
    date: str
    distance_km: float
    duration_seconds: int
    segments: list[SegmentResult]
    title: str | None = None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r_lat1 = radians(lat1)
    r_lat2 = radians(lat2)
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = sin(d_lat / 2) ** 2 + cos(r_lat1) * cos(r_lat2) * sin(d_lon / 2) ** 2
    return 12742 * asin(sqrt(a))


def _format_pace(pace_min_per_km: float) -> str:
    minutes = int(pace_min_per_km)
    seconds = int((pace_min_per_km - minutes) * 60)
    return f"{minutes}:{seconds:02d}"


def _compute_segments(
    cum_dist: list[float], cum_time: list[float], total_distance: float
) -> list[SegmentResult]:
    results: list[SegmentResult] = []
    n = len(cum_dist)

    for name, dist_min, dist_max in SEGMENT_DEFS:
        if total_distance < dist_min:
            continue

        best_pace = float("inf")
        best_dist = 0.0
        best_time = 0.0

        for i in range(n):
            for j in range(i + 1, n):
                d = cum_dist[j] - cum_dist[i]
                if d < dist_min:
                    continue
                if d > dist_max:
                    break
                t = cum_time[j] - cum_time[i]
                if t <= 0:
                    continue
                pace = (t / 60) / d
                if pace < best_pace:
                    best_pace = pace
                    best_dist = d
                    best_time = t

        if best_pace < float("inf"):
            results.append(
                SegmentResult(
                    name=name,
                    distance_km=round(best_dist, 3),
                    duration_seconds=int(best_time),
                    pace=round(best_pace, 2),
                    pace_formatted=_format_pace(best_pace),
                )
            )

    return results


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
    for trkpt in root.iter(f"{GPX_NS}trkpt"):
        lat = float(trkpt.attrib["lat"])
        lon = float(trkpt.attrib["lon"])
        time_el = trkpt.find(f"{GPX_NS}time")
        if time_el is None or time_el.text is None:
            continue
        time_str = time_el.text.replace("Z", "+00:00")
        t = datetime.fromisoformat(time_str)
        trackpoints.append((lat, lon, t))

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

    segments = _compute_segments(cum_dist, cum_time, total_distance)

    date_str = trackpoints[0][2].strftime("%Y-%m-%d")

    return GpxParseResult(
        date=date_str,
        distance_km=round(total_distance, 2),
        duration_seconds=int(total_time),
        segments=segments,
        title=title,
    )
