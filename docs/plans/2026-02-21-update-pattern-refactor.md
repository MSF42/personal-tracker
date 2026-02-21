# Update Pattern Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extract the duplicated 5-line dynamic UPDATE SQL block from all six repositories into a single `execute_update()` helper function in `api/src/repositories/utils.py`.

**Architecture:** A new module-level async function accepts `(db, table, update_data, id_val)`, stamps `updated_at`, builds the SET clause, and executes + commits. Each repository imports and calls it instead of repeating the 5-line block inline. No inheritance hierarchy is introduced.

**Tech Stack:** Python 3.14, aiosqlite, pytest (asyncio_mode="auto")

**Test runner:** `/Users/stevefurches/Documents/Steve/personal-tracker/api/.venv/bin/py.test`
**Linter:** `/Users/stevefurches/Documents/Steve/personal-tracker/api/.venv/bin/ruff check api/src/repositories/utils.py`
**Working directory for all commands:** `/Users/stevefurches/Documents/Steve/personal-tracker/api`

> **Note:** The existing integration test suite fails at app startup due to a missing `data/uploads` directory (pre-existing environment issue unrelated to this refactor). Task 1 adds a standalone unit test for `execute_update` that uses an in-memory SQLite database directly — no app startup required.

---

### Task 1: Create `utils.py` with `execute_update` and its unit test

**Files:**
- Create: `api/src/repositories/utils.py`
- Create: `api/tests/test_utils.py`

---

**Step 1: Write the failing test**

Create `api/tests/test_utils.py`:

```python
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
```

**Step 2: Run test to verify it fails**

```bash
/Users/stevefurches/Documents/Steve/personal-tracker/api/.venv/bin/py.test \
  /Users/stevefurches/Documents/Steve/personal-tracker/api/tests/test_utils.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.repositories.utils'`

---

**Step 3: Create `api/src/repositories/utils.py`**

```python
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
```

**Step 4: Run test to verify it passes**

```bash
/Users/stevefurches/Documents/Steve/personal-tracker/api/.venv/bin/py.test \
  /Users/stevefurches/Documents/Steve/personal-tracker/api/tests/test_utils.py -v
```

Expected: 2 tests PASS

**Step 5: Lint**

```bash
/Users/stevefurches/Documents/Steve/personal-tracker/api/.venv/bin/ruff check \
  /Users/stevefurches/Documents/Steve/personal-tracker/api/src/repositories/utils.py \
  /Users/stevefurches/Documents/Steve/personal-tracker/api/tests/test_utils.py
```

Expected: No errors

**Step 6: Commit**

```bash
cd /Users/stevefurches/Documents/Steve/personal-tracker && \
git add api/src/repositories/utils.py api/tests/test_utils.py && \
git commit -m "feat: add execute_update helper to eliminate duplicated update SQL pattern"
```

---

### Task 2: Update `running_repository.py`

**Files:**
- Modify: `api/src/repositories/running_repository.py`

The `update()` method currently (lines 71–94) ends with:

```python
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        set_clause = ", ".join(f"{key} = ?" for key in update_data.keys())
        values = list(update_data.values()) + [activity_id]

        await self.db.execute(
            f"UPDATE running_activities SET {set_clause} WHERE id = ?",
            values,
        )
        await self.db.commit()

        return await self.find_by_id(activity_id)
```

**Step 1: Add import at top of file**

Add to the existing imports block (after `from aiosqlite import Connection`):

```python
from src.repositories.utils import execute_update
```

**Step 2: Replace the duplicated block in `update()`**

Replace the 10-line block above with:

```python
        await execute_update(self.db, "running_activities", update_data, activity_id)
        return await self.find_by_id(activity_id)
```

Also remove the now-unused `datetime` import if it's no longer used elsewhere in the file. Check: `datetime` is still used in `create()` and `create_with_gpx()` for `now = datetime.now(...)` — so keep it.

**Step 3: Lint**

```bash
/Users/stevefurches/Documents/Steve/personal-tracker/api/.venv/bin/ruff check \
  /Users/stevefurches/Documents/Steve/personal-tracker/api/src/repositories/running_repository.py
```

Expected: No errors

**Step 4: Commit**

