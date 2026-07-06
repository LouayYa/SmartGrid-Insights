def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_create_meter(client):
    response = client.post("/meters", json={"name": "Meter A"})

    assert response.status_code == 201
    data = response.get_json()
    assert data["name"] == "Meter A"
    assert isinstance(data["meter_id"], int)
    assert "created_at" in data


def test_create_meter_requires_name(client):
    response = client.post("/meters", json={"name": "  "})

    assert response.status_code == 400
    assert response.get_json() == {"error": "name is required"}


def test_create_meter_rejects_duplicate_name(client):
    client.post("/meters", json={"name": "Meter A"})

    response = client.post("/meters", json={"name": "Meter A"})

    assert response.status_code == 409
    assert response.get_json() == {"error": "meter name already exists"}


def test_get_all_meters(client):
    client.post("/meters", json={"name": "Meter A"})
    client.post("/meters", json={"name": "Meter B"})

    response = client.get("/meters")

    assert response.status_code == 200
    names = [m["name"] for m in response.get_json()]
    assert names == ["Meter A", "Meter B"]


def test_get_meter(client):
    created = client.post("/meters", json={"name": "Meter A"}).get_json()

    response = client.get(f"/meters/{created['meter_id']}")

    assert response.status_code == 200
    assert response.get_json()["name"] == "Meter A"


def test_get_meter_not_found(client):
    response = client.get("/meters/999999")

    assert response.status_code == 404
    assert response.get_json() == {"error": "meter not found"}


def test_update_meter(client):
    created = client.post("/meters", json={"name": "Meter A"}).get_json()

    response = client.put(f"/meters/{created['meter_id']}", json={"name": "Meter A2"})

    assert response.status_code == 200
    assert response.get_json() == {
        "meter_id": created["meter_id"],
        "name": "Meter A2",
        "status": "updated",
    }


def test_update_meter_not_found(client):
    response = client.put("/meters/999999", json={"name": "Meter X"})

    assert response.status_code == 404


def test_update_meter_requires_name(client):
    created = client.post("/meters", json={"name": "Meter A"}).get_json()

    response = client.put(f"/meters/{created['meter_id']}", json={"name": "  "})

    assert response.status_code == 400


def test_update_meter_rejects_duplicate_name(client):
    client.post("/meters", json={"name": "Meter A"})
    meter_b = client.post("/meters", json={"name": "Meter B"}).get_json()

    response = client.put(f"/meters/{meter_b['meter_id']}", json={"name": "Meter A"})

    assert response.status_code == 409


def test_update_meter_allows_same_name(client):
    created = client.post("/meters", json={"name": "Meter A"}).get_json()

    response = client.put(f"/meters/{created['meter_id']}", json={"name": "Meter A"})

    assert response.status_code == 200


def test_delete_meter(client):
    created = client.post("/meters", json={"name": "Meter A"}).get_json()

    response = client.delete(f"/meters/{created['meter_id']}")

    assert response.status_code == 200
    assert response.get_json() == {"meter_id": created["meter_id"], "status": "deleted"}

    listed = client.get("/meters").get_json()
    assert listed == []


def test_delete_meter_not_found(client):
    response = client.delete("/meters/999999")

    assert response.status_code == 404
