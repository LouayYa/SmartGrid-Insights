import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


class FakeResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json_data = json_data if json_data is not None else []

    def json(self):
        return self._json_data


@pytest.fixture
def mock_readings(monkeypatch):
    """Patch app.main.requests.get to return canned readings instead of hitting
    the Data Collection Service over the network."""

    def _apply(status_code=200, json_data=None):
        def fake_get(url, params=None, timeout=None):
            return FakeResponse(status_code=status_code, json_data=json_data)

        monkeypatch.setattr("app.main.requests.get", fake_get)

    return _apply
