import pytest


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
