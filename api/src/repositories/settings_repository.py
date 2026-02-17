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
