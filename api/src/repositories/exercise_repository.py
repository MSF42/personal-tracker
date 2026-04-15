import sqlite3
from datetime import datetime, timezone

from aiosqlite import Connection

from src.models.exercise import (
    CreateExerciseRequest,
    ExerciseResponse,
    UpdateExerciseRequest,
)
from src.repositories.search_sync import index_exercise, remove_from_index
from src.repositories.utils import execute_update


class SQLiteExerciseRepository:
    def __init__(self, db: Connection):
        self.db = db

    # create
    async def create(self, exercise: CreateExerciseRequest) -> ExerciseResponse:
        now = datetime.now(timezone.utc).isoformat()
        try:
            cursor = await self.db.execute(
                """
                INSERT INTO exercises (name, description, muscle_group, equipment, instructions, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    exercise.name,
                    exercise.description,
                    exercise.muscle_group.value,
                    exercise.equipment,
                    exercise.instructions,
                    now,
                    now,
                ),
            )
            exercise_id = cursor.lastrowid
            await index_exercise(
                self.db, exercise_id, exercise.name, exercise.description
            )
            await self.db.commit()
            return await self.find_by_id(exercise_id)
        except sqlite3.IntegrityError as e:
            raise ValueError(f"Exercise with name {exercise.name} already exists") from e

    # find by id
    async def find_by_id(self, exercise_id: int) -> ExerciseResponse | None:
        cursor = await self.db.execute("SELECT * FROM exercises WHERE id = ?", (exercise_id,))
        row = await cursor.fetchone()

        if row is None:
            return None

        return ExerciseResponse(**dict(row))

    # find all
    async def find_all(self) -> list[ExerciseResponse]:
        cursor = await self.db.execute("SELECT * FROM exercises ORDER BY created_at DESC")
        rows = await cursor.fetchall()

        return [ExerciseResponse(**dict(row)) for row in rows]

    # update
    async def update(
        self, exercise_id: int, data: UpdateExerciseRequest
    ) -> ExerciseResponse | None:
        existing = await self.find_by_id(exercise_id)
        if existing is None:
            return None

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return existing
        if "muscle_group" in update_data and update_data["muscle_group"] is not None:
            update_data["muscle_group"] = update_data["muscle_group"].value
        await execute_update(self.db, "exercises", update_data, exercise_id)
        if "name" in update_data or "description" in update_data:
            refreshed = await self.find_by_id(exercise_id)
            if refreshed is not None:
                await index_exercise(
                    self.db, exercise_id, refreshed.name, refreshed.description
                )
                await self.db.commit()
            return refreshed
        return await self.find_by_id(exercise_id)

    # delete
    async def delete(self, exercise_id: int) -> bool:
        cursor = await self.db.execute(
            "DELETE FROM exercises WHERE id = ?",
            (exercise_id,),
        )
        await remove_from_index(self.db, "exercise", exercise_id)
        await self.db.commit()
        return cursor.rowcount > 0
