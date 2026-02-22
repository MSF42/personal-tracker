from datetime import datetime, timezone

from aiosqlite import Connection

from src.models.note import (
    CreateNoteRequest,
    MoveNoteRequest,
    NoteInDB,
    NoteResponse,
    NoteTreeNode,
    UpdateNoteRequest,
    note_from_db,
)
from src.repositories.utils import execute_update


class SQLiteNoteRepository:
    def __init__(self, db: Connection):
        self.db = db

    async def get_tree(self) -> list[NoteTreeNode]:
        cursor = await self.db.execute("SELECT * FROM notes ORDER BY sort_order, id")
        rows = await cursor.fetchall()

        nodes: dict[int, NoteTreeNode] = {}
        roots: list[NoteTreeNode] = []

        for row in rows:
            note = note_from_db(NoteInDB(**dict(row)))
            node = NoteTreeNode(**note.model_dump(), children=[])
            nodes[node.id] = node

        for node in nodes.values():
            if node.parent_id and node.parent_id in nodes:
                nodes[node.parent_id].children.append(node)
            else:
                roots.append(node)

        return roots

    async def find_by_id(self, note_id: int) -> NoteResponse | None:
        cursor = await self.db.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        return note_from_db(NoteInDB(**dict(row)))

    async def create(self, data: CreateNoteRequest) -> NoteResponse:
        now = datetime.now(timezone.utc).isoformat()

        # If no sort_order provided (0 default), place at end of siblings
        if data.sort_order == 0:
            cursor = await self.db.execute(
                "SELECT COALESCE(MAX(sort_order), -1) + 1 FROM notes WHERE parent_id IS ?",
                (data.parent_id,),
            )
            row = await cursor.fetchone()
            sort_order = row[0]
        else:
            sort_order = data.sort_order

        cursor = await self.db.execute(
            """
            INSERT INTO notes (parent_id, content, sort_order, collapsed, created_at, updated_at)
            VALUES (?, ?, ?, 0, ?, ?)
            """,
            (data.parent_id, data.content, sort_order, now, now),
        )
        await self.db.commit()
        return await self.find_by_id(cursor.lastrowid)

    async def update(self, note_id: int, data: UpdateNoteRequest) -> NoteResponse | None:
        existing = await self.find_by_id(note_id)
        if existing is None:
            return None

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return existing

        if "collapsed" in update_data:
            update_data["collapsed"] = 1 if update_data["collapsed"] else 0

        await execute_update(self.db, "notes", update_data, note_id)
        return await self.find_by_id(note_id)

    async def move(self, note_id: int, data: MoveNoteRequest) -> NoteResponse | None:
        existing = await self.find_by_id(note_id)
        if existing is None:
            return None

        now = datetime.now(timezone.utc).isoformat()
        await self.db.execute(
            "UPDATE notes SET parent_id = ?, sort_order = ?, updated_at = ? WHERE id = ?",
            (data.parent_id, data.sort_order, now, note_id),
        )
        await self.db.commit()
        return await self.find_by_id(note_id)

    async def delete(self, note_id: int) -> bool:
        # CASCADE delete handled by FK, but need PRAGMA foreign_keys = ON
        await self.db.execute("PRAGMA foreign_keys = ON")
        cursor = await self.db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        await self.db.commit()
        return cursor.rowcount > 0
