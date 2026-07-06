from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

# Accepted string formats for the Date field: ISO first (the canonical API
# format), then the source dataset's d/m/yyyy and d/m/yy for compatibility.
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y")


def parse_date_string(value):
    """Coerce a date-ish value (date or string in any accepted format) to date."""
    if isinstance(value, date):
        return value
    s = str(value).strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(
        f"Unrecognized date format: {value!r} (expected YYYY-MM-DD, d/m/yyyy, or d/m/yy)"
    )


class ConsumptionBase(BaseModel):
    Global_active_power: Optional[float] = None
    Global_reactive_power: Optional[float] = None
    Voltage: Optional[float] = None
    Global_intensity: Optional[float] = None
    Sub_metering_1: Optional[float] = None
    Sub_metering_2: Optional[float] = None
    Sub_metering_3: Optional[float] = None


class ConsumptionCreate(ConsumptionBase):
    """Payload for POST — date and time required, numerics optional."""

    Date: date
    Time: str

    @field_validator("Date", mode="before")
    @classmethod
    def _flexible_date(cls, v):
        return parse_date_string(v)


class ConsumptionUpdate(BaseModel):
    """Payload for PUT — all fields optional for partial updates."""

    Date: Optional[date] = None
    Time: Optional[str] = None
    Global_active_power: Optional[float] = None
    Global_reactive_power: Optional[float] = None
    Voltage: Optional[float] = None
    Global_intensity: Optional[float] = None
    Sub_metering_1: Optional[float] = None
    Sub_metering_2: Optional[float] = None
    Sub_metering_3: Optional[float] = None

    @field_validator("Date", mode="before")
    @classmethod
    def _flexible_date(cls, v):
        if v is None:
            return None
        return parse_date_string(v)


class ConsumptionResponse(ConsumptionBase):
    """Full record representation including the primary key.

    Date serializes as ISO (YYYY-MM-DD).
    """

    ID: int
    Date: date
    Time: str

    model_config = ConfigDict(from_attributes=True)


class LoadResponse(BaseModel):
    records_loaded: int
    status: str
