from aiosqlite import Connection

# Tables holding things the user created; settings rows (units, theme) don't
# count, since a brand-new install already has some.
USER_DATA_TABLES = (
    "tasks",
    "habits",
    "running_activities",
    "exercises",
    "workout_routines",
    "workout_logs",
    "measurements",
    "countdowns",
)


class SQLiteSettingsRepository:
    def __init__(self, db: Connection):
        self.db = db

    async def get(self, key: str) -> str | None:
        cursor = await self.db.execute("SELECT value FROM user_settings WHERE key = ?", (key,))
        row = await cursor.fetchone()
        return row["value"] if row else None

    async def set(self, key: str, value: str) -> None:
        await self.db.execute(
            "INSERT INTO user_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = ?",
            (key, value, value),
        )
        await self.db.commit()

    async def delete(self, key: str) -> None:
        await self.db.execute("DELETE FROM user_settings WHERE key = ?", (key,))
        await self.db.commit()

    async def has_user_data(self) -> bool:
        """Whether any user-entered records exist (unit preferences aside)."""
        for table in USER_DATA_TABLES:
            cursor = await self.db.execute(f"SELECT 1 FROM {table} LIMIT 1")  # noqa: S608
            if await cursor.fetchone():
                return True
        return False

    async def delete_all_data(self) -> None:
        tables = [
            "habit_completions",
            "habits",
            "search_index",
            "set_logs",
            "workout_logs",
            "run_samples",
            "run_laps",
            "gpx_segments",
            "routine_exercises",
            "workout_routines",
            "exercises",
            "running_activities",
            "tasks",
            "measurement_entries",
            "measurements",
            "countdowns",
            "user_settings",
        ]
        for table in tables:
            await self.db.execute(f"DELETE FROM {table}")  # noqa: S608
        await self.db.commit()
