from datetime import datetime, timezone

from aiosqlite import Connection


async def execute_update(
    db: Connection, table: str, update_data: dict, id_val: int
) -> None:
    """Execute a dynamic UPDATE statement, stamping updated_at automatically.

    Mutates update_data in place to add the updated_at timestamp.
    Caller is responsible for domain-specific conversions (bool->int, enum->value, etc.)
    before calling this function.
    """
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    set_clause = ", ".join(f"{key} = ?" for key in update_data)
    values = list(update_data.values()) + [id_val]
    await db.execute(f"UPDATE {table} SET {set_clause} WHERE id = ?", values)  # noqa: S608
    await db.commit()
