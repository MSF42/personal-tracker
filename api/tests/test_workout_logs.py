import uuid


async def test_create_workout_log_with_json_body(client):
    """Creating a workout log should accept a JSON body, not query params."""
    routine_resp = await client.post(
        "/api/v1/workout-routines",
        json={"name": f"Leg Day {uuid.uuid4().hex[:8]}"},
    )
    assert routine_resp.status_code == 201
    routine_id = routine_resp.json()["id"]

    log_resp = await client.post(
        "/api/v1/workout-logs",
        json={"routine_id": routine_id, "date": "2026-02-22", "notes": "felt good"},
    )
    assert log_resp.status_code == 201
    data = log_resp.json()
    assert data["routine_id"] == routine_id
    assert data["date"] == "2026-02-22"


async def test_log_set_with_json_body(client):
    """Logging a set should accept a JSON body, not query params."""
    exercise_resp = await client.post(
        "/api/v1/exercises",
        json={"name": f"Bench Press {uuid.uuid4().hex[:8]}", "muscle_group": "chest"},
    )
    assert exercise_resp.status_code == 201
    exercise_id = exercise_resp.json()["id"]

    routine_resp = await client.post(
        "/api/v1/workout-routines",
        json={"name": f"Push Day {uuid.uuid4().hex[:8]}"},
    )
    assert routine_resp.status_code == 201
    routine_id = routine_resp.json()["id"]

    log_resp = await client.post(
        "/api/v1/workout-logs",
        json={"routine_id": routine_id, "date": "2026-02-22"},
    )
    assert log_resp.status_code == 201
    log_id = log_resp.json()["id"]

    set_resp = await client.post(
        f"/api/v1/workout-logs/{log_id}/sets",
        json={"exercise_id": exercise_id, "set_number": 1, "reps": 10, "weight": 135.0},
    )
    assert set_resp.status_code == 201
    data = set_resp.json()
    assert data["reps"] == 10


async def test_get_logs_by_routine_is_reachable(client):
    """GET /routine/{id} must not be shadowed by GET /{workout_log_id}."""
    response = await client.get("/api/v1/workout-logs/routine/999")
    assert response.status_code != 422


async def test_list_workout_logs_returns_list(client):
    """GET /workout-logs must return a list (response model enforced)."""
    response = await client.get("/api/v1/workout-logs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
