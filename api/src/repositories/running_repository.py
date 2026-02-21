from datetime import datetime, timezone

from aiosqlite import Connection

from src.models.running import (
    CreateRunningActivityRequest,
    RunningActivityInDB,
    RunningActivityResponse,
    UpdateRunningActivityRequest,
    running_from_db,
)
from src.repositories.utils import execute_update


class SQLiteRunningRepository:
    def __init__(self, db: Connection):
        self.db = db

    async def create(self, activity: CreateRunningActivityRequest) -> RunningActivityResponse:
        now = datetime.now(timezone.utc).isoformat()

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

        return await self.find_by_id(cursor.lastrowid)

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

    async def get_stats_by_month(self, year: int) -> list[dict]:
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

    async def create_with_gpx(
        self,
        date: str,
        distance_km: float,
        duration_seconds: int,
        notes: str | None,
        title: str | None = None,
    ) -> RunningActivityResponse:
        now = datetime.now(timezone.utc).isoformat()
        cursor = await self.db.execute(
            """
            INSERT INTO running_activities (date, duration_seconds, distance_km, notes, has_gpx,
                                            title, created_at, updated_at)
            VALUES (?, ?, ?, ?, 1, ?, ?, ?)
            """,
            (date, duration_seconds, distance_km, notes, title, now, now),
        )
        await self.db.commit()
        return await self.find_by_id(cursor.lastrowid)

    async def save_segments(self, activity_id: int, segments: list[dict]) -> list[dict]:
        saved = []
        for seg in segments:
            cursor = await self.db.execute(
                """
                INSERT INTO gpx_segments (running_activity_id, segment_name, distance_km,
                                          duration_seconds, pace, pace_formatted)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    activity_id,
                    seg["name"],
                    seg["distance_km"],
                    seg["duration_seconds"],
                    seg["pace"],
                    seg["pace_formatted"],
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
                }
            )
        await self.db.commit()
        return saved

    async def get_segments(self, activity_id: int) -> list[dict]:
        cursor = await self.db.execute(
            """
            SELECT id, segment_name, distance_km, duration_seconds, pace, pace_formatted
            FROM gpx_segments
            WHERE running_activity_id = ?
            ORDER BY distance_km ASC
            """,
            (activity_id,),
        )
        return [dict(row) for row in await cursor.fetchall()]

    async def get_personal_bests(self) -> dict:
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
