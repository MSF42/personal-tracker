"""compute_best_segments: bounds, and the two-pointer scan matches brute force."""

import random

from src.services.track_segments import (
    SEGMENT_DEFS,
    SegmentResult,
    compute_best_segments,
    format_pace,
)


def _brute_force(cum_dist: list[float], cum_time: list[float]) -> list[SegmentResult]:
    out: list[SegmentResult] = []
    n = len(cum_dist)
    for name, dist_min, dist_max in SEGMENT_DEFS:
        if cum_dist[-1] < dist_min:
            continue
        best = (float("inf"), 0.0, 0.0, 0, 0)
        for i in range(n):
            for j in range(i + 1, n):
                d = cum_dist[j] - cum_dist[i]
                if d < dist_min or d > dist_max:
                    continue
                t = cum_time[j] - cum_time[i]
                if t <= 0:
                    continue
                pace = (t / 60) / d
                if pace < best[0]:
                    best = (pace, d, t, i, j)
        if best[0] < float("inf"):
            pace, d, t, i, j = best
            out.append(
                SegmentResult(
                    name,
                    round(d, 3),
                    int(t),
                    round(pace, 2),
                    format_pace(pace),
                    round(cum_time[i], 1),
                    round(cum_time[j], 1),
                )
            )
    return out


def _track(seed: int, n: int = 400) -> tuple[list[float], list[float]]:
    rng = random.Random(seed)
    cum_dist = [0.0]
    cum_time = [0.0]
    for _ in range(n):
        cum_dist.append(cum_dist[-1] + rng.uniform(0.002, 0.006))  # 2–6 m per second
        cum_time.append(cum_time[-1] + 1.0)
    return cum_dist, cum_time


def test_matches_brute_force_on_random_tracks() -> None:
    for seed in range(5):
        cum_dist, cum_time = _track(seed)
        assert compute_best_segments(cum_dist, cum_time, cum_dist[-1]) == _brute_force(
            cum_dist, cum_time
        )


def test_reports_start_and_end_offsets() -> None:
    # 2 km at a steady 5 min/km except a fast 1 km burst from 300 s to 540 s.
    cum_dist, cum_time = [0.0], [0.0]
    for sec in range(1, 900):
        speed = 1 / 240 if 300 <= sec < 540 else 1 / 330  # km per second
        cum_dist.append(cum_dist[-1] + speed)
        cum_time.append(float(sec))
    one_k = next(
        s for s in compute_best_segments(cum_dist, cum_time, cum_dist[-1]) if s.name == "1K"
    )
    assert one_k.start_seconds is not None and one_k.end_seconds is not None
    assert 295 <= one_k.start_seconds <= 305
    assert one_k.end_seconds - one_k.start_seconds == one_k.duration_seconds
    assert one_k.pace < 4.2
