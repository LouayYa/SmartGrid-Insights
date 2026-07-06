SAMPLE_READINGS = [
    {
        "timestamp": "2007-01-01T08:00:00",
        "global_active_power": 1.0,
        "sub_metering_1": 1.0,
        "sub_metering_2": 2.0,
        "sub_metering_3": 3.0,
    },
    {
        "timestamp": "2007-01-01T20:00:00",
        "global_active_power": 3.0,
        "sub_metering_1": 0.0,
        "sub_metering_2": 1.0,
        "sub_metering_3": 2.0,
    },
    {
        "timestamp": "2007-01-02T20:00:00",
        "global_active_power": 5.0,
        "sub_metering_1": 2.0,
        "sub_metering_2": 0.0,
        "sub_metering_3": 1.0,
    },
]


def test_get_daily_averages(client, mock_readings):
    mock_readings(json_data=SAMPLE_READINGS)

    response = client.get(
        "/analysis/averages/1",
        params={"start_date": "2007-01-01", "end_date": "2007-01-02"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data == [
        {"date": "2007-01-01", "avg_power": 2.0},
        {"date": "2007-01-02", "avg_power": 5.0},
    ]


def test_get_peak_hour(client, mock_readings):
    mock_readings(json_data=SAMPLE_READINGS)

    response = client.get(
        "/analysis/peaks/1",
        params={"start_date": "2007-01-01", "end_date": "2007-01-02"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data == {"peak_hour": 20, "avg_power": 4.0}


def test_get_category_breakdown(client, mock_readings):
    mock_readings(json_data=SAMPLE_READINGS)

    response = client.get(
        "/analysis/categories/1",
        params={"start_date": "2007-01-01", "end_date": "2007-01-02"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data == {"kitchen": 3.0, "laundry": 3.0, "water_heater_ac": 6.0}


def test_no_readings_returns_404(client, mock_readings):
    mock_readings(json_data=[])

    response = client.get(
        "/analysis/averages/1",
        params={"start_date": "2007-01-01", "end_date": "2007-01-02"},
    )

    assert response.status_code == 404


def test_upstream_failure_returns_502(client, mock_readings):
    mock_readings(status_code=500, json_data=[])

    response = client.get(
        "/analysis/averages/1",
        params={"start_date": "2007-01-01", "end_date": "2007-01-02"},
    )

    assert response.status_code == 502


def test_missing_query_params_returns_422(client):
    response = client.get("/analysis/averages/1")

    assert response.status_code == 422


AGGREGATE_ROW = {
    "meter_id": 1,
    "day": "2007-01-01",
    "avg_power": 1.5,
    "peak_power": 3.2,
    "kitchen_wh": 10.0,
    "laundry_wh": 5.0,
    "water_heater_ac_wh": 20.0,
    "samples": 1440,
    "computed_at": "2026-07-06T02:00:00",
}


def test_precomputed_daily_passthrough(client, mock_readings):
    mock_readings(json_data=[AGGREGATE_ROW])

    response = client.get(
        "/analysis/daily/1",
        params={"start_date": "2007-01-01", "end_date": "2007-01-02"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["day"] == "2007-01-01"
    assert data[0]["avg_power"] == 1.5
    # computed_at is internal to the batch table; the schema strips it.
    assert "computed_at" not in data[0]


def test_precomputed_daily_404_when_dag_has_not_run(client, mock_readings):
    mock_readings(json_data=[])

    response = client.get(
        "/analysis/daily/1",
        params={"start_date": "2007-01-01", "end_date": "2007-01-02"},
    )

    assert response.status_code == 404
    assert "DAG" in response.json()["detail"]


def test_collection_unreachable_returns_502(client, monkeypatch):
    import requests as requests_lib

    def fake_get(url, params=None, timeout=None):
        raise requests_lib.ConnectionError("down")

    monkeypatch.setattr("app.main.requests.get", fake_get)

    response = client.get(
        "/analysis/averages/1",
        params={"start_date": "2007-01-01", "end_date": "2007-01-02"},
    )

    assert response.status_code == 502


def test_fetch_paginates_until_short_page(client, monkeypatch):
    """Analyses must see every page of readings, not just the first."""
    monkeypatch.setattr("app.main.PAGE_SIZE", 2)

    pages = {0: SAMPLE_READINGS[:2], 2: SAMPLE_READINGS[2:]}
    requested_offsets = []

    class FakeResponse:
        def __init__(self, data):
            self.status_code = 200
            self._data = data

        def json(self):
            return self._data

    def fake_get(url, params=None, timeout=None):
        requested_offsets.append(params["offset"])
        return FakeResponse(pages.get(params["offset"], []))

    monkeypatch.setattr("app.main.requests.get", fake_get)

    response = client.get(
        "/analysis/categories/1",
        params={"start_date": "2007-01-01", "end_date": "2007-01-02"},
    )

    assert response.status_code == 200
    # All three readings (across two pages) were aggregated.
    assert response.json() == {"kitchen": 3.0, "laundry": 3.0, "water_heater_ac": 6.0}
    assert requested_offsets == [0, 2]


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
