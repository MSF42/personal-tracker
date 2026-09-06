from collections.abc import Mapping
from datetime import UTC, datetime

from aiosqlite import Connection

_ALLOWED_TABLES = frozenset(
    {
        "tasks",
        "running_activities",
        "exercises",
        "workout_routines",
        "measurements",
        "countdowns",
        "measurement_entries",
        "habits",
    }
)


def require_row_id(last_row_id: int | None) -> int:
    """Narrow ``cursor.lastrowid`` to ``int``.

    SQLite always sets it after a successful INSERT, but the type is
    ``int | None`` because it is also readable before one.
    """
    if last_row_id is None:
        raise RuntimeError("INSERT did not produce a row id")
    return last_row_id


def require_found[T](value: T | None, what: str) -> T:
    """Narrow a just-created record's lookup result to non-None."""
    if value is None:
        raise RuntimeError(f"{what} could not be read back after being written")
    return value


def _validate_table(table: str) -> None:
    if table not in _ALLOWED_TABLES:
        raise ValueError(f"Table '{table}' is not permitted for dynamic update")


async def execute_update(
    db: Connection, table: str, update_data: Mapping[str, object], id_val: int
) -> None:
    """Execute a dynamic UPDATE statement, stamping updated_at automatically."""
    _validate_table(table)
    payload = {**update_data, "updated_at": datetime.now(UTC).isoformat()}
    set_clause = ", ".join(f"{key} = ?" for key in payload)
    values = list(payload.values()) + [id_val]
    await db.execute(f"UPDATE {table} SET {set_clause} WHERE id = ?", values)  # noqa: S608
    await db.commit()
