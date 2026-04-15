"""Helpers for wiki-link / tag / mention parsing in note content.

The outliner supports Obsidian-style ``[[Target Name]]`` or
``[[Target Name|alias]]`` references between notes. A dedicated ``node_links``
table holds the parsed targets so backlinks can be served with a JOIN instead
of a LIKE scan.
"""

from __future__ import annotations

import re

_WIKI_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")


def parse_wiki_targets(content: str | None) -> list[str]:
    """Return the distinct, case-folded wiki-link targets in ``content``.

    Each match is trimmed and lower-cased so backlink lookups are
    case-insensitive without requiring ``COLLATE NOCASE`` on the table.
    """
    if not content:
        return []
    seen: set[str] = set()
    for match in _WIKI_RE.finditer(content):
        target = match.group(1).strip().lower()
        if target:
            seen.add(target)
    return sorted(seen)
