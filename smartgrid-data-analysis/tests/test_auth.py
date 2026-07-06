from tests.test_analysis import SAMPLE_READINGS


def test_requires_api_key_when_configured(client, mock_readings, monkeypatch):
    monkeypatch.setattr("app.main.API_KEY", "sekrit")
    mock_readings(json_data=SAMPLE_READINGS)

    params = {"start_date": "2007-01-01", "end_date": "2007-01-02"}
    assert client.get("/analysis/averages/1", params=params).status_code == 401
    assert client.get(
        "/analysis/averages/1", params=params, headers={"X-API-Key": "sekrit"}
    ).status_code == 200
    # Probes stay open.
    assert client.get("/health").status_code == 200


def test_auth_disabled_when_key_unset(client, mock_readings):
    mock_readings(json_data=SAMPLE_READINGS)
    params = {"start_date": "2007-01-01", "end_date": "2007-01-02"}
    assert client.get("/analysis/averages/1", params=params).status_code == 200
