"""UI route tests.

All outbound HTTP calls (services.py) are monkeypatched — these tests
exercise routing, validation, flash messaging, and the async simulation
job store without any backend running.
"""
import time

import app as webui

METERS = [
    {"meter_id": 1, "name": "kitchen", "created_at": "2026-01-01T00:00:00"},
]
READINGS = [
    {
        "reading_id": 1,
        "meter_id": 1,
        "timestamp": "2007-01-05T10:00:00",
        "global_active_power": 1.5,
        "voltage": 240.0,
        "sub_metering_1": 0.0,
        "sub_metering_2": 1.0,
        "sub_metering_3": 17.0,
    },
]


def test_index_lists_meters(client, monkeypatch):
    monkeypatch.setattr(webui, "list_meters", lambda: METERS)

    response = client.get("/")

    assert response.status_code == 200
    assert b"kitchen" in response.data


def test_index_survives_meter_service_outage(client, monkeypatch):
    def boom():
        raise RuntimeError("meter service down")

    monkeypatch.setattr(webui, "list_meters", boom)

    response = client.get("/")

    assert response.status_code == 200
    assert b"Failed to load meters" in response.data


def test_index_shows_readings_for_valid_filter(client, monkeypatch):
    monkeypatch.setattr(webui, "list_meters", lambda: METERS)
    captured = {}

    def fake_get_readings(meter_id=None, start_date=None, end_date=None):
        captured.update(meter_id=meter_id, start_date=start_date, end_date=end_date)
        return READINGS

    monkeypatch.setattr(webui, "get_readings", fake_get_readings)

    response = client.get(
        "/", query_string={"meter_id": "1", "start_date": "2007-01-01", "end_date": "2007-01-10"}
    )

    assert response.status_code == 200
    assert captured == {"meter_id": 1, "start_date": "2007-01-01", "end_date": "2007-01-10"}


def test_index_rejects_out_of_dataset_dates(client, monkeypatch):
    monkeypatch.setattr(webui, "list_meters", lambda: METERS)

    response = client.get(
        "/", query_string={"meter_id": "1", "start_date": "2010-01-01", "end_date": "2010-01-10"}
    )

    assert response.status_code == 200
    assert b"Dates must be between" in response.data


def test_create_meter(client, monkeypatch):
    created = {}
    monkeypatch.setattr(webui, "list_meters", lambda: [])
    monkeypatch.setattr(webui, "create_meter", lambda name: created.update(name=name))

    response = client.post("/meters/create", data={"name": "garage"}, follow_redirects=True)

    assert response.status_code == 200
    assert created == {"name": "garage"}
    assert b"Meter created successfully" in response.data


def test_create_meter_requires_name(client, monkeypatch):
    monkeypatch.setattr(webui, "list_meters", lambda: [])

    response = client.post("/meters/create", data={"name": "  "}, follow_redirects=True)

    assert b"Meter name is required" in response.data


def test_delete_meter_also_clears_readings(client, monkeypatch):
    calls = []
    monkeypatch.setattr(webui, "list_meters", lambda: [])
    monkeypatch.setattr(webui, "delete_readings_by_meter", lambda mid: calls.append(("readings", mid)))
    monkeypatch.setattr(webui, "delete_meter", lambda mid: calls.append(("meter", mid)))

    response = client.post("/meters/delete", data={"meter_id": "1"}, follow_redirects=True)

    assert response.status_code == 200
    assert calls == [("readings", 1), ("meter", 1)]


def test_simulate_runs_job_to_completion(client, monkeypatch):
    monkeypatch.setattr(webui, "list_meters", lambda: METERS)
    monkeypatch.setattr(
        webui, "trigger_simulation",
        lambda meter_id, start_date=None, end_date=None: {"records_published": 42},
    )

    response = client.post(
        "/simulate",
        data={"meter_id": "1", "start_date": "2007-01-01", "end_date": "2007-01-02"},
    )

    assert response.status_code == 302
    job_id = response.location.split("sim_job=")[1]

    # The job runs in a background thread; wait briefly for it to finish.
    for _ in range(50):
        status = client.get(f"/simulate/status/{job_id}").get_json()
        if status["status"] != "running":
            break
        time.sleep(0.1)

    assert status["status"] == "done"
    assert "42" in status["message"]


