from datetime import datetime, timezone

from aiosqlite import Connection

from src.models.habit import (
    HabitCreate,
    HabitInDB,
    HabitResponse,
    HabitUpdate,
    habit_from_db,
)
from src.repositories.utils import execute_update


class SQLiteHabitRepository:
    def __init__(self, db: Connection):
        self.db = db

    def _today(self) -> str:
        return datetime.now(timezone.utc).date().isoformat()

    async def _fetch_completions(self, habit_ids: list[int]) -> dict[int, list[str]]:
        if not habit_ids:
            return {}
        placeholders = ",".join("?" for _ in habit_ids)
        cursor = await self.db.execute(
            f"SELECT habit_id, date FROM habit_completions WHERE habit_id IN ({placeholders}) ORDER BY date DESC",  # noqa: S608
            habit_ids,
        )
        rows = await cursor.fetchall()
        result: dict[int, list[str]] = {hid: [] for hid in habit_ids}
        for row in rows:
            result[row["habit_id"]].append(row["date"])
        return result

    async def find_all(self, include_archived: bool = False) -> list[HabitResponse]:
        query = "SELECT * FROM habits"
        if not include_archived:
            query += " WHERE archived = 0"
        query += " ORDER BY created_at ASC"
        cursor = await self.db.execute(query)
        rows = await cursor.fetchall()
        if not rows:
            return []
        habit_ids = [row["id"] for row in rows]
        completions = await self._fetch_completions(habit_ids)
        today = self._today()
        return [
            habit_from_db(HabitInDB(**dict(row)), completions.get(row["id"], []), today)
            for row in rows
        ]

    async def find_by_id(self, habit_id: int) -> HabitResponse | None:
        cursor = await self.db.execute("SELECT * FROM habits WHERE id = ?", (habit_id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        completions = await self._fetch_completions([habit_id])
        today = self._today()
        return habit_from_db(HabitInDB(**dict(row)), completions.get(habit_id, []), today)

    async def create(self, data: HabitCreate) -> HabitResponse:
        now = datetime.now(timezone.utc).isoformat()
        frequency_days_str = (
            ",".join(str(d) for d in data.frequency_days) if data.frequency_days else None
        )
        cursor = await self.db.execute(
            """
            INSERT INTO habits (name, description, frequency, frequency_days, color,
                                archived, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 0, ?, ?)
            """,
            (
                data.name,
                data.description,
                data.frequency,
                frequency_days_str,
                data.color,
                now,
                now,
            ),
        )
        await self.db.commit()
        return await self.find_by_id(cursor.lastrowid)

    async def update(self, habit_id: int, data: HabitUpdate) -> HabitResponse | None:
        existing = await self.find_by_id(habit_id)
        if existing is None:
            return None

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return existing

        if "archived" in update_data:
            update_data["archived"] = 1 if update_data["archived"] else 0

        if "frequency_days" in update_data:
            if update_data["frequency_days"] is not None:
                update_data["frequency_days"] = ",".join(
                    str(d) for d in update_data["frequency_days"]
                )
            else:
                update_data["frequency_days"] = None

        await execute_update(self.db, "habits", update_data, habit_id)
        return await self.find_by_id(habit_id)

    async def delete(self, habit_id: int) -> bool:
        cursor = await self.db.execute("DELETE FROM habits WHERE id = ?", (habit_id,))
        await self.db.commit()
        return cursor.rowcount > 0

    async def toggle_completion(self, habit_id: int, date_str: str) -> HabitResponse | None:
        existing = await self.find_by_id(habit_id)
        if existing is None:
            return None

        now = datetime.now(timezone.utc).isoformat()
        if date_str in (existing.completed_today and [date_str] or []):
            # Check directly in DB
            pass

        check_cursor = await self.db.execute(
            "SELECT id FROM habit_completions WHERE habit_id = ? AND date = ?",
            (habit_id, date_str),
        )
        existing_completion = await check_cursor.fetchone()

        if existing_completion:
            await self.db.execute(
                "DELETE FROM habit_completions WHERE habit_id = ? AND date = ?",
                (habit_id, date_str),
            )
        else:
            await self.db.execute(
                "INSERT OR IGNORE INTO habit_completions (habit_id, date, created_at) VALUES (?, ?, ?)",
                (habit_id, date_str, now),
            )
        await self.db.commit()
        return await self.find_by_id(habit_id)
