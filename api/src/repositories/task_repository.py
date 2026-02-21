from datetime import datetime, timezone

from aiosqlite import Connection

from src.models.task import (
    CreateTaskRequest,
    RepeatType,
    TaskInDB,
    TaskResponse,
    UpdateTaskRequest,
    task_from_db,
)
from src.repositories.utils import execute_update
from src.services.task_recurrence import calculate_next_due_date


class SQLiteTaskRepository:
    def __init__(self, db: Connection):
        self.db = db

    async def create(self, task: CreateTaskRequest) -> TaskResponse:
        now = datetime.now(timezone.utc).isoformat()

        repeat_days_str = (
            ",".join(str(d) for d in task.repeat_days) if task.repeat_days else None
        )

        cursor = await self.db.execute(
            """
            INSERT INTO tasks (title, description, category, due_date, completed,
                               repeat_type, repeat_interval, repeat_days,
                               created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task.title,
                task.description,
                task.category,
                task.due_date,
                1 if task.completed else 0,
                task.repeat_type.value if task.repeat_type else None,
                task.repeat_interval,
                repeat_days_str,
                now,
                now,
            ),
        )
        await self.db.commit()

        # Fetch and return the created task
        return await self.find_by_id(cursor.lastrowid)

    async def find_by_id(self, task_id: int) -> TaskResponse | None:
        cursor = await self.db.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,),
        )
        row = await cursor.fetchone()

        if row is None:
            return None

        # Convert row to dict (since we set row_factory = aiosqlite.Row)
        task_in_db = TaskInDB(**dict(row))
        return task_from_db(task_in_db)

    async def find_all(self) -> list[TaskResponse]:
        cursor = await self.db.execute("SELECT * FROM tasks ORDER BY created_at DESC")
        rows = await cursor.fetchall()

        return [task_from_db(TaskInDB(**dict(row))) for row in rows]

    async def delete(self, task_id: int) -> bool:
        cursor = await self.db.execute(
            "DELETE FROM tasks WHERE id = ?",
            (task_id,),
        )
        await self.db.commit()

        return cursor.rowcount > 0  # True if a row was deleted

    async def update(self, task_id: int, data: UpdateTaskRequest) -> TaskResponse | None:
        # First check if task exists
        existing = await self.find_by_id(task_id)
        if existing is None:
            return None

        # Get only the fields that were provided (not None/unset)
        update_data = data.model_dump(exclude_unset=True)

        # Handle recurrence: if completing a recurring task, calculate next due date
        if update_data.get("completed") is True and existing.repeat_type and existing.due_date:
            update_data["due_date"] = calculate_next_due_date(
                existing.due_date,
                RepeatType(existing.repeat_type),
                existing.repeat_interval or 1,
                existing.repeat_days,
            )
            update_data["completed"] = False  # Reset to incomplete for next occurrence

        if not update_data:
            return existing  # Nothing to update

        # Handle completed bool -> int conversion
        if "completed" in update_data:
            update_data["completed"] = 1 if update_data["completed"] else 0

        # Handle enum conversion
        if "repeat_type" in update_data and update_data["repeat_type"] is not None:
            update_data["repeat_type"] = update_data["repeat_type"].value

        # Serialize repeat_days list to comma-separated string
        if "repeat_days" in update_data:
            if update_data["repeat_days"] is not None:
                update_data["repeat_days"] = ",".join(
                    str(d) for d in update_data["repeat_days"]
                )
            else:
                update_data["repeat_days"] = None

        await execute_update(self.db, "tasks", update_data, task_id)
        return await self.find_by_id(task_id)

    async def find_with_filters(
        self,
        completed: bool | None = None,
        category: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[TaskResponse], int]:
        # Build WHERE clause dynamically
        conditions = []
        params = []

        if completed is not None:
            conditions.append("completed = ?")
            params.append(1 if completed else 0)

        if category is not None:
            conditions.append("category = ?")
            params.append(category)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Get total count
        count_cursor = await self.db.execute(
            f"SELECT COUNT(*) FROM tasks WHERE {where_clause}",
            params,
        )
        total = (await count_cursor.fetchone())[0]

        # Get paginated results
        cursor = await self.db.execute(
            f"""SELECT * FROM tasks                                                       
                  WHERE {where_clause}                                                      
                  ORDER BY created_at DESC                                                  
                  LIMIT ? OFFSET ?""",
            params + [limit, offset],
        )
        rows = await cursor.fetchall()

        tasks = [task_from_db(TaskInDB(**dict(row))) for row in rows]
        return tasks, total
