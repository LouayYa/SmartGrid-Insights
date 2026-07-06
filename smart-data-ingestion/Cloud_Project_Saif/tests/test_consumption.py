API_PREFIX = "/api/v1"


def make_payload(date="1/1/07", time="00:00:00", **overrides):
    payload = {
        "Date": date,
        "Time": time,
        "Global_active_power": 1.23,
        "Global_reactive_power": 0.1,
        "Voltage": 240.0,
        "Global_intensity": 5.0,
        "Sub_metering_1": 0.0,
        "Sub_metering_2": 1.0,
        "Sub_metering_3": 17.0,
    }
    payload.update(overrides)
    return payload


def test_create_consumption(client):
    response = client.post(f"{API_PREFIX}/consumption", json=make_payload())

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "created"
    assert isinstance(data["id"], int)


def test_create_consumption_requires_date_and_time(client):
    payload = make_payload()
    del payload["Date"]

    response = client.post(f"{API_PREFIX}/consumption", json=payload)

    assert response.status_code == 422


def test_list_consumption_empty(client):
    response = client.get(f"{API_PREFIX}/consumption")

    assert response.status_code == 200
    assert response.json() == []


def test_list_consumption_respects_limit(client):
    for i in range(3):
        client.post(f"{API_PREFIX}/consumption", json=make_payload(time=f"0{i}:00:00"))

    response = client.get(f"{API_PREFIX}/consumption", params={"limit": 2})

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_consumption_filters_by_date_range(client):
    client.post(f"{API_PREFIX}/consumption", json=make_payload(date="1/1/07"))
    client.post(f"{API_PREFIX}/consumption", json=make_payload(date="15/1/07"))
    client.post(f"{API_PREFIX}/consumption", json=make_payload(date="1/2/07"))

    response = client.get(
        f"{API_PREFIX}/consumption",
        params={"start_date": "1/1/07", "end_date": "31/1/07"},
    )

    assert response.status_code == 200
    dates = [row["Date"] for row in response.json()]
    assert dates == ["1/1/07", "15/1/07"]


def test_list_consumption_requires_both_date_bounds(client):
    response = client.get(f"{API_PREFIX}/consumption", params={"start_date": "1/1/07"})

    assert response.status_code == 400


def test_list_consumption_rejects_inverted_range(client):
    response = client.get(
        f"{API_PREFIX}/consumption",
        params={"start_date": "31/1/07", "end_date": "1/1/07"},
    )

    assert response.status_code == 400


def test_list_consumption_rejects_bad_date_format(client):
    response = client.get(
        f"{API_PREFIX}/consumption",
        params={"start_date": "not-a-date", "end_date": "1/1/07"},
    )

    assert response.status_code == 400


def test_update_consumption(client):
    create_resp = client.post(f"{API_PREFIX}/consumption", json=make_payload())
    record_id = create_resp.json()["id"]

    response = client.put(
        f"{API_PREFIX}/consumption/{record_id}",
        json={"Global_active_power": 9.99},
    )

    assert response.status_code == 200
    assert response.json() == {"id": record_id, "status": "updated"}

    listed = client.get(f"{API_PREFIX}/consumption").json()
    updated = next(row for row in listed if row["ID"] == record_id)
    assert updated["Global_active_power"] == 9.99


def test_update_consumption_not_found(client):
    response = client.put(
        f"{API_PREFIX}/consumption/999999",
        json={"Global_active_power": 1.0},
    )

    assert response.status_code == 404


def test_delete_consumption(client):
    create_resp = client.post(f"{API_PREFIX}/consumption", json=make_payload())
    record_id = create_resp.json()["id"]

    response = client.delete(f"{API_PREFIX}/consumption/{record_id}")

    assert response.status_code == 200
    assert response.json() == {"id": record_id, "status": "deleted"}

    listed = client.get(f"{API_PREFIX}/consumption").json()
    assert all(row["ID"] != record_id for row in listed)


def test_delete_consumption_not_found(client):
    response = client.delete(f"{API_PREFIX}/consumption/999999")

    assert response.status_code == 404
