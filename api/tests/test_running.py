import pytest


@pytest.mark.asyncio
async def test_import_gpx_rejects_malformed_xml(client):
    """Malformed XML uploaded as GPX must return 422, not 500."""
    response = await client.post(
        "/api/v1/runs/import-gpx",
        files={"file": ("track.gpx", b"this is not xml!!!", "application/gpx+xml")},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_import_gpx_rejects_too_few_trackpoints(client):
    """A GPX with fewer than 2 trackpoints must return 422, not 500."""
    gpx = b"""<?xml version="1.0"?>
<gpx xmlns="http://www.topografix.com/GPX/1/1">
  <trk><trkseg>
    <trkpt lat="51.5" lon="-0.1"><time>2026-01-01T09:00:00Z</time></trkpt>
  </trkseg></trk>
</gpx>"""
    response = await client.post(
        "/api/v1/runs/import-gpx",
        files={"file": ("track.gpx", gpx, "application/gpx+xml")},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_run(client):
    response = await client.post(
        "/api/v1/runs",
        json={
            "date": "2026-02-08T20:00:22Z",
            "duration_seconds": 900,
            "distance_km": 2.00,
            "notes": "This is a test run.",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["notes"] == "This is a test run."
    assert "id" in data
