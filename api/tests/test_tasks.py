import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_create_task(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/tasks",
        json={"title": "Test Task", "description": "A test task"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Task"
    assert "id" in data


@pytest.mark.asyncio
async def test_get_task_not_found(client: AsyncClient) -> None:
    response = await client.get("/api/v1/tasks/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_and_get_task(client: AsyncClient) -> None:
    # Create
    create_response = await client.post(
        "/api/v1/tasks",
        json={"title": "Fetch Me"},
    )
    task_id = create_response.json()["id"]

    # Get
    get_response = await client.get(f"/api/v1/tasks/{task_id}")
    assert get_response.status_code == 200
    assert get_response.json()["title"] == "Fetch Me"


@pytest.mark.asyncio
async def test_create_task_missing_fields_returns_422(client: AsyncClient) -> None:
    response = await client.post("/api/v1/tasks", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_task_linked_to_workout_routine(client: AsyncClient) -> None:
    routine_resp = await client.post(
        "/api/v1/workout-routines", json={"name": "Workout A"}
    )
    routine_id = routine_resp.json()["id"]

    response = await client.post(
        "/api/v1/tasks",
        json={
            "title": "Do Workout A",
            "link_type": "workout_routine",
            "link_routine_id": routine_id,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["link_type"] == "workout_routine"
    assert data["link_routine_id"] == routine_id


@pytest.mark.asyncio
async def test_create_task_linked_to_run(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/tasks",
        json={"title": "Morning Run", "link_type": "run"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["link_type"] == "run"
    assert data["link_routine_id"] is None


@pytest.mark.asyncio
async def test_create_task_workout_link_without_routine_id_returns_422(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/tasks",
        json={"title": "Do Workout A", "link_type": "workout_routine"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_task_routine_id_without_link_type_returns_422(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/tasks",
        json={"title": "Do Workout A", "link_routine_id": 1},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_task_can_change_and_clear_link(client: AsyncClient) -> None:
    routine_resp = await client.post(
        "/api/v1/workout-routines", json={"name": "Workout A"}
    )
    routine_id = routine_resp.json()["id"]
    create_resp = await client.post(
        "/api/v1/tasks",
        json={
            "title": "Do Workout A",
            "link_type": "workout_routine",
            "link_routine_id": routine_id,
        },
    )
    task_id = create_resp.json()["id"]

    cleared = await client.put(
        f"/api/v1/tasks/{task_id}",
        json={"link_type": None, "link_routine_id": None},
    )
    assert cleared.status_code == 200
    assert cleared.json()["link_type"] is None
    assert cleared.json()["link_routine_id"] is None

    # A partial update that never touches the link fields at all (the app's
    # own "mark complete" call is exactly this shape) must not be rejected.
    completed = await client.put(
        f"/api/v1/tasks/{task_id}", json={"completed": True}
    )
    assert completed.status_code == 200
