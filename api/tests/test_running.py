import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_import_gpx_rejects_malformed_xml(client: AsyncClient) -> None:
    """Malformed XML uploaded as GPX must return 422, not 500."""
    response = await client.post(
        "/api/v1/runs/import-gpx",
        files={"file": ("track.gpx", b"this is not xml!!!", "application/gpx+xml")},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_import_gpx_rejects_too_few_trackpoints(client: AsyncClient) -> None:
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
async def test_create_run(client: AsyncClient) -> None:
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


@pytest.mark.asyncio
async def test_list_runs_filters_by_inclusive_date_range(client: AsyncClient) -> None:
    # The test DB is shared across the session, so use dates no other test touches.
    for day in ("1901-03-01", "1901-03-10", "1901-03-20"):
        await client.post(
            "/api/v1/runs",
            json={"date": day, "duration_seconds": 600, "distance_km": 2.0},
        )

    response = await client.get(
        "/api/v1/runs", params={"date_from": "1901-03-01", "date_to": "1901-03-10"}
    )
    assert response.status_code == 200
    assert [r["date"] for r in response.json()] == ["1901-03-10", "1901-03-01"]

    open_ended = await client.get("/api/v1/runs", params={"date_to": "1901-03-10"})
    assert [r["date"] for r in open_ended.json()] == ["1901-03-10", "1901-03-01"]

    unfiltered = {r["date"] for r in (await client.get("/api/v1/runs")).json()}
    assert {"1901-03-01", "1901-03-10", "1901-03-20"} <= unfiltered
    assert (await client.get("/api/v1/runs", params={"date_from": "nope"})).status_code == 422


@pytest.mark.asyncio
async def test_badges_endpoints(client: AsyncClient) -> None:
    # Shared test DB: use far-past dates so other tests' runs come later and
    # can't change these runs' badges (badges only look backwards).
    for day in ("1902-01-01", "1902-01-02", "1902-01-03"):
        await client.post(
            "/api/v1/runs", json={"date": day, "duration_seconds": 1000, "distance_km": 3.0}
        )
    resp = await client.post(
        "/api/v1/runs", json={"date": "1902-01-20", "duration_seconds": 1500, "distance_km": 5.0}
    )
    five_k = resp.json()["id"]

    one = await client.get(f"/api/v1/runs/{five_k}/badges")
    assert one.status_code == 200
    assert {"kind": "longest", "since": None, "ever": True, "effort": None, "value": 5.0} in (
        one.json()
    )

    # (Other 1902 runs can earn comeback / beat-last-year badges against
    # another test's 1901 runs, so check one run that earns nothing.)
    listed = await client.get(
        "/api/v1/runs/badges", params={"date_from": "1902-01-10", "date_to": "1902-12-31"}
    )
    assert [r["run_id"] for r in listed.json()] == [five_k]
    quiet = await client.get(
        "/api/v1/runs/badges", params={"date_from": "1902-01-02", "date_to": "1902-01-02"}
    )
    assert quiet.json() == []  # runs without badges are omitted

    assert (await client.get("/api/v1/runs/999999/badges")).status_code == 404
    efforts = await client.get("/api/v1/runs/best-efforts")
    assert efforts.status_code == 200
    assert all({"name", "duration_seconds", "run_id"} <= e.keys() for e in efforts.json())
