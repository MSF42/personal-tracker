# Update Pattern Refactor Design

**Date:** 2026-02-21
**Status:** Approved

## Problem

Every repository in `api/src/repositories/` repeats the same 5-line block for dynamic UPDATE SQL:

```python
update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
set_clause = ", ".join(f"{key} = ?" for key in update_data.keys())
values = list(update_data.values()) + [id]
await self.db.execute(f"UPDATE {table} SET {set_clause} WHERE id = ?", values)
await self.db.commit()
```

This appears in `task_repository`, `running_repository`, `exercise_repository`,
`measurement_repository` (twice), `note_repository`, and `workout_routine_repository`.
Any change to the update pattern (e.g., audit logging, timestamp strategy) must be
made in six or more places.

## Chosen Approach: Module-level helper function (Approach A)

Extract the duplicated 5-line block into a standalone async function in a new
`api/src/repositories/utils.py` module. No inheritance hierarchy is introduced.

### New file: `api/src/repositories/utils.py`

```python
from datetime import datetime, timezone
from aiosqlite import Connection

async def execute_update(
    db: Connection, table: str, update_data: dict, id_val: int
) -> None:
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    set_clause = ", ".join(f"{key} = ?" for key in update_data)
    values = list(update_data.values()) + [id_val]
    await db.execute(f"UPDATE {table} SET {set_clause} WHERE id = ?", values)
    await db.commit()
```

### What each repo's `update()` becomes

Before:
```python
update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
set_clause = ", ".join(f"{key} = ?" for key in update_data.keys())
values = list(update_data.values()) + [activity_id]
await self.db.execute(
    f"UPDATE running_activities SET {set_clause} WHERE id = ?", values
)
await self.db.commit()
return await self.find_by_id(activity_id)
```

After:
```python
await execute_update(self.db, "running_activities", update_data, activity_id)
return await self.find_by_id(activity_id)
```

## What Stays Inline (Not Extracted)

- `find_by_id` existence check — explicit control flow per domain
- `model_dump(exclude_unset=True)` — domain awareness
- Domain-specific conversions (bool→int, enum→value, list serialization) — varies per repo
- Final `return await self.find_by_id(id)` — some repos use differently-named find
  methods (`find_measurement_by_id`, `find_entry_by_id`)

## Files Touched

| File | Change |
|------|--------|
| `api/src/repositories/utils.py` | New file with `execute_update` |
| `api/src/repositories/running_repository.py` | Use helper in `update()` |
| `api/src/repositories/exercise_repository.py` | Use helper in `update()` |
| `api/src/repositories/measurement_repository.py` | Use helper in `update_measurement()` and `update_entry()` |
| `api/src/repositories/note_repository.py` | Use helper in `update()` |
| `api/src/repositories/workout_routine_repository.py` | Use helper in `update()` |
| `api/src/repositories/task_repository.py` | Use helper in `update()` (recurrence logic stays inline) |

## Alternatives Considered

**B: Base repository class** — Adds inheritance hierarchy without enough benefit
over a simple function. Rejected.

**C: Full template method** — Over-engineered; requires callbacks for domain
conversions, making repos harder to read. Rejected (YAGNI).
