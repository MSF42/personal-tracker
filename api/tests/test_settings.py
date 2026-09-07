import io
import zipfile

import pytest
from httpx import AsyncClient


def make_zip(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_reset_clears_measurements(client: AsyncClient) -> None:
    """Data reset should delete measurement data."""
    # Create a measurement via the API
    create_resp = await client.post(
        "/api/v1/measurements",
        json={"name": "Reset Test Weight", "unit": "kg"},
    )
    assert create_resp.status_code == 201

    # Reset all data
    reset_resp = await client.post("/api/v1/settings/reset")
    assert reset_resp.status_code == 200

    # Measurement should be gone
    get_resp = await client.get("/api/v1/measurements")
    assert get_resp.json() == []


@pytest.mark.asyncio
async def test_restore_rejects_path_traversal_in_uploads(client: AsyncClient) -> None:
    """A zip entry with path traversal in an uploads path must be rejected."""
    bad_zip = make_zip(
        {
            "tracker.db": b"x" * 100,
            "uploads/../evil.txt": b"pwned",
        }
    )
    response = await client.post(
        "/api/v1/settings/restore",
        files={"file": ("backup.zip", bad_zip, "application/zip")},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_restore_rejects_tracker_db_path_traversal(client: AsyncClient) -> None:
    """A zip with a tracker.db entry containing path components must be rejected."""
    bad_zip = make_zip(
        {
            "../tracker.db": b"x" * 100,
        }
    )
    response = await client.post(
        "/api/v1/settings/restore",
        files={"file": ("backup.zip", bad_zip, "application/zip")},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_seed_populates_every_domain(client: AsyncClient) -> None:
    """Seeding should leave data behind in every domain it touches."""
    response = await client.post("/api/v1/settings/seed")
    assert response.status_code == 200

    for path, min_count in [
        ("/api/v1/tasks", 5),
        ("/api/v1/habits", 5),
        ("/api/v1/exercises", 10),
        ("/api/v1/workout-routines", 3),
        ("/api/v1/runs", 5),
        ("/api/v1/measurements", 2),
    ]:
        res = await client.get(path)
        assert res.status_code == 200, path
        assert len(res.json()) >= min_count, path

    logs_res = await client.get("/api/v1/workout-logs")
    assert logs_res.status_code == 200
    assert len(logs_res.json()) >= 7
