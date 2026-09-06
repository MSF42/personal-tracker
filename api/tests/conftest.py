import os
import tempfile
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

# Point the API at a throwaway database before src.* is imported: settings are
# read once at import time, and without this every test run writes into the
# developer's real data/tracker.db.
_TEST_DATA_DIR = tempfile.mkdtemp(prefix="personal-tracker-tests-")
os.environ.setdefault("DATABASE_PATH", os.path.join(_TEST_DATA_DIR, "tracker.db"))
os.environ.setdefault("UPLOADS_PATH", os.path.join(_TEST_DATA_DIR, "uploads"))


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    from src.app import create_app
    from src.db.migrations import run_migrations

    # ASGITransport does not run the lifespan handler, so apply migrations here.
    await run_migrations(os.environ["DATABASE_PATH"])
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
