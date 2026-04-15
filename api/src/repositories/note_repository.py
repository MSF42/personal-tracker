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
from src.models.task import RepeatType
from src.repositories.search_sync import index_note, remove_from_index
from src.repositories.utils import execute_update
from src.services.task_recurrence import calculate_next_due_date


class SQLiteNoteRepository:
    def __init__(self, db: Connection):
        self.db = db

    async def get_tree(self, include_archived: bool = False) -> list[NoteTreeNode]:
        query = "SELECT * FROM notes"
        if not include_archived:
            query += " WHERE archived = 0"
        query += " ORDER BY sort_order, id"
        cursor = await self.db.execute(query)
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
        note_id = cursor.lastrowid
        await index_note(self.db, note_id, data.content)
        await self.db.commit()
        return await self.find_by_id(note_id)

    async def update(self, note_id: int, data: UpdateNoteRequest) -> NoteResponse | None:
        existing = await self.find_by_id(note_id)
        if existing is None:
            return None

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return existing

        if "collapsed" in update_data:
            update_data["collapsed"] = 1 if update_data["collapsed"] else 0
        if "archived" in update_data:
            update_data["archived"] = 1 if update_data["archived"] else 0
        if "repeat_days" in update_data:
            if update_data["repeat_days"] is not None:
                update_data["repeat_days"] = ",".join(
                    str(d) for d in update_data["repeat_days"]
                )
            else:
                update_data["repeat_days"] = None

        await execute_update(self.db, "notes", update_data, note_id)

        # If content changed, keep the search index + backlinks in sync
        if "content" in update_data:
            await index_note(self.db, note_id, update_data["content"])
            await self.db.commit()

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

    async def search(self, query: str, limit: int = 50) -> list[NoteResponse]:
        # Legacy LIKE search kept for the existing notes sidebar. The unified
        # FTS5 index is exposed via /api/v1/search.
        pattern = f"%{query}%"
        cursor = await self.db.execute(
            "SELECT * FROM notes WHERE content LIKE ? AND archived = 0 "
            "ORDER BY updated_at DESC LIMIT ?",
            (pattern, limit),
        )
        rows = await cursor.fetchall()
        return [note_from_db(NoteInDB(**dict(row))) for row in rows]

    async def delete(self, note_id: int) -> bool:
        # Collect all descendants first so we can clean up their search rows.
        cursor = await self.db.execute(
            """
            WITH RECURSIVE descendants(id) AS (
                SELECT id FROM notes WHERE id = ?
                UNION ALL
                SELECT n.id FROM notes n JOIN descendants d ON n.parent_id = d.id
            )
            SELECT id FROM descendants
            """,
            (note_id,),
        )
        descendant_ids = [row["id"] for row in await cursor.fetchall()]

        cursor = await self.db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        deleted = cursor.rowcount > 0

        for d_id in descendant_ids:
            await remove_from_index(self.db, "note", d_id)

        await self.db.commit()
        return deleted

    async def get_due(self, before_iso_date: str) -> list[NoteResponse]:
        """Return notes with due_date <= before_iso_date, excluding archived.

        Used by the /api/v1/today route. ``before_iso_date`` is a ``YYYY-MM-DD``
        string so callers can pass today's date directly from the client.
        """
        cursor = await self.db.execute(
            """
            SELECT * FROM notes
            WHERE due_date IS NOT NULL
              AND due_date <= ?
              AND archived = 0
            ORDER BY due_date ASC
            """,
            (before_iso_date,),
        )
        rows = await cursor.fetchall()
        return [note_from_db(NoteInDB(**dict(row))) for row in rows]

    async def complete_due(self, note_id: int) -> NoteResponse | None:
        """Roll the due date forward for recurring notes, or clear it.

        Mirrors the task completion flow in ``task_repository.update`` which
        already uses ``calculate_next_due_date``. For non-recurring notes the
        due date is simply cleared.
        """
        existing = await self.find_by_id(note_id)
        if existing is None:
            return None

        if existing.due_date and existing.recurrence_type:
            next_due = calculate_next_due_date(
                existing.due_date,
                RepeatType(existing.recurrence_type),
                existing.recurrence_interval or 1,
                existing.repeat_days,
            )
            await execute_update(self.db, "notes", {"due_date": next_due}, note_id)
        else:
            await execute_update(self.db, "notes", {"due_date": None}, note_id)

        return await self.find_by_id(note_id)

    async def export_markdown(self, note_id: int) -> str | None:
        """Return a nested markdown document for ``note_id`` and its subtree.

        The root note is rendered as an ``# H1``; descendants become a bulleted
        outline indented by depth, so pasting the output into another outliner
        round-trips cleanly.
        """
        root = await self.find_by_id(note_id)
        if root is None:
            return None

        cursor = await self.db.execute(
            "SELECT id, parent_id, content, sort_order FROM notes ORDER BY sort_order, id"
        )
        all_rows = await cursor.fetchall()
        children_by_parent: dict[int | None, list[dict]] = {}
        for row in all_rows:
            children_by_parent.setdefault(row["parent_id"], []).append(
                {
                    "id": row["id"],
                    "content": row["content"] or "",
                    "sort_order": row["sort_order"],
                }
            )
        for lst in children_by_parent.values():
            lst.sort(key=lambda r: r["sort_order"])

        lines: list[str] = []
        title_first_line = (root.content or "Untitled").split("\n")[0].strip() or "Untitled"
        lines.append(f"# {title_first_line}")
        rest = (root.content or "").split("\n")[1:]
        if rest:
            lines.append("")
            lines.extend(rest)
        lines.append("")

        def walk(parent_id: int, depth: int) -> None:
            for child in children_by_parent.get(parent_id, []):
                indent = "  " * depth
                content_lines = (child["content"] or "").split("\n")
                first = content_lines[0] if content_lines else ""
                lines.append(f"{indent}- {first}")
                for extra in content_lines[1:]:
                    lines.append(f"{indent}  {extra}")
                walk(child["id"], depth + 1)

        walk(root.id, 0)
        return "\n".join(lines)
