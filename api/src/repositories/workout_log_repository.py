from datetime import datetime, timezone

from aiosqlite import Connection


class SQLiteWorkoutLogRepository:
    def __init__(self, db: Connection):
        self.db = db

    async def create(self, routine_id: int, date: str, notes: str | None = None) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        cursor = await self.db.execute(
            "INSERT INTO workout_logs (routine_id, date, notes, created_at) VALUES (?, ?, ?, ?)",
            (routine_id, date, notes, now),
        )
        await self.db.commit()
        return {"id": cursor.lastrowid, "routine_id": routine_id, "date": date, "notes": notes}

    async def log_set(
        self,
        workout_log_id: int,
        exercise_id: int,
        set_number: int,
        reps: int,
        weight: float | None = None,
    ) -> dict:
        await self.db.execute(
            "INSERT INTO set_logs (workout_log_id, exercise_id, set_number, reps, weight) VALUES (?, ?, ?, ?, ?)",
            (workout_log_id, exercise_id, set_number, reps, weight),
        )
        await self.db.commit()
        return {
            "workout_log_id": workout_log_id,
            "exercise_id": exercise_id,
            "set_number": set_number,
            "reps": reps,
            "weight": weight,
        }

    async def get_workout_with_sets(self, workout_log_id: int) -> dict | None:
        # Get workout log
        cursor = await self.db.execute("SELECT * FROM workout_logs WHERE id = ?", (workout_log_id,))
        workout = await cursor.fetchone()
        if not workout:
            return None

        # Get sets
        sets_cursor = await self.db.execute(
            """SELECT sl.*, e.name as exercise_name
               FROM set_logs sl
                        JOIN exercises e ON sl.exercise_id = e.id
               WHERE sl.workout_log_id = ?
               ORDER BY sl.exercise_id, sl.set_number""",
            (workout_log_id,),
        )
        sets = [dict(row) for row in await sets_cursor.fetchall()]

        return {**dict(workout), "sets": sets}

    async def find_all(self) -> list[dict]:
        """Get all workout logs."""
        cursor = await self.db.execute(
            """SELECT wl.*, wr.name as routine_name
               FROM workout_logs wl
               JOIN workout_routines wr ON wl.routine_id = wr.id
               ORDER BY wl.date DESC"""
        )
        return [dict(row) for row in await cursor.fetchall()]

    async def get_exercise_history(self, exercise_id: int) -> list[dict]:
        """Get history of a specific exercise across all workout logs."""
        cursor = await self.db.execute(
            """SELECT sl.set_number, sl.reps, sl.weight,
                      wl.id as workout_log_id, wl.date,
                      wr.name as routine_name
               FROM set_logs sl
               JOIN workout_logs wl ON sl.workout_log_id = wl.id
               JOIN workout_routines wr ON wl.routine_id = wr.id
               WHERE sl.exercise_id = ?
               ORDER BY wl.date DESC, sl.set_number ASC""",
            (exercise_id,),
        )
        return [dict(row) for row in await cursor.fetchall()]

    async def get_exercise_prs(self) -> dict[int, float]:
        cursor = await self.db.execute(
            "SELECT exercise_id, MAX(weight) AS pr_weight "
            "FROM set_logs WHERE weight IS NOT NULL AND weight > 0 "
            "GROUP BY exercise_id"
        )
        return {row["exercise_id"]: row["pr_weight"] for row in await cursor.fetchall()}

    async def get_exercise_last_performed(self) -> dict[int, str]:
        """Get the most recent workout date for each exercise."""
        cursor = await self.db.execute(
            """SELECT sl.exercise_id, MAX(wl.date) as last_date
               FROM set_logs sl
               JOIN workout_logs wl ON sl.workout_log_id = wl.id
               GROUP BY sl.exercise_id"""
        )
        return {row["exercise_id"]: row["last_date"] for row in await cursor.fetchall()}

    async def find_by_routine(self, routine_id: int) -> list[dict]:
        """Get all workout logs for a routine."""
        cursor = await self.db.execute(
            "SELECT * FROM workout_logs WHERE routine_id = ? ORDER BY date DESC",
            (routine_id,),
        )
        return [dict(row) for row in await cursor.fetchall()]

    async def delete(self, workout_log_id: int) -> bool:
        cursor = await self.db.execute("DELETE FROM workout_logs WHERE id = ?", (workout_log_id,))
        await self.db.commit()
        return cursor.rowcount > 0

    async def update(
        self, workout_log_id: int, date: str | None = None, notes: str | None = None
    ) -> dict | None:
        existing = await self.db.execute(
            "SELECT * FROM workout_logs WHERE id = ?", (workout_log_id,)
        )
        row = await existing.fetchone()
        if not row:
            return None

        updates = {}
        if date is not None:
            updates["date"] = date
        if notes is not None:
            updates["notes"] = notes

        if updates:
            # Only "date" and "notes" are updatable — explicit safe columns, no dynamic column names
            allowed = {"date", "notes"}
            filtered = {k: v for k, v in updates.items() if k in allowed}
            if filtered:
                set_clause = ", ".join(f"{key} = ?" for key in filtered)
                values = list(filtered.values()) + [workout_log_id]
                await self.db.execute(
                    f"UPDATE workout_logs SET {set_clause} WHERE id = ?",  # noqa: S608
                    values,
                )
                await self.db.commit()

        cursor = await self.db.execute(
            """SELECT wl.*, wr.name as routine_name
               FROM workout_logs wl
               JOIN workout_routines wr ON wl.routine_id = wr.id
               WHERE wl.id = ?""",
            (workout_log_id,),
        )
        updated = await cursor.fetchone()
        return dict(updated) if updated else None
