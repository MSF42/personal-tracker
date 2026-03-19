import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_create_task(client):
    response = await client.post(
        "/api/v1/tasks",
        json={"title": "Test Task", "description": "A test task"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Task"
    assert "id" in data


@pytest.mark.asyncio
async def test_get_task_not_found(client):
    response = await client.get("/api/v1/tasks/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_and_get_task(client):
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
async def test_create_task_missing_fields_returns_422(client):
    response = await client.post("/api/v1/tasks", json={})
    assert response.status_code == 422
