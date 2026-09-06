from httpx import AsyncClient

BASE = "/api/v1/countdowns"


async def test_countdown_crud(client: AsyncClient) -> None:
    created = await client.post(BASE, json={"title": "Wicked 10K", "date": "2026-10-31"})
    assert created.status_code == 201
    body = created.json()
    assert body["title"] == "Wicked 10K"
    assert body["date"] == "2026-10-31"

    listed = await client.get(BASE)
    assert listed.status_code == 200
    assert any(c["id"] == body["id"] for c in listed.json())

    updated = await client.put(f"{BASE}/{body['id']}", json={"date": "2026-11-01"})
    assert updated.status_code == 200
    assert updated.json()["date"] == "2026-11-01"
    assert updated.json()["title"] == "Wicked 10K"

    deleted = await client.delete(f"{BASE}/{body['id']}")
    assert deleted.status_code == 204
    assert (await client.delete(f"{BASE}/{body['id']}")).status_code == 404


async def test_countdowns_sorted_by_date(client: AsyncClient) -> None:
    later = await client.post(BASE, json={"title": "Marathon", "date": "2027-09-25"})
    earlier = await client.post(BASE, json={"title": "Flying Pig", "date": "2027-05-02"})
    dates = [c["date"] for c in (await client.get(BASE)).json()]
    assert dates == sorted(dates)
    for resp in (later, earlier):
        await client.delete(f"{BASE}/{resp.json()['id']}")


async def test_countdown_rejects_bad_date(client: AsyncClient) -> None:
    resp = await client.post(BASE, json={"title": "Oops", "date": "31/10/2026"})
    assert resp.status_code == 422
