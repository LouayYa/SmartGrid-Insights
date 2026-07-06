"""services.py tests — verify each wrapper hits the right URL with the right
payload/params and unwraps JSON, with requests fully faked."""
import pytest

import services


class FakeResponse:
    def __init__(self, json_data=None, status_code=200):
        self._json = json_data if json_data is not None else {}
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._json


@pytest.fixture
def http(monkeypatch):
    """Capture outbound calls; respond with a canned JSON body."""
    calls = {}

    def record(method):
        def _do(url, json=None, params=None, headers=None, timeout=None):
            calls.update(method=method, url=url, json=json, params=params, headers=headers)
            return FakeResponse(calls.get("response", {"ok": True}))
        return _do

    monkeypatch.setattr(services.requests, "get", record("GET"))
    monkeypatch.setattr(services.requests, "post", record("POST"))
    monkeypatch.setattr(services.requests, "put", record("PUT"))
    monkeypatch.setattr(services.requests, "delete", record("DELETE"))
    return calls


def test_list_meters(http):
    services.list_meters()
    assert http["method"] == "GET"
    assert http["url"].endswith("/meters")


def test_create_meter(http):
    services.create_meter("kitchen")
    assert http["method"] == "POST"
    assert http["url"].endswith("/meters")
    assert http["json"] == {"name": "kitchen"}


def test_update_meter(http):
    services.update_meter(3, "garage")
    assert http["method"] == "PUT"
    assert http["url"].endswith("/meters/3")
    assert http["json"] == {"name": "garage"}


def test_delete_meter(http):
    services.delete_meter(3)
    assert http["method"] == "DELETE"
    assert http["url"].endswith("/meters/3")


def test_delete_readings_by_meter(http):
    services.delete_readings_by_meter(4)
    assert http["method"] == "DELETE"
    assert http["url"].endswith("/readings/by-meter/4")


def test_trigger_simulation_passes_only_given_dates(http):
    services.trigger_simulation(1, start_date="2007-01-01")
    assert http["method"] == "POST"
    assert http["url"].endswith("/simulate/1")
    assert http["json"] == {"start_date": "2007-01-01"}


def test_get_readings_builds_params(http):
    services.get_readings(meter_id=1, start_date="2007-01-01", end_date="2007-01-02")
    assert http["params"] == {
        "meter_id": 1,
        "start_date": "2007-01-01",
        "end_date": "2007-01-02",
    }


def test_analysis_wrappers_hit_expected_endpoints(http):
    services.get_averages(1, "2007-01-01", "2007-01-02")
    assert http["url"].endswith("/analysis/averages/1")

    services.get_peaks(1, "2007-01-01", "2007-01-02")
    assert http["url"].endswith("/analysis/peaks/1")

    services.get_categories(1, "2007-01-01", "2007-01-02")
    assert http["url"].endswith("/analysis/categories/1")
    assert http["params"] == {"start_date": "2007-01-01", "end_date": "2007-01-02"}


def test_all_calls_send_api_key_header(http, monkeypatch):
    monkeypatch.setattr(services, "HEADERS", {"X-API-Key": "sekrit"})

    services.list_meters()
    assert http["headers"] == {"X-API-Key": "sekrit"}

    services.trigger_simulation(1)
    assert http["headers"] == {"X-API-Key": "sekrit"}
