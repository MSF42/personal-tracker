import uuid

from httpx import AsyncClient


def _unique_name(prefix: str) -> str:
    return f"{prefix} {uuid.uuid4().hex[:8]}"


async def test_create_and_list_measurement(client: AsyncClient) -> None:
    name = _unique_name("Waist")
    response = await client.post(
        "/api/v1/measurements", json={"name": name, "unit": "in"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == name
    assert data["unit"] == "in"

    list_response = await client.get("/api/v1/measurements")
    assert list_response.status_code == 200
    assert any(m["id"] == data["id"] for m in list_response.json())


async def test_update_measurement_sort_order(client: AsyncClient) -> None:
    first = (
        await client.post(
            "/api/v1/measurements", json={"name": _unique_name("Waist")}
        )
    ).json()
    second = (
        await client.post(
            "/api/v1/measurements", json={"name": _unique_name("Neck")}
        )
    ).json()
    assert first["sort_order"] < second["sort_order"]

    # Swap their sort_order to move "Neck" ahead of "Waist".
    swap_first = await client.put(
        f"/api/v1/measurements/{first['id']}",
        json={"sort_order": second["sort_order"]},
    )
    swap_second = await client.put(
        f"/api/v1/measurements/{second['id']}",
        json={"sort_order": first["sort_order"]},
    )
    assert swap_first.status_code == 200
    assert swap_second.status_code == 200

    listed = (await client.get("/api/v1/measurements")).json()
    by_id = {m["id"]: m for m in listed}
    assert by_id[first["id"]]["sort_order"] == second["sort_order"]
    assert by_id[second["id"]]["sort_order"] == first["sort_order"]


async def test_delete_measurement(client: AsyncClient) -> None:
    created = (
        await client.post(
            "/api/v1/measurements", json={"name": _unique_name("Chest")}
        )
    ).json()
    response = await client.delete(f"/api/v1/measurements/{created['id']}")
    assert response.status_code == 204

    listed = (await client.get("/api/v1/measurements")).json()
    assert all(m["id"] != created["id"] for m in listed)
