import logging
import os
import time
from collections import defaultdict
from datetime import datetime
from typing import List

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from app.schemas import CategoryBreakdown, DailyAggregate, DailyAverage, PeakHourResponse

load_dotenv()

# When set, every endpoint except the open paths requires this value in the
# X-API-Key header. Unset (default) disables auth — local dev and tests.
# The same key is forwarded on calls to the Data Collection Service.
API_KEY = os.getenv("SMARTGRID_API_KEY", "")
OPEN_PATHS = {"/", "/health", "/docs", "/openapi.json"}

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("analysis")

app = FastAPI(title="Data Analysis Service", version="1.0.0")

DATA_COLLECTION_URL = os.getenv("DATA_COLLECTION_URL", "http://localhost:8002")

# The collection service paginates GET /readings; page through it so
# analyses always see the full date range.
PAGE_SIZE = 50000


@app.middleware("http")
async def require_api_key(request: Request, call_next):
    if API_KEY and request.url.path not in OPEN_PATHS:
        if request.headers.get("X-API-Key") != API_KEY:
            return JSONResponse(status_code=401, content={"detail": "Invalid or missing API key"})
    return await call_next(request)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s -> %d (%.1f ms)",
        request.method, request.url.path, response.status_code, elapsed_ms,
    )
    return response


@app.get("/health")
def health():
    return {"status": "ok"}


def fetch_readings(meter_id: int, start_date: str, end_date: str) -> list:
    readings = []
    offset = 0
    while True:
        params = {
            "meter_id": meter_id,
            "start_date": start_date,
            "end_date": end_date,
            "limit": PAGE_SIZE,
            "offset": offset,
        }
        try:
            resp = requests.get(
                f"{DATA_COLLECTION_URL}/readings",
                params=params,
                headers={"X-API-Key": API_KEY},
                timeout=30,
            )
        except requests.RequestException as exc:
            raise HTTPException(status_code=502, detail=f"Data Collection Service unreachable: {exc}")
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Failed to fetch readings from Data Collection Service")
        page = resp.json()
        readings.extend(page)
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    if not readings:
        raise HTTPException(status_code=404, detail="No readings found for the given meter and date range")
    return readings


@app.get("/analysis/averages/{meter_id}", response_model=List[DailyAverage])
def get_daily_averages(
    meter_id: int,
    start_date: str = Query(...),
    end_date: str = Query(...),
):
    readings = fetch_readings(meter_id, start_date, end_date)

    daily_sums = defaultdict(lambda: {"total": 0.0, "count": 0})
    for r in readings:
        date_str = datetime.fromisoformat(r["timestamp"]).strftime("%Y-%m-%d")
        daily_sums[date_str]["total"] += r["global_active_power"]
        daily_sums[date_str]["count"] += 1

    return [
        DailyAverage(date=date, avg_power=round(vals["total"] / vals["count"], 4))
        for date, vals in sorted(daily_sums.items())
    ]


@app.get("/analysis/peaks/{meter_id}", response_model=PeakHourResponse)
def get_peak_hour(
    meter_id: int,
    start_date: str = Query(...),
    end_date: str = Query(...),
):
    readings = fetch_readings(meter_id, start_date, end_date)

    hourly_sums = defaultdict(lambda: {"total": 0.0, "count": 0})
    for r in readings:
        hour = datetime.fromisoformat(r["timestamp"]).hour
        hourly_sums[hour]["total"] += r["global_active_power"]
        hourly_sums[hour]["count"] += 1

    peak_hour = max(hourly_sums, key=lambda h: hourly_sums[h]["total"] / hourly_sums[h]["count"])
    avg = hourly_sums[peak_hour]["total"] / hourly_sums[peak_hour]["count"]

    return PeakHourResponse(peak_hour=peak_hour, avg_power=round(avg, 4))


@app.get("/analysis/daily/{meter_id}", response_model=List[DailyAggregate])
def get_precomputed_daily(
    meter_id: int,
    start_date: str = Query(...),
    end_date: str = Query(...),
):
    """Serve the Airflow-precomputed daily aggregates.

    Unlike the on-demand endpoints above (which pull raw readings and
    aggregate per request), this reads the analytics_daily table that the
    daily batch pipeline maintains — constant-time regardless of range size.
    """
    params = {"meter_id": meter_id, "start_date": start_date, "end_date": end_date}
    try:
        resp = requests.get(
            f"{DATA_COLLECTION_URL}/aggregates/daily",
            params=params,
            headers={"X-API-Key": API_KEY},
            timeout=30,
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Data Collection Service unreachable: {exc}")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch aggregates from Data Collection Service")
    rows = resp.json()
    if not rows:
        raise HTTPException(
            status_code=404,
            detail="No precomputed aggregates for the given meter and range — has the daily_consumption_aggregates DAG run?",
        )
    return rows


@app.get("/analysis/categories/{meter_id}", response_model=CategoryBreakdown)
def get_category_breakdown(
    meter_id: int,
    start_date: str = Query(...),
    end_date: str = Query(...),
):
    readings = fetch_readings(meter_id, start_date, end_date)

    kitchen = sum(r["sub_metering_1"] for r in readings)
    laundry = sum(r["sub_metering_2"] for r in readings)
    water_heater_ac = sum(r["sub_metering_3"] for r in readings)

    return CategoryBreakdown(
        kitchen=round(kitchen, 4),
        laundry=round(laundry, 4),
        water_heater_ac=round(water_heater_ac, 4),
    )