def test_simulate_reports_failure(client, monkeypatch):
    def boom(meter_id, start_date=None, end_date=None):
        raise RuntimeError("collection service down")

    monkeypatch.setattr(webui, "trigger_simulation", boom)

    response = client.post("/simulate", data={"meter_id": "1"})
    job_id = response.location.split("sim_job=")[1]

    for _ in range(50):
        status = client.get(f"/simulate/status/{job_id}").get_json()
        if status["status"] != "running":
            break
        time.sleep(0.1)

    assert status["status"] == "error"
    assert "collection service down" in status["message"]


def test_simulate_requires_meter_id(client, monkeypatch):
    monkeypatch.setattr(webui, "list_meters", lambda: [])

    response = client.post("/simulate", data={}, follow_redirects=True)

    assert b"Meter ID is required" in response.data


def test_simulate_rejects_bad_dates(client, monkeypatch):
    monkeypatch.setattr(webui, "list_meters", lambda: [])

    response = client.post(
        "/simulate",
        data={"meter_id": "1", "start_date": "2010-01-01"},
        follow_redirects=True,
    )

    assert b"Simulation dates must be between" in response.data


def test_simulate_status_unknown_job(client):
    response = client.get("/simulate/status/nope")

    assert response.status_code == 404


def test_update_meter_route(client, monkeypatch):
    updated = {}
    monkeypatch.setattr(webui, "list_meters", lambda: [])
    monkeypatch.setattr(webui, "update_meter", lambda mid, name: updated.update(mid=mid, name=name))

    response = client.post(
        "/meters/update", data={"meter_id": "2", "name": "attic"}, follow_redirects=True
    )

    assert response.status_code == 200
    assert updated == {"mid": 2, "name": "attic"}
    assert b"Meter updated successfully" in response.data


def test_update_meter_requires_fields(client, monkeypatch):
    monkeypatch.setattr(webui, "list_meters", lambda: [])

    response = client.post("/meters/update", data={"meter_id": "2"}, follow_redirects=True)

    assert b"Meter ID and new name are required" in response.data


def test_delete_meter_requires_id(client, monkeypatch):
    monkeypatch.setattr(webui, "list_meters", lambda: [])

    response = client.post("/meters/delete", data={}, follow_redirects=True)

    assert b"Meter ID is required" in response.data


def test_analysis_averages_flow(client, monkeypatch):
    monkeypatch.setattr(webui, "list_meters", lambda: METERS)
    monkeypatch.setattr(webui, "get_readings", lambda **kw: READINGS)
    monkeypatch.setattr(
        webui, "get_averages",
        lambda mid, s, e: [{"date": "2007-01-05", "avg_power": 1.5}],
    )

    response = client.get("/", query_string={
        "meter_id": "1",
        "start_date": "2007-01-01",
        "end_date": "2007-01-10",
        "analysis_type": "averages",
    })

    assert response.status_code == 200
    assert b"2007-01-05" in response.data


def test_analysis_requires_all_fields(client, monkeypatch):
    monkeypatch.setattr(webui, "list_meters", lambda: METERS)

    response = client.get("/", query_string={"analysis_type": "peaks"})

    assert response.status_code == 200
    assert b"required for analysis" in response.data


def test_analysis_peaks_and_categories(client, monkeypatch):
    monkeypatch.setattr(webui, "list_meters", lambda: METERS)
    monkeypatch.setattr(webui, "get_readings", lambda **kw: READINGS)
    monkeypatch.setattr(webui, "get_peaks", lambda mid, s, e: {"peak_hour": 17, "avg_power": 2.0})
    monkeypatch.setattr(
        webui, "get_categories",
        lambda mid, s, e: {"kitchen": 1.0, "laundry": 2.0, "water_heater_ac": 3.0},
    )

    base = {"meter_id": "1", "start_date": "2007-01-01", "end_date": "2007-01-10"}
    peaks = client.get("/", query_string={**base, "analysis_type": "peaks"})
    categories = client.get("/", query_string={**base, "analysis_type": "categories"})

    assert peaks.status_code == 200
    assert categories.status_code == 200
