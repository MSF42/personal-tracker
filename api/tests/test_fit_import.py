from datetime import UTC, datetime

from httpx import AsyncClient

from tests.fit_builder import simple_run

IMPORT_FIT = "/api/v1/runs/import-fit"
IMPORT_GPX = "/api/v1/runs/import-gpx"
UUID_A = bytes(range(16))


async def _post_fit(
    client: AsyncClient, data: bytes, name: str = "run.fit"
) -> tuple[int, dict[str, object]]:
    resp = await client.post(IMPORT_FIT, files={"file": (name, data, "application/octet-stream")})
    return resp.status_code, resp.json()


async def _delete(client: AsyncClient, run_id: object) -> None:
    await client.delete(f"/api/v1/runs/{run_id}")


async def test_import_fit_creates_run_with_metrics_laps_and_samples(client: AsyncClient) -> None:
    status, body = await _post_fit(client, simple_run(uuid_bytes=UUID_A))
    assert status == 201, body
    activity = body["activity"]
    assert isinstance(activity, dict)
    run_id = activity["id"]
    try:
        assert activity["source"] == "fit"
        assert activity["has_gpx"] is True
        assert activity["distance_km"] == 2.0
        assert activity["duration_seconds"] == 720
        assert activity["avg_hr"] == 150
        assert activity["avg_cadence"] == 160
        assert activity["calories"] == 170
        assert activity["title"] == "Run"
        laps = body["laps"]
        assert isinstance(laps, list) and len(laps) == 2
        segments = body["segments"]
        assert isinstance(segments, list) and any(s["segment_name"] == "1K" for s in segments)

        laps_resp = await client.get(f"/api/v1/runs/{run_id}/laps")
        assert laps_resp.status_code == 200
        assert [lap["lap_index"] for lap in laps_resp.json()] == [0, 1]

        samples_resp = await client.get(f"/api/v1/runs/{run_id}/samples")
        assert samples_resp.status_code == 200
        samples = samples_resp.json()
        assert len(samples) == 73
        assert samples[0]["t_seconds"] == 0 and samples[-1]["t_seconds"] == 720

        thinned = (await client.get(f"/api/v1/runs/{run_id}/samples?max_points=10")).json()
        assert len(thinned) == 10
        assert thinned[0]["t_seconds"] == 0 and thinned[-1]["t_seconds"] == 720
    finally:
        await _delete(client, run_id)


async def test_same_fit_twice_is_rejected(client: AsyncClient) -> None:
    data = simple_run()
    status, body = await _post_fit(client, data)
    assert status == 201
    run_id = body["activity"]["id"]  # type: ignore[index]
    try:
        status, body = await _post_fit(client, data, name="copy.fit")
        assert status == 409
        assert body["code"] == "CONFLICT"
    finally:
        await _delete(client, run_id)


async def test_same_session_uuid_is_rejected_even_if_bytes_differ(client: AsyncClient) -> None:
    status, body = await _post_fit(client, simple_run(uuid_bytes=UUID_A, hr=150))
    assert status == 201
    run_id = body["activity"]["id"]  # type: ignore[index]
    try:
        # Different HR values change the bytes, totals and hash; the UUID still matches.
        status, _ = await _post_fit(client, simple_run(uuid_bytes=UUID_A, hr=140, seconds=730))
        assert status == 409
    finally:
        await _delete(client, run_id)


async def test_gpx_then_fit_of_same_start_is_rejected(client: AsyncClient) -> None:
    start = datetime(2026, 3, 1, 9, 0, tzinfo=UTC)
    gpx = f"""<?xml version="1.0"?>
<gpx xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg>
  <trkpt lat="51.5000" lon="-0.1000"><time>{start.isoformat()}</time></trkpt>
  <trkpt lat="51.5090" lon="-0.1000"><time>2026-03-01T09:05:00+00:00</time></trkpt>
  <trkpt lat="51.5180" lon="-0.1000"><time>2026-03-01T09:12:00+00:00</time></trkpt>
</trkseg></trk></gpx>""".encode()
    resp = await client.post(IMPORT_GPX, files={"file": ("run.gpx", gpx, "application/gpx+xml")})
    assert resp.status_code == 201
    run_id = resp.json()["activity"]["id"]
    assert resp.json()["activity"]["start_time"].startswith("2026-03-01T09:00:00")
    try:
        status, body = await _post_fit(client, simple_run(start=start))
        assert status == 409, body
    finally:
        await _delete(client, run_id)


async def test_different_run_next_day_is_accepted(client: AsyncClient) -> None:
    a = simple_run(start=datetime(2026, 3, 1, 9, 0, tzinfo=UTC))
    b = simple_run(start=datetime(2026, 3, 2, 9, 0, tzinfo=UTC))
    ids = []
    try:
        for data in (a, b):
            status, body = await _post_fit(client, data)
            assert status == 201, body
            ids.append(body["activity"]["id"])  # type: ignore[index]
    finally:
        for run_id in ids:
            await _delete(client, run_id)


async def test_invalid_fit_returns_422(client: AsyncClient) -> None:
    status, body = await _post_fit(client, b"nope")
    assert status == 422
    assert body["code"] == "VALIDATION_ERROR"
