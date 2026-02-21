from datetime import datetime, timezone

import aiosqlite

from src.repositories.utils import execute_update


async def test_execute_update_updates_field_and_stamps_updated_at():
    async with aiosqlite.connect(":memory:") as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            "CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT, updated_at TEXT)"
        )
        await db.execute("INSERT INTO items (name, updated_at) VALUES ('old', '2020-01-01')")
        await db.commit()

        before = datetime.now(timezone.utc)
        update_data = {"name": "new"}
        await execute_update(db, "items", update_data, 1)
        after = datetime.now(timezone.utc)

        cursor = await db.execute("SELECT * FROM items WHERE id = 1")
        row = dict(await cursor.fetchone())

        assert row["name"] == "new"
        updated_at = datetime.fromisoformat(row["updated_at"])
        assert before <= updated_at <= after


async def test_execute_update_handles_multiple_fields():
    async with aiosqlite.connect(":memory:") as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            "CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT, value INTEGER, updated_at TEXT)"
        )
        await db.execute(
            "INSERT INTO items (name, value, updated_at) VALUES ('old', 1, '2020-01-01')"
        )
        await db.commit()

        await execute_update(db, "items", {"name": "new", "value": 42}, 1)

        cursor = await db.execute("SELECT * FROM items WHERE id = 1")
        row = dict(await cursor.fetchone())

        assert row["name"] == "new"
        assert row["value"] == 42
