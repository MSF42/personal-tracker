import re

from fastapi import APIRouter, Depends

from src.db.database import get_db

router = APIRouter(prefix="/api/v1/tags", tags=["Tags"])

_TAG_RE = re.compile(r"(?:^|\s)#([a-z0-9_\-]{2,32})", re.IGNORECASE)
_MENTION_RE = re.compile(r"(?:^|\s)@([a-z0-9_\-]{2,32})", re.IGNORECASE)


@router.get("")
async def list_tags(db=Depends(get_db)):
    """Return tag and mention counts scanned from note content.

    Cheap enough for a personal-scale database; called once when the sidebar
    mounts. Each note contributes at most one count per distinct tag/mention
    so a note with ``#foo #foo`` still counts as a single ``foo`` hit.
    """
    cursor = await db.execute(
        "SELECT content FROM notes WHERE archived = 0"
    )
    rows = await cursor.fetchall()

    tag_counts: dict[str, int] = {}
    mention_counts: dict[str, int] = {}
    for row in rows:
        content = row["content"] or ""
        for name in {m.group(1).lower() for m in _TAG_RE.finditer(content)}:
            tag_counts[name] = tag_counts.get(name, 0) + 1
        for name in {m.group(1).lower() for m in _MENTION_RE.finditer(content)}:
            mention_counts[name] = mention_counts.get(name, 0) + 1

    tags_sorted = sorted(
        ({"name": k, "count": v} for k, v in tag_counts.items()),
        key=lambda x: (-x["count"], x["name"]),
    )
    mentions_sorted = sorted(
        ({"name": k, "count": v} for k, v in mention_counts.items()),
        key=lambda x: (-x["count"], x["name"]),
    )
    return {"tags": tags_sorted, "mentions": mentions_sorted}
