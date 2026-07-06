from typing import List

from pydantic import BaseModel


class DailyAverage(BaseModel):
    date: str
    avg_power: float


class PeakHourResponse(BaseModel):
    peak_hour: int
    avg_power: float


class CategoryBreakdown(BaseModel):
    kitchen: float
    laundry: float
    water_heater_ac: float


class DailyAggregate(BaseModel):
    """A precomputed per-meter daily aggregate from the Airflow batch
    pipeline, served by the Data Collection Service."""

    meter_id: int
    day: str
    avg_power: float
    peak_power: float
    kitchen_wh: float
    laundry_wh: float
    water_heater_ac_wh: float
    samples: int
