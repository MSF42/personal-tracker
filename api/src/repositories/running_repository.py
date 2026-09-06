from datetime import UTC, datetime
from typing import Any

from aiosqlite import Connection

from src.models.running import (
    CreateRunningActivityRequest,
    RunningActivityInDB,
    RunningActivityResponse,
    UpdateRunningActivityRequest,
    running_from_db,
)
from src.repositories.utils import execute_update, require_found, require_row_id


class SQLiteRunningRepository:
    def __init__(self, db: Connection):
        self.db = db

    async def create(self, activity: CreateRunningActivityRequest) -> RunningActivityResponse:
        now = datetime.now(UTC).isoformat()

        cursor = await self.db.execute(
            """
            INSERT INTO running_activities (date, duration_seconds, distance_km, notes, title,
                                            created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                activity.date,
                activity.duration_seconds,
                activity.distance_km,
                activity.notes,
                activity.title,
                now,
                now,
            ),
        )
        await self.db.commit()

        return require_found(
            await self.find_by_id(require_row_id(cursor.lastrowid)), "Running activity"
        )

    async def find_by_id(self, activity_id: int) -> RunningActivityResponse | None:
        cursor = await self.db.execute(
            "SELECT * FROM running_activities WHERE id = ?",
            (activity_id,),
        )
        row = await cursor.fetchone()

        if row is None:
            return None

        activity_in_db = RunningActivityInDB(**dict(row))
        return running_from_db(activity_in_db)

    async def find_all(self) -> list[RunningActivityResponse]:
        cursor = await self.db.execute(
            "SELECT * FROM running_activities ORDER BY date DESC"  # Order by date, not created_at
        )
        rows = await cursor.fetchall()

        return [running_from_db(RunningActivityInDB(**dict(row))) for row in rows]

    async def delete(self, activity_id: int) -> bool:
        cursor = await self.db.execute(
            "DELETE FROM running_activities WHERE id = ?",
            (activity_id,),
        )
        await self.db.commit()

        return cursor.rowcount > 0

    async def update(
        self, activity_id: int, data: UpdateRunningActivityRequest
    ) -> RunningActivityResponse | None:
        existing = await self.find_by_id(activity_id)
        if existing is None:
            return None

        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            return existing

        await execute_update(self.db, "running_activities", update_data, activity_id)
        return await self.find_by_id(activity_id)

    async def get_stats_by_month(self, year: int) -> list[dict[str, Any]]:
        """Get monthly running statistics for a given year."""
        cursor = await self.db.execute(
            """
            SELECT strftime('%Y-%m', date) as month,
                   COUNT(*)                as total_runs,
                   SUM(distance_km)        as total_distance,
                   SUM(duration_seconds)   as total_duration,
                   AVG(distance_km)        as avg_distance,
                   MAX(distance_km)        as longest_run
            FROM running_activities
            WHERE strftime('%Y', date) = ?
            GROUP BY month
            ORDER BY month DESC
            """,
            (str(year),),
        )
        return [dict(row) for row in await cursor.fetchall()]

    async def find_import_duplicate(
        self,
        import_sha256: str,
        date: str,
        distance_km: float,
        duration_seconds: int,
        source_uuid: str | None = None,
        start_time: str | None = None,
    ) -> RunningActivityResponse | None:
        """Find an already-imported run matching this file.

        Matches, in order of confidence: the exact same file (content hash), the
        same device workout (HealthFit session UUID), a track that started within
        a minute of an existing imported track (catches GPX vs FIT of one run),
        or a re-export with identical date and duration and distance within 10 m.
        """
        cursor = await self.db.execute(
            """
            SELECT * FROM running_activities
            WHERE import_sha256 = ?
               OR (? IS NOT NULL AND source_uuid = ?)
               OR (? IS NOT NULL AND has_gpx = 1 AND start_time IS NOT NULL
                   AND ABS(strftime('%s', start_time) - strftime('%s', ?)) <= 60)
               OR (has_gpx = 1 AND date = ? AND duration_seconds = ?
                   AND ABS(distance_km - ?) < 0.01)
            ORDER BY id ASC
            LIMIT 1
            """,
            (
                import_sha256,
                source_uuid,
                source_uuid,
                start_time,
                start_time,
                date,
                duration_seconds,
                distance_km,
            ),
        )
        row = await cursor.fetchone()
        return running_from_db(RunningActivityInDB(**dict(row))) if row is not None else None

    async def create_from_import(
        self,
        *,
        source: str,
        import_sha256: str,
        date: str,
        distance_km: float,
        duration_seconds: int,
        title: str | None,
        start_time: str | None = None,
        source_uuid: str | None = None,
        elapsed_seconds: int | None = None,
        is_indoor: bool = False,
        metrics: dict[str, Any] | None = None,
    ) -> RunningActivityResponse:
        """Insert a run that came from a track file (GPX or FIT). has_gpx marks 'has track data'."""
        now = datetime.now(UTC).isoformat()
        metrics = metrics or {}
        metric_cols = (
            "avg_hr",
            "max_hr",
            "avg_cadence",
            "max_cadence",
            "calories",
            "total_ascent_m",
            "total_descent_m",
            "avg_power",
            "max_power",
            "avg_temperature_c",
        )
        cols = [
            "date",
            "duration_seconds",
            "distance_km",
            "notes",
            "has_gpx",
            "title",
            "source",
            "import_sha256",
            "source_uuid",
            "start_time",
            "elapsed_seconds",
            "is_indoor",
            *metric_cols,
            "created_at",
            "updated_at",
        ]
        values: list[Any] = [
            date,
            duration_seconds,
            distance_km,
            None,
            1,
            title,
            source,
            import_sha256,
            source_uuid,
            start_time,
            elapsed_seconds,
            int(is_indoor),
            *(metrics.get(c) for c in metric_cols),
            now,
            now,
        ]
        placeholders = ", ".join("?" for _ in cols)
        cursor = await self.db.execute(
            f"INSERT INTO running_activities ({', '.join(cols)}) VALUES ({placeholders})",  # noqa: S608
            values,
        )
        await self.db.commit()
        return require_found(
            await self.find_by_id(require_row_id(cursor.lastrowid)), "Running activity"
        )

    async def save_laps(self, activity_id: int, laps: list[dict[str, Any]]) -> list[dict[str, Any]]:
        saved: list[dict[str, Any]] = []
        for lap in laps:
            cursor = await self.db.execute(
                """
                INSERT INTO run_laps (running_activity_id, lap_index, start_time, timer_seconds,
                                      elapsed_seconds, distance_km, pace, avg_hr, max_hr,
                                      avg_cadence, avg_power, total_ascent_m, trigger)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    activity_id,
                    lap["lap_index"],
                    lap.get("start_time"),
                    lap["timer_seconds"],
                    lap.get("elapsed_seconds"),
                    lap["distance_km"],
                    lap.get("pace"),
                    lap.get("avg_hr"),
                    lap.get("max_hr"),
                    lap.get("avg_cadence"),
                    lap.get("avg_power"),
                    lap.get("total_ascent_m"),
                    lap.get("trigger"),
                ),
            )
            saved.append({**lap, "id": cursor.lastrowid})
        await self.db.commit()
        return saved

    async def save_samples(self, activity_id: int, samples: list[dict[str, Any]]) -> int:
        await self.db.executemany(
            """
            INSERT INTO run_samples (running_activity_id, t_seconds, distance_km, heart_rate,
                                     cadence, speed_mps, altitude_m, power, lat, lon)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    activity_id,
                    s["t_seconds"],
                    s.get("distance_km"),
                    s.get("heart_rate"),
                    s.get("cadence"),
                    s.get("speed_mps"),
                    s.get("altitude_m"),
                    s.get("power"),
                    s.get("lat"),
                    s.get("lon"),
                )
                for s in samples
            ],
        )
        await self.db.commit()
        return len(samples)

    async def get_laps(self, activity_id: int) -> list[dict[str, Any]]:
        cursor = await self.db.execute(
            "SELECT * FROM run_laps WHERE running_activity_id = ? ORDER BY lap_index ASC",
            (activity_id,),
        )
        return [dict(row) for row in await cursor.fetchall()]

    async def get_samples(
        self, activity_id: int, max_points: int | None = None
    ) -> list[dict[str, Any]]:
        """Samples in time order, evenly thinned to at most max_points (first and last kept)."""
        cursor = await self.db.execute(
            """
            SELECT t_seconds, distance_km, heart_rate, cadence, speed_mps, altitude_m, power, lat, lon
            FROM run_samples WHERE running_activity_id = ? ORDER BY t_seconds ASC
            """,
            (activity_id,),
        )
        rows = [dict(row) for row in await cursor.fetchall()]
        if max_points is None or max_points < 2 or len(rows) <= max_points:
            return rows
        step = (len(rows) - 1) / (max_points - 1)
        return [rows[round(i * step)] for i in range(max_points)]

    async def save_segments(
        self, activity_id: int, segments: list[dict[str, object]]
    ) -> list[dict[str, object]]:
        saved = []
        for seg in segments:
            cursor = await self.db.execute(
                """
                INSERT INTO gpx_segments (running_activity_id, segment_name, distance_km,
                                          duration_seconds, pace, pace_formatted,
                                          start_seconds, end_seconds)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    activity_id,
                    seg["name"],
                    seg["distance_km"],
                    seg["duration_seconds"],
                    seg["pace"],
                    seg["pace_formatted"],
                    seg.get("start_seconds"),
                    seg.get("end_seconds"),
                ),
            )
            saved.append(
                {
                    "id": cursor.lastrowid,
                    "segment_name": seg["name"],
                    "distance_km": seg["distance_km"],
                    "duration_seconds": seg["duration_seconds"],
                    "pace": seg["pace"],
                    "pace_formatted": seg["pace_formatted"],
                    "start_seconds": seg.get("start_seconds"),
                    "end_seconds": seg.get("end_seconds"),
                }
            )
        await self.db.commit()
        return saved

    async def get_segments(self, activity_id: int) -> list[dict[str, Any]]:
        cursor = await self.db.execute(
            """
            SELECT id, segment_name, distance_km, duration_seconds, pace, pace_formatted,
                   start_seconds, end_seconds
            FROM gpx_segments
            WHERE running_activity_id = ?
            ORDER BY distance_km ASC
            """,
            (activity_id,),
        )
        return [dict(row) for row in await cursor.fetchall()]

    async def get_personal_bests(self) -> dict[str, Any]:
        """Get personal best records."""
        # Longest run
        longest = await self.db.execute(
            "SELECT * FROM running_activities ORDER BY distance_km DESC LIMIT 1"
        )
        longest_row = await longest.fetchone()

        # Fastest pace (best time per km)
        fastest = await self.db.execute(
            """SELECT *
               FROM running_activities
               WHERE distance_km > 0
               ORDER BY (CAST(duration_seconds AS REAL) / distance_km) ASC
               LIMIT 1"""
        )
        fastest_row = await fastest.fetchone()

        return {
            "longest_run": running_from_db(RunningActivityInDB(**dict(longest_row)))
            if longest_row
            else None,
            "fastest_pace": running_from_db(RunningActivityInDB(**dict(fastest_row)))
            if fastest_row
            else None,
        }
