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
