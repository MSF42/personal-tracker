"""Best-effort segment detection shared by the GPX and FIT importers.

Given cumulative distance (km) and cumulative time (s) arrays from a recorded
track, find the fastest stretch matching each standard race distance.
"""

from dataclasses import dataclass

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
    start_seconds: float | None = None  # offset from the run start
    end_seconds: float | None = None


def format_pace(pace_min_per_km: float) -> str:
    minutes = int(pace_min_per_km)
    seconds = int((pace_min_per_km - minutes) * 60)
    return f"{minutes}:{seconds:02d}"


def compute_best_segments(
    cum_dist: list[float], cum_time: list[float], total_distance: float
) -> list[SegmentResult]:
    """Fastest window of each standard distance.

    For every start index i, only end indices j with dist_min <= d <= dist_max are
    candidates. Because cum_dist is monotonic, the first such j only moves forward
    as i advances (two-pointer scan), so the cost is O(n * window) rather than O(n^2).
    """
    results: list[SegmentResult] = []
    n = len(cum_dist)

    for name, dist_min, dist_max in SEGMENT_DEFS:
        if total_distance < dist_min:
            continue

        best_pace = float("inf")
        best_dist = 0.0
        best_time = 0.0
        best_i = 0
        best_j = 0

        j_start = 1
        for i in range(n):
            if j_start <= i:
                j_start = i + 1
            while j_start < n and cum_dist[j_start] - cum_dist[i] < dist_min:
                j_start += 1
            if j_start >= n:
                break
            for j in range(j_start, n):
                d = cum_dist[j] - cum_dist[i]
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
                    best_i = i
                    best_j = j

        if best_pace < float("inf"):
            results.append(
                SegmentResult(
                    name=name,
                    distance_km=round(best_dist, 3),
                    duration_seconds=int(best_time),
                    pace=round(best_pace, 2),
                    pace_formatted=format_pace(best_pace),
                    start_seconds=round(cum_time[best_i], 1),
                    end_seconds=round(cum_time[best_j], 1),
                )
            )

    return results
