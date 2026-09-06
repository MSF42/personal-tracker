"""Search-index maintenance helpers.

These are invoked from the mutation paths of individual repositories (tasks,
habits, exercises, workout routines). Keeping the logic in one module means
every domain sees the same insert/delete behaviour and there's a single place
to look when a kind needs to be added or removed from the unified
``search_index`` FTS5 table.
"""

from __future__ import annotations

from aiosqlite import Connection


async def _replace_index_row(
    db: Connection,
    kind: str,
    entity_id: int,
    title: str,
    body: str,
) -> None:
    await db.execute(
        "DELETE FROM search_index WHERE kind = ? AND entity_id = ?",
        (kind, entity_id),
    )
    await db.execute(
        "INSERT INTO search_index (kind, entity_id, parent_id, title, body) "
        "VALUES (?, ?, NULL, ?, ?)",
        (kind, entity_id, title, body),
    )


async def index_task(db: Connection, task_id: int, title: str, description: str | None) -> None:
    body = f"{title}\n{description or ''}"
    await _replace_index_row(db, "task", task_id, title, body)


async def index_habit(db: Connection, habit_id: int, name: str, description: str | None) -> None:
    body = f"{name}\n{description or ''}"
    await _replace_index_row(db, "habit", habit_id, name, body)


async def index_exercise(
    db: Connection, exercise_id: int, name: str, description: str | None
) -> None:
    body = f"{name}\n{description or ''}"
    await _replace_index_row(db, "exercise", exercise_id, name, body)


async def index_routine(
    db: Connection, routine_id: int, name: str, description: str | None
) -> None:
    body = f"{name}\n{description or ''}"
    await _replace_index_row(db, "routine", routine_id, name, body)


async def remove_from_index(db: Connection, kind: str, entity_id: int) -> None:
    await db.execute(
        "DELETE FROM search_index WHERE kind = ? AND entity_id = ?",
        (kind, entity_id),
    )
