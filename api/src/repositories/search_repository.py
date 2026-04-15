"""Query side of the unified FTS5 search index.

The mutation side lives in ``search_sync.py``. This repository is only
instantiated by the ``/api/v1/search`` route handler, which exposes prefix
search with ``<mark>``-annotated snippets for the command palette.
"""

from __future__ import annotations

from typing import Any

from aiosqlite import Connection


def _build_fts_query(q: str) -> str:
    """Convert a free-text query into an FTS5 MATCH expression.

    Each whitespace-separated term is quoted (so punctuation or reserved
    tokens can't break the parser) and marked as a prefix match with ``*``.
    An empty input produces an empty string, which the caller treats as
    "no results".
    """
    terms = []
    for raw in q.strip().split():
        cleaned = raw.replace('"', '""')
        if cleaned:
            terms.append(f'"{cleaned}"*')
    return " ".join(terms)


class SQLiteSearchRepository:
    def __init__(self, db: Connection):
        self.db = db

    async def query(self, q: str, limit: int = 30) -> list[dict[str, Any]]:
        fts = _build_fts_query(q)
        if not fts:
            return []
        cursor = await self.db.execute(
            """
            SELECT
                kind,
                entity_id,
                title,
                snippet(search_index, 4, '<mark>', '</mark>', '…', 16) AS snippet
            FROM search_index
            WHERE search_index MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (fts, limit),
        )
        rows = await cursor.fetchall()
        return [
            {
                "kind": r["kind"],
                "entity_id": int(r["entity_id"]),
                "title": r["title"] or "",
                "snippet": r["snippet"] or "",
            }
            for r in rows
        ]
