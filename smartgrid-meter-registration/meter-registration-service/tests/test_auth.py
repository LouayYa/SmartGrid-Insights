import app as meter_app


def test_requires_api_key_when_configured(client, monkeypatch):
    monkeypatch.setattr(meter_app, "API_KEY", "sekrit")

    assert client.get("/meters").status_code == 401
    assert client.get("/meters", headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.get("/meters", headers={"X-API-Key": "sekrit"}).status_code == 200
    # Probes stay open.
    assert client.get("/health").status_code == 200


def test_auth_disabled_when_key_unset(client):
    assert client.get("/meters").status_code == 200