```bash
cd /Users/stevefurches/Documents/Steve/personal-tracker && \
git add api/src/repositories/running_repository.py && \
git commit -m "refactor: use execute_update helper in running_repository"
```

---

### Task 3: Update `exercise_repository.py`

**Files:**
- Modify: `api/src/repositories/exercise_repository.py`

The `update()` method currently ends with:

```python
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        set_clause = ", ".join(f"{key} = ?" for key in update_data.keys())
        values = list(update_data.values()) + [exercise_id]
        await self.db.execute(
            f"UPDATE exercises SET {set_clause} WHERE id = ?",
            values,
        )
        await self.db.commit()

        return await self.find_by_id(exercise_id)
```

**Step 1: Add import**

```python
from src.repositories.utils import execute_update
```

**Step 2: Replace the block**

```python
        await execute_update(self.db, "exercises", update_data, exercise_id)
        return await self.find_by_id(exercise_id)
```

Check: `datetime` is still used in `create()` — keep the import.

**Step 3: Lint**

```bash
/Users/stevefurches/Documents/Steve/personal-tracker/api/.venv/bin/ruff check \
  /Users/stevefurches/Documents/Steve/personal-tracker/api/src/repositories/exercise_repository.py
```

Expected: No errors

**Step 4: Commit**

```bash
cd /Users/stevefurches/Documents/Steve/personal-tracker && \
git add api/src/repositories/exercise_repository.py && \
git commit -m "refactor: use execute_update helper in exercise_repository"
```

---

### Task 4: Update `note_repository.py`

**Files:**
- Modify: `api/src/repositories/note_repository.py`

The `update()` method currently ends with:

```python
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        set_clause = ", ".join(f"{key} = ?" for key in update_data)
        values = list(update_data.values()) + [note_id]

        await self.db.execute(
            f"UPDATE notes SET {set_clause} WHERE id = ?",
            values,
        )
        await self.db.commit()
        return await self.find_by_id(note_id)
```

**Step 1: Add import**

```python
from src.repositories.utils import execute_update
```

**Step 2: Replace the block**

```python
        await execute_update(self.db, "notes", update_data, note_id)
        return await self.find_by_id(note_id)
```

Check: `datetime` is still used in `create()` and `move()` — keep the import.

**Step 3: Lint**

```bash
/Users/stevefurches/Documents/Steve/personal-tracker/api/.venv/bin/ruff check \
  /Users/stevefurches/Documents/Steve/personal-tracker/api/src/repositories/note_repository.py
```

Expected: No errors

**Step 4: Commit**

```bash
cd /Users/stevefurches/Documents/Steve/personal-tracker && \
git add api/src/repositories/note_repository.py && \
git commit -m "refactor: use execute_update helper in note_repository"
```

---

### Task 5: Update `workout_routine_repository.py`

**Files:**
- Modify: `api/src/repositories/workout_routine_repository.py`

The `update()` method currently ends with:

```python
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        set_clause = ", ".join(f"{key} = ?" for key in update_data.keys())
        values = list(update_data.values()) + [workout_routine_id]

        await self.db.execute(
            f"UPDATE workout_routines SET {set_clause} WHERE id = ?",
            values,
        )
        await self.db.commit()

        return await self.find_by_id(workout_routine_id)
```

**Step 1: Add import**

```python
from src.repositories.utils import execute_update
```

**Step 2: Replace the block**

```python
        await execute_update(self.db, "workout_routines", update_data, workout_routine_id)
        return await self.find_by_id(workout_routine_id)
```

Check: `datetime` is still used in `create()` — keep the import.

**Step 3: Lint**

```bash
/Users/stevefurches/Documents/Steve/personal-tracker/api/.venv/bin/ruff check \
  /Users/stevefurches/Documents/Steve/personal-tracker/api/src/repositories/workout_routine_repository.py
```

Expected: No errors

**Step 4: Commit**

```bash
cd /Users/stevefurches/Documents/Steve/personal-tracker && \
git add api/src/repositories/workout_routine_repository.py && \
git commit -m "refactor: use execute_update helper in workout_routine_repository"
```

---

### Task 6: Update `measurement_repository.py` (two update methods)

