from datetime import datetime, timezone

from aiosqlite import Connection

_ALLOWED_TABLES = frozenset({
    "tasks",
    "running_activities",
    "exercises",
    "workout_routines",
    "measurements",
    "measurement_entries",
    "notes",
    "habits",
})


def _validate_table(table: str) -> None:
    if table not in _ALLOWED_TABLES:
        raise ValueError(f"Table '{table}' is not permitted for dynamic update")


async def execute_update(
    db: Connection, table: str, update_data: dict[str, object], id_val: int
) -> None:
    """Execute a dynamic UPDATE statement, stamping updated_at automatically."""
    _validate_table(table)
    payload = {**update_data, "updated_at": datetime.now(timezone.utc).isoformat()}
    set_clause = ", ".join(f"{key} = ?" for key in payload)
    values = list(payload.values()) + [id_val]
    await db.execute(f"UPDATE {table} SET {set_clause} WHERE id = ?", values)  # noqa: S608
    await db.commit()
