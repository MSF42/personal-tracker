from datetime import UTC, datetime

from aiosqlite import Connection

from src.models.countdown import CountdownResponse, CreateCountdownRequest, UpdateCountdownRequest
from src.repositories.utils import execute_update, require_found, require_row_id


class SQLiteCountdownRepository:
    def __init__(self, db: Connection):
        self.db = db

    async def create(self, data: CreateCountdownRequest) -> CountdownResponse:
        now = datetime.now(UTC).isoformat()
        cursor = await self.db.execute(
            "INSERT INTO countdowns (title, date, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (data.title, data.date, now, now),
        )
        await self.db.commit()
        return require_found(await self.find_by_id(require_row_id(cursor.lastrowid)), "Countdown")

    async def find_by_id(self, countdown_id: int) -> CountdownResponse | None:
        cursor = await self.db.execute("SELECT * FROM countdowns WHERE id = ?", (countdown_id,))
        row = await cursor.fetchone()
        return CountdownResponse(**dict(row)) if row is not None else None

    async def find_all(self) -> list[CountdownResponse]:
        cursor = await self.db.execute("SELECT * FROM countdowns ORDER BY date ASC, id ASC")
        return [CountdownResponse(**dict(row)) for row in await cursor.fetchall()]

    async def update(
        self, countdown_id: int, data: UpdateCountdownRequest
    ) -> CountdownResponse | None:
        existing = await self.find_by_id(countdown_id)
        if existing is None:
            return None
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return existing
        await execute_update(self.db, "countdowns", update_data, countdown_id)
        return await self.find_by_id(countdown_id)

    async def delete(self, countdown_id: int) -> bool:
        cursor = await self.db.execute("DELETE FROM countdowns WHERE id = ?", (countdown_id,))
        await self.db.commit()
        return cursor.rowcount > 0
