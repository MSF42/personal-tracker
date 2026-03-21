from datetime import date

import pytest

BASE = "/api/v1/habits"


@pytest.mark.asyncio
async def test_create_habit_returns_201_with_correct_fields(client):
    response = await client.post(
        BASE,
        json={"name": "Drink Water", "frequency": "daily", "color": "#10b981"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Drink Water"
    assert data["frequency"] == "daily"
    assert data["color"] == "#10b981"
    assert data["archived"] is False
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert "current_streak" in data
    assert "longest_streak" in data
    assert "completed_today" in data


@pytest.mark.asyncio
async def test_create_habit_defaults(client):
    response = await client.post(BASE, json={"name": "Meditate"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Meditate"
    assert data["frequency"] == "daily"
    assert data["color"] == "#3b82f6"
    assert data["description"] is None


@pytest.mark.asyncio
async def test_get_habit_by_id_returns_200(client):
    create_resp = await client.post(
        BASE,
        json={"name": "Morning Run", "frequency": "daily", "color": "#f59e0b"},
    )
    assert create_resp.status_code == 201
    habit_id = create_resp.json()["id"]

    response = await client.get(f"{BASE}/{habit_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == habit_id
    assert data["name"] == "Morning Run"
    assert data["frequency"] == "daily"
    assert data["color"] == "#f59e0b"


@pytest.mark.asyncio
async def test_update_habit_returns_updated_fields(client):
    create_resp = await client.post(
        BASE,
        json={"name": "Old Name", "frequency": "daily", "color": "#3b82f6"},
    )
    assert create_resp.status_code == 201
    habit_id = create_resp.json()["id"]

    update_resp = await client.put(
        f"{BASE}/{habit_id}",
        json={"name": "New Name", "color": "#ef4444"},
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["id"] == habit_id
    assert data["name"] == "New Name"
    assert data["color"] == "#ef4444"
    assert data["frequency"] == "daily"


@pytest.mark.asyncio
async def test_list_habits_contains_created_habit(client):
    await client.post(BASE, json={"name": "Read Books"})
    response = await client.get(BASE)
    assert response.status_code == 200
    names = [h["name"] for h in response.json()]
    assert "Read Books" in names


@pytest.mark.asyncio
async def test_list_habits_excludes_archived_by_default(client):
    # Create a habit then archive it
    create_resp = await client.post(BASE, json={"name": "To Archive"})
    habit_id = create_resp.json()["id"]
    await client.put(f"{BASE}/{habit_id}", json={"archived": True})

    response = await client.get(BASE)
    assert response.status_code == 200
    ids = [h["id"] for h in response.json()]
    assert habit_id not in ids


@pytest.mark.asyncio
async def test_list_habits_include_archived_param(client):
    # Create a habit then archive it
    create_resp = await client.post(BASE, json={"name": "Archived Habit"})
    habit_id = create_resp.json()["id"]
    await client.put(f"{BASE}/{habit_id}", json={"archived": True})

    # Without flag — should not appear
    response_default = await client.get(BASE)
    ids_default = [h["id"] for h in response_default.json()]
    assert habit_id not in ids_default

    # With flag — should appear
    response_all = await client.get(BASE, params={"include_archived": "true"})
    assert response_all.status_code == 200
    ids_all = [h["id"] for h in response_all.json()]
    assert habit_id in ids_all


@pytest.mark.asyncio
async def test_toggle_completion_marks_completed(client):
    create_resp = await client.post(BASE, json={"name": "Exercise"})
    habit_id = create_resp.json()["id"]

    date_str = date.today().isoformat()
    response = await client.post(
        f"{BASE}/{habit_id}/complete",
        json={"date": date_str},
    )
    assert response.status_code == 200
    # Completions endpoint should now include this date
    completions_resp = await client.get(f"{BASE}/completions")
    assert completions_resp.status_code == 200
    completions = completions_resp.json()
    str_id = str(habit_id)
    assert str_id in completions
    assert date_str in completions[str_id]


@pytest.mark.asyncio
async def test_toggle_completion_reverts_on_second_call(client):
    create_resp = await client.post(BASE, json={"name": "Yoga"})
    habit_id = create_resp.json()["id"]
    date_str = date.today().isoformat()
    payload = {"date": date_str}

    # First toggle — mark complete
    await client.post(f"{BASE}/{habit_id}/complete", json=payload)
    # Second toggle — revert
    await client.post(f"{BASE}/{habit_id}/complete", json=payload)

    completions_resp = await client.get(f"{BASE}/completions")
    completions = completions_resp.json()
    str_id = str(habit_id)
    dates = completions.get(str_id, [])
    assert date_str not in dates


@pytest.mark.asyncio
async def test_get_habit_completions_returns_dict(client):
    response = await client.get(f"{BASE}/completions")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)


@pytest.mark.asyncio
async def test_delete_habit_returns_204(client):
    create_resp = await client.post(BASE, json={"name": "Temp Habit"})
    habit_id = create_resp.json()["id"]

    delete_resp = await client.delete(f"{BASE}/{habit_id}")
    assert delete_resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_habit_then_get_returns_404(client):
    create_resp = await client.post(BASE, json={"name": "Gone Habit"})
    habit_id = create_resp.json()["id"]

    await client.delete(f"{BASE}/{habit_id}")

    get_resp = await client.get(f"{BASE}/{habit_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_habit_returns_404(client):
    response = await client.delete(f"{BASE}/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_toggle_completion_nonexistent_habit_returns_404(client):
    response = await client.post(
        f"{BASE}/99999/complete",
        json={"date": date.today().isoformat()},
    )
    assert response.status_code == 404
