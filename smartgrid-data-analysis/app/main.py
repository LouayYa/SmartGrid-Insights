import os
from collections import defaultdict
from datetime import datetime
from typing import List

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query

from app.schemas import DailyAverage, PeakHourResponse, CategoryBreakdown

load_dotenv()

app = FastAPI(title="Data Analysis Service", version="1.0.0")

DATA_COLLECTION_URL = os.getenv("DATA_COLLECTION_URL", "http://localhost:8002")


def fetch_readings(meter_id: int, start_date: str, end_date: str) -> list:
    params = {
        "meter_id": meter_id,
        "start_date": start_date,
        "end_date": end_date,
    }
    try:
        resp = requests.get(f"{DATA_COLLECTION_URL}/readings", params=params, timeout=30)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Data Collection Service unreachable: {exc}")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch readings from Data Collection Service")
    readings = resp.json()
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
