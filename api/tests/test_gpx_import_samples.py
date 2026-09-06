from httpx import AsyncClient

GPX = b"""<?xml version="1.0"?>
<gpx xmlns="http://www.topografix.com/GPX/1/1"><trk><name>Loop</name><trkseg>
  <trkpt lat="51.5000" lon="-0.1000"><ele>30.0</ele><time>2026-04-01T09:00:00Z</time></trkpt>
  <trkpt lat="51.5090" lon="-0.1000"><ele>32.5</ele><time>2026-04-01T09:05:00Z</time></trkpt>
  <trkpt lat="51.5090" lon="-0.0850"><time>2026-04-01T09:10:00Z</time></trkpt>
  <trkpt lat="51.5180" lon="-0.0850"><ele>35</ele><time>2026-04-01T09:15:00Z</time></trkpt>
</trkseg></trk></gpx>"""


async def test_gpx_import_stores_samples_with_positions(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/runs/import-gpx", files={"file": ("loop.gpx", GPX, "application/gpx+xml")}
    )
    assert resp.status_code == 201, resp.text
    run = resp.json()["activity"]
    try:
        samples = (await client.get(f"/api/v1/runs/{run['id']}/samples")).json()
        assert len(samples) == 4
        assert samples[0]["t_seconds"] == 0 and samples[-1]["t_seconds"] == 900
        assert samples[0]["lat"] == 51.5 and samples[0]["lon"] == -0.1
        assert samples[0]["altitude_m"] == 30.0
        assert samples[2]["altitude_m"] is None
        assert samples[0]["distance_km"] == 0
        # Cumulative distance ends at the run's total (rounded to 2 dp on the run).
        assert abs(samples[-1]["distance_km"] - run["distance_km"]) < 0.01
    finally:
        await client.delete(f"/api/v1/runs/{run['id']}")
