from datetime import datetime, timezone

from aiosqlite import Connection

from src.models.measurement import (
    CreateMeasurementEntryRequest,
    CreateMeasurementRequest,
    MeasurementEntryInDB,
    MeasurementEntryResponse,
    MeasurementInDB,
    MeasurementResponse,
    UpdateMeasurementEntryRequest,
    UpdateMeasurementRequest,
    entry_from_db,
    measurement_from_db,
)
from src.repositories.utils import execute_update


class SQLiteMeasurementRepository:
    def __init__(self, db: Connection):
        self.db = db

    async def create_measurement(self, data: CreateMeasurementRequest) -> MeasurementResponse:
        now = datetime.now(timezone.utc).isoformat()

        # Get next sort_order
        cursor = await self.db.execute("SELECT COALESCE(MAX(sort_order), -1) + 1 FROM measurements")
        row = await cursor.fetchone()
        next_order = row[0] if row else 0

        cursor = await self.db.execute(
            """
            INSERT INTO measurements (name, unit, sort_order, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (data.name, data.unit, next_order, now, now),
        )
        await self.db.commit()

        return await self.find_measurement_by_id(cursor.lastrowid)

    async def find_measurement_by_id(self, measurement_id: int) -> MeasurementResponse | None:
        cursor = await self.db.execute(
            "SELECT * FROM measurements WHERE id = ?",
            (measurement_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return measurement_from_db(MeasurementInDB(**dict(row)))

    async def find_all_measurements(self) -> list[MeasurementResponse]:
        cursor = await self.db.execute("SELECT * FROM measurements ORDER BY sort_order ASC")
        rows = await cursor.fetchall()
        return [measurement_from_db(MeasurementInDB(**dict(row))) for row in rows]

    async def update_measurement(
        self, measurement_id: int, data: UpdateMeasurementRequest
    ) -> MeasurementResponse | None:
        existing = await self.find_measurement_by_id(measurement_id)
        if existing is None:
            return None

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return existing

        await execute_update(self.db, "measurements", update_data, measurement_id)
        return await self.find_measurement_by_id(measurement_id)

    async def delete_measurement(self, measurement_id: int) -> bool:
        cursor = await self.db.execute(
            "DELETE FROM measurements WHERE id = ?",
            (measurement_id,),
        )
        await self.db.commit()
        return cursor.rowcount > 0

    async def create_entry(
        self, measurement_id: int, data: CreateMeasurementEntryRequest
    ) -> MeasurementEntryResponse:
        now = datetime.now(timezone.utc).isoformat()

        cursor = await self.db.execute(
            """
            INSERT INTO measurement_entries (measurement_id, date, value, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (measurement_id, data.date, data.value, data.notes, now, now),
        )
        await self.db.commit()

        return await self.find_entry_by_id(cursor.lastrowid)

    async def find_entry_by_id(self, entry_id: int) -> MeasurementEntryResponse | None:
        cursor = await self.db.execute(
            "SELECT * FROM measurement_entries WHERE id = ?",
            (entry_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return entry_from_db(MeasurementEntryInDB(**dict(row)))

    async def find_entries(self, measurement_id: int) -> list[MeasurementEntryResponse]:
        cursor = await self.db.execute(
            "SELECT * FROM measurement_entries WHERE measurement_id = ? ORDER BY date DESC",
            (measurement_id,),
        )
        rows = await cursor.fetchall()
        return [entry_from_db(MeasurementEntryInDB(**dict(row))) for row in rows]

    async def update_entry(
        self, entry_id: int, data: UpdateMeasurementEntryRequest
    ) -> MeasurementEntryResponse | None:
        existing = await self.find_entry_by_id(entry_id)
        if existing is None:
            return None

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return existing

        await execute_update(self.db, "measurement_entries", update_data, entry_id)
        return await self.find_entry_by_id(entry_id)

    async def delete_entry(self, entry_id: int) -> bool:
        cursor = await self.db.execute(
            "DELETE FROM measurement_entries WHERE id = ?",
            (entry_id,),
        )
        await self.db.commit()
        return cursor.rowcount > 0
