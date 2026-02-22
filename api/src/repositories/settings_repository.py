from aiosqlite import Connection


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

    async def delete_all_data(self) -> None:
        tables = [
            "set_logs",
            "workout_logs",
            "gpx_segments",
            "routine_exercises",
            "workout_routines",
            "exercises",
            "running_activities",
            "tasks",
            "notes",
            "measurement_entries",
            "measurements",
            "user_settings",
        ]
        for table in tables:
            await self.db.execute(f"DELETE FROM {table}")  # noqa: S608
        await self.db.commit()
