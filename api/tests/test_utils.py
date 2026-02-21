from datetime import datetime, timezone

import aiosqlite
import pytest

from src.repositories.utils import execute_update


async def test_execute_update_updates_field_and_stamps_updated_at():
    async with aiosqlite.connect(":memory:") as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            "CREATE TABLE tasks (id INTEGER PRIMARY KEY, name TEXT, updated_at TEXT)"
        )
        await db.execute("INSERT INTO tasks (name, updated_at) VALUES ('old', '2020-01-01')")
        await db.commit()

        before = datetime.now(timezone.utc)
        update_data = {"name": "new"}
        await execute_update(db, "tasks", update_data, 1)
        after = datetime.now(timezone.utc)

        cursor = await db.execute("SELECT * FROM tasks WHERE id = 1")
        row = dict(await cursor.fetchone())

        assert row["name"] == "new"
        updated_at = datetime.fromisoformat(row["updated_at"])
        assert before <= updated_at <= after


async def test_execute_update_handles_multiple_fields():
    async with aiosqlite.connect(":memory:") as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            "CREATE TABLE tasks (id INTEGER PRIMARY KEY, name TEXT, value INTEGER, updated_at TEXT)"
        )
        await db.execute(
            "INSERT INTO tasks (name, value, updated_at) VALUES ('old', 1, '2020-01-01')"
        )
        await db.commit()

        await execute_update(db, "tasks", {"name": "new", "value": 42}, 1)

        cursor = await db.execute("SELECT * FROM tasks WHERE id = 1")
        row = dict(await cursor.fetchone())

        assert row["name"] == "new"
        assert row["value"] == 42


async def test_execute_update_does_not_mutate_caller_dict():
    async with aiosqlite.connect(":memory:") as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            "CREATE TABLE tasks (id INTEGER PRIMARY KEY, name TEXT, updated_at TEXT)"
        )
        await db.execute("INSERT INTO tasks (name, updated_at) VALUES ('orig', '2020-01-01')")
        await db.commit()

        update_data = {"name": "new"}
        original_keys = set(update_data.keys())
        await execute_update(db, "tasks", update_data, 1)

        assert set(update_data.keys()) == original_keys, "execute_update must not mutate caller's dict"


async def test_execute_update_rejects_invalid_table():
    async with aiosqlite.connect(":memory:") as db:
        with pytest.raises(ValueError, match="not permitted"):
            await execute_update(db, "unknown_table", {"name": "x"}, 1)
