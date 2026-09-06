from httpx import AsyncClient

IMPORT = "/api/v1/runs/import-gpx"


def make_gpx(start_minute: int = 0, comment: str = "") -> bytes:
    """Two-kilometre-ish track with three timed points; `comment` changes bytes only."""
    return f"""<?xml version="1.0"?>
<gpx xmlns="http://www.topografix.com/GPX/1/1">{comment}
  <trk><name>Dup test</name><trkseg>
    <trkpt lat="51.5000" lon="-0.1000"><time>2026-03-01T09:{start_minute:02d}:00Z</time></trkpt>
    <trkpt lat="51.5090" lon="-0.1000"><time>2026-03-01T09:{start_minute + 5:02d}:00Z</time></trkpt>
    <trkpt lat="51.5180" lon="-0.1000"><time>2026-03-01T09:{start_minute + 10:02d}:00Z</time></trkpt>
  </trkseg></trk>
</gpx>""".encode()


async def _import(
    client: AsyncClient, gpx: bytes, name: str = "run.gpx"
) -> tuple[int, dict[str, object]]:
    resp = await client.post(IMPORT, files={"file": (name, gpx, "application/gpx+xml")})
    return resp.status_code, resp.json()


async def test_same_file_twice_is_rejected(client: AsyncClient) -> None:
    status, body = await _import(client, make_gpx())
    assert status == 201
    run_id = body["activity"]["id"]  # type: ignore[index]
    try:
        status, body = await _import(client, make_gpx(), name="copy.gpx")
        assert status == 409
        assert body["code"] == "CONFLICT"
        assert f"run #{run_id}" in str(body["error"])
    finally:
        await client.delete(f"/api/v1/runs/{run_id}")


async def test_reexport_of_same_activity_is_rejected(client: AsyncClient) -> None:
    status, body = await _import(client, make_gpx())
    assert status == 201
    run_id = body["activity"]["id"]  # type: ignore[index]
    try:
        # Different bytes (hash differs), same date, duration and distance.
        status, _ = await _import(client, make_gpx(comment="<!-- re-export -->"))
        assert status == 409
    finally:
        await client.delete(f"/api/v1/runs/{run_id}")


async def test_different_activity_same_day_is_accepted(client: AsyncClient) -> None:
    status, body = await _import(client, make_gpx())
    assert status == 201
    first = body["activity"]["id"]  # type: ignore[index]
    second = None
    try:
        # Same day and distance, but starting half an hour later with a different
        # duration: a genuine second run, not a re-export.
        gpx = make_gpx(start_minute=30).replace(b"09:40:00Z", b"09:42:00Z")
        status, body = await _import(client, gpx)
        assert status == 201
        second = body["activity"]["id"]  # type: ignore[index]
    finally:
        await client.delete(f"/api/v1/runs/{first}")
        if second is not None:
            await client.delete(f"/api/v1/runs/{second}")
