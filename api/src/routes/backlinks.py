from fastapi import APIRouter, Depends, Query

from src.db.database import get_db

router = APIRouter(prefix="/api/v1/backlinks", tags=["Backlinks"])


@router.get("")
async def get_backlinks(
    target: str = Query(..., min_length=1, max_length=200),
    exclude_note_id: int | None = None,
    db=Depends(get_db),
):
    """Return notes whose content references ``target`` via ``[[target]]``.

    Matching is case-insensitive; the link index is populated on every note
    upsert so this is a cheap indexed JOIN rather than a LIKE scan. Pass
    ``exclude_note_id`` to filter out the note currently being viewed.
    """
    normalized = target.strip().lower()
    if not normalized:
        return {"links": []}
    params: list = [normalized]
    query = (
        "SELECT n.id, n.parent_id, n.content, n.updated_at "
        "FROM node_links l "
        "JOIN notes n ON n.id = l.node_id "
        "WHERE l.target_name = ? AND n.archived = 0"
    )
    if exclude_note_id is not None:
        query += " AND n.id != ?"
        params.append(exclude_note_id)
    query += " ORDER BY n.updated_at DESC LIMIT 200"
    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    return {
        "links": [
            {
                "id": r["id"],
                "parent_id": r["parent_id"],
                "content": r["content"] or "",
                "updated_at": r["updated_at"],
            }
            for r in rows
        ]
    }