**Files:**
- Modify: `api/src/repositories/measurement_repository.py`

This repo has two update methods: `update_measurement()` and `update_entry()`. Both end with the same duplicated block, targeting different tables and id columns.

**`update_measurement()` currently ends with:**

```python
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        set_clause = ", ".join(f"{key} = ?" for key in update_data.keys())
        values = list(update_data.values()) + [measurement_id]

        await self.db.execute(
            f"UPDATE measurements SET {set_clause} WHERE id = ?",
            values,
        )
        await self.db.commit()

        return await self.find_measurement_by_id(measurement_id)
```

**`update_entry()` currently ends with:**

```python
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        set_clause = ", ".join(f"{key} = ?" for key in update_data.keys())
        values = list(update_data.values()) + [entry_id]

        await self.db.execute(
            f"UPDATE measurement_entries SET {set_clause} WHERE id = ?",
            values,
        )
        await self.db.commit()

        return await self.find_entry_by_id(entry_id)
```

**Step 1: Add import**

```python
from src.repositories.utils import execute_update
```

**Step 2: Replace block in `update_measurement()`**

```python
        await execute_update(self.db, "measurements", update_data, measurement_id)
        return await self.find_measurement_by_id(measurement_id)
```

**Step 3: Replace block in `update_entry()`**

```python
        await execute_update(self.db, "measurement_entries", update_data, entry_id)
        return await self.find_entry_by_id(entry_id)
```

Check: `datetime` is still used in `create_measurement()`, `create_entry()` — keep the import.

**Step 4: Lint**

```bash
/Users/stevefurches/Documents/Steve/personal-tracker/api/.venv/bin/ruff check \
  /Users/stevefurches/Documents/Steve/personal-tracker/api/src/repositories/measurement_repository.py
```

Expected: No errors

**Step 5: Commit**

```bash
cd /Users/stevefurches/Documents/Steve/personal-tracker && \
git add api/src/repositories/measurement_repository.py && \
git commit -m "refactor: use execute_update helper in measurement_repository"
```

---

### Task 7: Update `task_repository.py`

**Files:**
- Modify: `api/src/repositories/task_repository.py`

This is the most complex repo. The `update()` method has domain-specific business logic (recurrence calculation, bool→int, enum→value, list serialization) that all stays inline. Only the final SQL block is replaced.

The current `update()` method ends with (lines 120–133):

```python
        # Always update updated_at
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Build dynamic SQL
        set_clause = ", ".join(f"{key} = ?" for key in update_data.keys())
        values = list(update_data.values()) + [task_id]

        await self.db.execute(
            f"UPDATE tasks SET {set_clause} WHERE id = ?",
            values,
        )
        await self.db.commit()

        return await self.find_by_id(task_id)
```

**Step 1: Add import**

```python
from src.repositories.utils import execute_update
```

**Step 2: Replace the block**

Remove the comment `# Always update updated_at` and `# Build dynamic SQL` along with their code, replacing with:

```python
        await execute_update(self.db, "tasks", update_data, task_id)
        return await self.find_by_id(task_id)
```

The `datetime` import is still used earlier in `update()` for the `now` variable in `create()` — keep it.

**Step 3: Lint**

```bash
/Users/stevefurches/Documents/Steve/personal-tracker/api/.venv/bin/ruff check \
  /Users/stevefurches/Documents/Steve/personal-tracker/api/src/repositories/task_repository.py
```

Expected: No errors

**Step 4: Run all unit tests to confirm nothing broken**

```bash
/Users/stevefurches/Documents/Steve/personal-tracker/api/.venv/bin/py.test \
  /Users/stevefurches/Documents/Steve/personal-tracker/api/tests/test_utils.py -v
```

Expected: 2 tests PASS

**Step 5: Commit**

```bash
cd /Users/stevefurches/Documents/Steve/personal-tracker && \
git add api/src/repositories/task_repository.py && \
git commit -m "refactor: use execute_update helper in task_repository"
```

---

## Done

After all 7 tasks, the duplicated 5-line dynamic UPDATE block has been eliminated from all repositories. A single `execute_update()` function is the authoritative source for how updates are executed — any future change (audit logging, timestamp strategy, etc.) needs to happen in exactly one place.
