import uuid

from httpx import AsyncClient


async def test_create_core_exercise(client: AsyncClient) -> None:
    """'core' is a valid muscle group alongside the original six."""
    resp = await client.post(
        "/api/v1/exercises",
        json={"name": f"Pallof Press {uuid.uuid4().hex[:8]}", "muscle_group": "core"},
    )
    assert resp.status_code == 201
    assert resp.json()["muscle_group"] == "core"


async def test_create_exercise_rejects_unknown_muscle_group(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/exercises",
        json={"name": f"Mystery {uuid.uuid4().hex[:8]}", "muscle_group": "cardio"},
    )
    assert resp.status_code == 422
