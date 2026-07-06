import requests
from config import METER_SERVICE_URL, COLLECTION_SERVICE_URL, ANALYSIS_SERVICE_URL

TIMEOUT = 300 # 300 seconds timeout for all requests

def list_meters():
    r = requests.get(f"{METER_SERVICE_URL}/meters", timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def create_meter(name: str):
    r = requests.post(
        f"{METER_SERVICE_URL}/meters",
        json={"name": name},
        timeout=TIMEOUT
    )
    r.raise_for_status()
    return r.json()

def update_meter(meter_id: int, name: str):
    r = requests.put(
        f"{METER_SERVICE_URL}/meters/{meter_id}",
        json={"name": name},
        timeout=TIMEOUT
    )
    r.raise_for_status()
    return r.json()

def delete_meter(meter_id: int):
    r = requests.delete(f"{METER_SERVICE_URL}/meters/{meter_id}", timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def delete_readings_by_meter(meter_id: int):
    r = requests.delete(f"{COLLECTION_SERVICE_URL}/readings/by-meter/{meter_id}", timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def trigger_simulation(meter_id: int, start_date=None, end_date=None):
    payload = {}
    if start_date:
        payload["start_date"] = start_date
    if end_date:
        payload["end_date"] = end_date

    r = requests.post(
        f"{COLLECTION_SERVICE_URL}/simulate/{meter_id}",
        json=payload,
        timeout=TIMEOUT
    )
    r.raise_for_status()
    return r.json()

def get_readings(meter_id=None, start_date=None, end_date=None):
    params = {}
    if meter_id:
        params["meter_id"] = meter_id
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date

    r = requests.get(
        f"{COLLECTION_SERVICE_URL}/readings",
        params=params,
        timeout=TIMEOUT
    )
    r.raise_for_status()
    return r.json()

def get_averages(meter_id: int, start_date: str, end_date: str):
    r = requests.get(
        f"{ANALYSIS_SERVICE_URL}/analysis/averages/{meter_id}",
        params={
            "start_date": start_date,
            "end_date": end_date,
        },
        timeout=TIMEOUT
    )
    r.raise_for_status()
    return r.json()

def get_peaks(meter_id: int, start_date: str, end_date: str):
    r = requests.get(
        f"{ANALYSIS_SERVICE_URL}/analysis/peaks/{meter_id}",
        params={
            "start_date": start_date,
            "end_date": end_date,
        },
        timeout=TIMEOUT
    )
    r.raise_for_status()
    return r.json()

def get_categories(meter_id: int, start_date: str, end_date: str):
    r = requests.get(
        f"{ANALYSIS_SERVICE_URL}/analysis/categories/{meter_id}",
        params={
            "start_date": start_date,
            "end_date": end_date,
        },
        timeout=TIMEOUT
    )
    r.raise_for_status()
    return r.json()