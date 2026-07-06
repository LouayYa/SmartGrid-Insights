"""Integration tests for the Data Ingestion Service.

Usage:
    python test_endpoints.py                                    # localhost
    python test_endpoints.py https://my-app.azurewebsites.net   # remote
"""
import sys

import requests

DEFAULT_BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"
EXPECTED_RECORDS = 260640

results = []


def record(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    status = "PASS" if ok else "FAIL"
    line = f"[{status}] {name}"
    if detail:
        line += f"  — {detail}"
    print(line)


def test_load(base_url: str) -> None:
    name = "POST /load"
    try:
        r = requests.post(f"{base_url}{API_PREFIX}/load", timeout=600)
        if r.status_code != 201:
            record(name, False, f"expected 201, got {r.status_code}: {r.text[:200]}")
            return
        body = r.json()
        loaded = body.get("records_loaded")
        if loaded != EXPECTED_RECORDS:
            record(name, False, f"expected records_loaded={EXPECTED_RECORDS}, got {loaded}")
            return
        if body.get("status") != "success":
            record(name, False, f"expected status='success', got {body.get('status')!r}")
            return
        record(name, True, f"records_loaded={loaded}")
    except Exception as exc:
        record(name, False, f"exception: {exc}")


def test_get_by_date(base_url: str) -> None:
    name = "GET /consumption?start_date=1/1/07&end_date=1/1/07"
    try:
        r = requests.get(
            f"{base_url}{API_PREFIX}/consumption",
            params={"start_date": "1/1/07", "end_date": "1/1/07"},
            timeout=120,
        )
        if r.status_code != 200:
            record(name, False, f"expected 200, got {r.status_code}: {r.text[:200]}")
            return
        body = r.json()
        if not isinstance(body, list) or len(body) == 0:
            record(name, False, f"expected non-empty list, got {type(body).__name__} len={len(body) if isinstance(body, list) else 'n/a'}")
            return
        record(name, True, f"{len(body)} records")
    except Exception as exc:
        record(name, False, f"exception: {exc}")


def test_get_limit(base_url: str) -> None:
    name = "GET /consumption?limit=5"
    try:
        r = requests.get(
            f"{base_url}{API_PREFIX}/consumption",
            params={"limit": 5},
            timeout=60,
        )
        if r.status_code != 200:
            record(name, False, f"expected 200, got {r.status_code}: {r.text[:200]}")
            return
        body = r.json()
        if not isinstance(body, list) or len(body) != 5:
            record(name, False, f"expected 5 records, got {len(body) if isinstance(body, list) else body!r}")
            return
        record(name, True, "5 records")
    except Exception as exc:
        record(name, False, f"exception: {exc}")


def test_create(base_url: str) -> int | None:
    name = "POST /consumption"
    payload = {
        "Date": "13/4/2026",
        "Time": "12:00:00",
        "Global_active_power": 1.23,
        "Global_reactive_power": 0.1,
        "Voltage": 240.0,
        "Global_intensity": 5.0,
        "Sub_metering_1": 0.0,
        "Sub_metering_2": 1.0,
        "Sub_metering_3": 17.0,
    }
    try:
        r = requests.post(
            f"{base_url}{API_PREFIX}/consumption",
            json=payload,
            timeout=30,
        )
        if r.status_code != 201:
            record(name, False, f"expected 201, got {r.status_code}: {r.text[:200]}")
            return None
        body = r.json()
        if body.get("status") != "created":
            record(name, False, f"expected status='created', got {body.get('status')!r}")
            return None
        new_id = body.get("id")
        if not isinstance(new_id, int):
            record(name, False, f"expected integer id, got {new_id!r}")
            return None
        record(name, True, f"id={new_id}")
        return new_id
    except Exception as exc:
        record(name, False, f"exception: {exc}")
        return None


def test_update(base_url: str, record_id: int) -> None:
    name = f"PUT /consumption/{record_id}"
    try:
        r = requests.put(
            f"{base_url}{API_PREFIX}/consumption/{record_id}",
            json={"Global_active_power": 9.99},
            timeout=30,
        )
        if r.status_code != 200:
            record(name, False, f"expected 200, got {r.status_code}: {r.text[:200]}")
            return
        body = r.json()
        if body.get("status") != "updated":
            record(name, False, f"expected status='updated', got {body.get('status')!r}")
            return
        if body.get("id") != record_id:
            record(name, False, f"expected id={record_id}, got {body.get('id')!r}")
            return
        record(name, True, "Global_active_power=9.99")
    except Exception as exc:
        record(name, False, f"exception: {exc}")


def test_delete(base_url: str, record_id: int) -> None:
    name = f"DELETE /consumption/{record_id}"
    try:
        r = requests.delete(
            f"{base_url}{API_PREFIX}/consumption/{record_id}",
            timeout=30,
        )
        if r.status_code != 200:
            record(name, False, f"expected 200, got {r.status_code}: {r.text[:200]}")
            return
        body = r.json()
        if body.get("status") != "deleted":
            record(name, False, f"expected status='deleted', got {body.get('status')!r}")
            return
        if body.get("id") != record_id:
            record(name, False, f"expected id={record_id}, got {body.get('id')!r}")
            return
        record(name, True)
    except Exception as exc:
        record(name, False, f"exception: {exc}")


def test_delete_missing(base_url: str, record_id: int) -> None:
    name = f"DELETE /consumption/{record_id} (already deleted)"
    try:
        r = requests.delete(
            f"{base_url}{API_PREFIX}/consumption/{record_id}",
            timeout=30,
        )
        if r.status_code != 404:
            record(name, False, f"expected 404, got {r.status_code}: {r.text[:200]}")
            return
        record(name, True, "404 as expected")
    except Exception as exc:
        record(name, False, f"exception: {exc}")


def main() -> int:
    base_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE_URL
    base_url = base_url.rstrip("/")
    print(f"Testing against: {base_url}\n")

    test_load(base_url)
    test_get_by_date(base_url)
    test_get_limit(base_url)
    new_id = test_create(base_url)
    if new_id is not None:
        test_update(base_url, new_id)
        test_delete(base_url, new_id)
        test_delete_missing(base_url, new_id)
    else:
        for skipped in (
            "PUT /consumption/{id}",
            "DELETE /consumption/{id}",
            "DELETE /consumption/{id} (already deleted)",
        ):
            record(skipped, False, "skipped — create failed")

    total = len(results)
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n{passed}/{total} passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
