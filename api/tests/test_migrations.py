import os
import tempfile

import pytest

from src.db.migrations import run_migrations


@pytest.mark.asyncio
async def test_migrations_run_on_fresh_database():
    """Fresh DB should complete all migrations without error."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        await run_migrations(db_path)  # Should not raise
    finally:
        os.unlink(db_path)
