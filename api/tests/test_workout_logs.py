import uuid

from httpx import AsyncClient


async def test_create_workout_log_with_json_body(client: AsyncClient) -> None:
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


async def test_log_set_with_json_body(client: AsyncClient) -> None:
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


async def test_get_logs_by_routine_is_reachable(client: AsyncClient) -> None:
    """GET /routine/{id} must not be shadowed by GET /{workout_log_id}."""
    response = await client.get("/api/v1/workout-logs/routine/999")
    assert response.status_code != 422


async def test_list_workout_logs_returns_list(client: AsyncClient) -> None:
    """GET /workout-logs must return a list (response model enforced)."""
    response = await client.get("/api/v1/workout-logs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


async def test_workout_log_sets_include_exercise_name(client: AsyncClient) -> None:
    """Sets on a workout log must carry their exercise name, for grouping/display."""
    exercise_resp = await client.post(
        "/api/v1/exercises",
        json={"name": f"Incline Press {uuid.uuid4().hex[:8]}", "muscle_group": "chest"},
    )
    exercise_id = exercise_resp.json()["id"]
    exercise_name = exercise_resp.json()["name"]

    routine_resp = await client.post(
        "/api/v1/workout-routines",
        json={"name": f"Chest Day {uuid.uuid4().hex[:8]}"},
    )
    routine_id = routine_resp.json()["id"]

    log_resp = await client.post(
        "/api/v1/workout-logs",
        json={"routine_id": routine_id, "date": "2026-02-22"},
    )
    log_id = log_resp.json()["id"]

    set_resp = await client.post(
        f"/api/v1/workout-logs/{log_id}/sets",
        json={"exercise_id": exercise_id, "set_number": 1, "reps": 8, "weight": 40.0},
    )
    set_id = set_resp.json()["id"]

    detail = await client.get(f"/api/v1/workout-logs/{log_id}")
    assert detail.json()["sets"][0]["exercise_name"] == exercise_name

    updated = await client.put(
        f"/api/v1/workout-logs/{log_id}/sets/{set_id}",
        json={"reps": 10},
    )
    assert updated.status_code == 200
    assert updated.json()["exercise_name"] == exercise_name


async def test_get_workout_log_includes_routine_name(client: AsyncClient) -> None:
    routine_resp = await client.post(
        "/api/v1/workout-routines",
        json={"name": f"Pull Day {uuid.uuid4().hex[:8]}"},
    )
    routine_id = routine_resp.json()["id"]
    routine_name = routine_resp.json()["name"]

    log_resp = await client.post(
        "/api/v1/workout-logs",
        json={"routine_id": routine_id, "date": "2026-02-22"},
    )
    log_id = log_resp.json()["id"]

    detail = await client.get(f"/api/v1/workout-logs/{log_id}")
    assert detail.status_code == 200
    assert detail.json()["routine_name"] == routine_name


async def test_get_logs_by_routine_includes_set_and_volume_totals(client: AsyncClient) -> None:
    exercise_resp = await client.post(
        "/api/v1/exercises",
        json={"name": f"Overhead Press {uuid.uuid4().hex[:8]}", "muscle_group": "shoulders"},
    )
    exercise_id = exercise_resp.json()["id"]

    routine_resp = await client.post(
        "/api/v1/workout-routines",
        json={"name": f"Shoulder Day {uuid.uuid4().hex[:8]}"},
    )
    routine_id = routine_resp.json()["id"]

    log_resp = await client.post(
        "/api/v1/workout-logs",
        json={"routine_id": routine_id, "date": "2026-02-22"},
    )
    log_id = log_resp.json()["id"]

    for set_number, (reps, weight) in enumerate([(10, 50.0), (8, 60.0)], start=1):
        set_resp = await client.post(
            f"/api/v1/workout-logs/{log_id}/sets",
            json={
                "exercise_id": exercise_id,
                "set_number": set_number,
                "reps": reps,
                "weight": weight,
            },
        )
        assert set_resp.status_code == 201

    history = await client.get(f"/api/v1/workout-logs/routine/{routine_id}")
    assert history.status_code == 200
    entries = history.json()
    assert len(entries) == 1
    assert entries[0]["id"] == log_id
    assert entries[0]["total_sets"] == 2
    assert entries[0]["total_volume"] == 10 * 50.0 + 8 * 60.0


async def test_get_logs_by_routine_with_no_sets_has_zero_totals(client: AsyncClient) -> None:
    routine_resp = await client.post(
        "/api/v1/workout-routines",
        json={"name": f"Empty Day {uuid.uuid4().hex[:8]}"},
    )
    routine_id = routine_resp.json()["id"]
    await client.post(
        "/api/v1/workout-logs",
        json={"routine_id": routine_id, "date": "2026-02-22"},
    )

    history = await client.get(f"/api/v1/workout-logs/routine/{routine_id}")
    assert history.status_code == 200
    entries = history.json()
    assert len(entries) == 1
    assert entries[0]["total_sets"] == 0
    assert entries[0]["total_volume"] == 0
