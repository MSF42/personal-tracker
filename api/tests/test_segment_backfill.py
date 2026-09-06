import os
import tempfile

import aiosqlite

from src.db.migrations import backfill_segment_bounds, run_migrations


async def test_backfill_fills_offsets_from_samples() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    try:
        await run_migrations(path)
        async with aiosqlite.connect(path) as db:
            db.row_factory = aiosqlite.Row
            await db.execute(
                "INSERT INTO running_activities (id, date, duration_seconds, distance_km, has_gpx,"
                " created_at, updated_at) VALUES (1, '2026-03-01', 600, 2.0, 1, 'x', 'x')"
            )
            await db.executemany(
                "INSERT INTO run_samples (running_activity_id, t_seconds, distance_km) VALUES (1, ?, ?)",
                [(t, t * 2.0 / 600) for t in range(0, 601, 5)],
            )
            # Legacy segment row without offsets.
            await db.execute(
                "INSERT INTO gpx_segments (running_activity_id, segment_name, distance_km,"
                " duration_seconds, pace, pace_formatted) VALUES (1, '1K', 1.0, 300, 5.0, '5:00')"
            )
            await db.commit()

            assert await backfill_segment_bounds(db) == 1
            cursor = await db.execute(
                "SELECT segment_name, start_seconds, end_seconds FROM gpx_segments"
                " WHERE running_activity_id = 1 ORDER BY distance_km"
            )
            rows = [dict(r) for r in await cursor.fetchall()]
            assert [r["segment_name"] for r in rows] == ["1K", "1 Mile"]
            assert all(
                r["start_seconds"] is not None and r["end_seconds"] is not None for r in rows
            )
            # Second pass is a no-op.
            assert await backfill_segment_bounds(db) == 0
    finally:
        os.unlink(path)
