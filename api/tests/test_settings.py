import pytest


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
