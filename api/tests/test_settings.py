import io
import zipfile

import pytest


def make_zip(entries: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_reset_clears_measurements(client):
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
async def test_restore_rejects_path_traversal_in_uploads(client):
    """A zip entry with path traversal in an uploads path must be rejected."""
    bad_zip = make_zip({
        "tracker.db": b"x" * 100,
        "uploads/../evil.txt": b"pwned",
    })
    response = await client.post(
        "/api/v1/settings/restore",
        files={"file": ("backup.zip", bad_zip, "application/zip")},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_restore_rejects_tracker_db_path_traversal(client):
    """A zip with a tracker.db entry containing path components must be rejected."""
    bad_zip = make_zip({
        "../tracker.db": b"x" * 100,
    })
    response = await client.post(
        "/api/v1/settings/restore",
        files={"file": ("backup.zip", bad_zip, "application/zip")},
    )
    assert response.status_code == 400
