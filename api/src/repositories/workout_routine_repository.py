import sqlite3
from datetime import datetime, timezone

from aiosqlite import Connection

from src.models.workout_routine import (
    CreateWorkoutRoutineRequest,
    UpdateWorkoutRoutineRequest,
    WorkoutRoutineInDB,
    WorkoutRoutineResponse,
    workout_routine_from_db,
)


class SQLiteWorkoutRoutineRepository:
    def __init__(self, db: Connection):
        self.db = db

    # create
    async def create(self, routine: CreateWorkoutRoutineRequest) -> WorkoutRoutineResponse:
        now = datetime.now(timezone.utc).isoformat()
        try:
            cursor = await self.db.execute(
                """
                INSERT INTO workout_routines (name, description, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                """,
                (routine.name, routine.description, now, now),
            )
            await self.db.commit()

            workout_routine_id = cursor.lastrowid
            return await self.find_by_id(workout_routine_id)
        except sqlite3.IntegrityError as e:
            raise ValueError(f"Workout routine with name {routine.name} already exists") from e

    # find by id
    async def find_by_id(self, workout_routine_id: int) -> WorkoutRoutineResponse | None:
        cursor = await self.db.execute(
            "SELECT * FROM workout_routines WHERE id = ?",
            (workout_routine_id,),
        )
        row = await cursor.fetchone()

        if row is None:
            return None

        routine_in_db = WorkoutRoutineInDB(**dict(row))
        return workout_routine_from_db(routine_in_db)

    # find all
    async def find_all(self) -> list[WorkoutRoutineResponse]:
        cursor = await self.db.execute("SELECT * FROM workout_routines")
        rows = await cursor.fetchall()

        return [workout_routine_from_db(WorkoutRoutineInDB(**dict(row))) for row in rows]

    # update
    async def update(
        self, workout_routine_id: int, data: UpdateWorkoutRoutineRequest
    ) -> WorkoutRoutineResponse | None:
        existing = await self.find_by_id(workout_routine_id)
        if existing is None:
            return None

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return existing

        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        set_clause = ", ".join(f"{key} = ?" for key in update_data.keys())
        values = list(update_data.values()) + [workout_routine_id]

        await self.db.execute(
            f"UPDATE workout_routines SET {set_clause} WHERE id = ?",
            values,
        )
        await self.db.commit()

        return await self.find_by_id(workout_routine_id)

    # delete
    async def delete(self, workout_routine_id: int) -> bool:
        cursor = await self.db.execute(
            "DELETE FROM workout_routines WHERE id = ?",
            (workout_routine_id,),
        )
        await self.db.commit()

        return cursor.rowcount > 0
