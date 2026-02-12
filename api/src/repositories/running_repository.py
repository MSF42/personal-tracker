from datetime import datetime, timezone

from aiosqlite import Connection

from src.models.running import (
    CreateRunningActivityRequest,
    RunningActivityInDB,
    RunningActivityResponse,
    UpdateRunningActivityRequest,
    running_from_db,
)


class SQLiteRunningRepository:
    def __init__(self, db: Connection):
        self.db = db

    async def create(self, activity: CreateRunningActivityRequest) -> RunningActivityResponse:
        now = datetime.now(timezone.utc).isoformat()

        cursor = await self.db.execute(
            """
            INSERT INTO running_activities (date, duration_seconds, distance_km, notes, created_at,
                                            updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                activity.date,
                activity.duration_seconds,
                activity.distance_km,
                activity.notes,
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

        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        set_clause = ", ".join(f"{key} = ?" for key in update_data.keys())
        values = list(update_data.values()) + [activity_id]

        await self.db.execute(
            f"UPDATE running_activities SET {set_clause} WHERE id = ?",
            values,
        )
        await self.db.commit()

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
            "longest_run": dict(longest_row) if longest_row else None,
            "fastest_pace": dict(fastest_row) if fastest_row else None,
        }
