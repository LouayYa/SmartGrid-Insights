from typing import Optional

from pydantic import BaseModel, ConfigDict


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

    Date: str
    Time: str


class ConsumptionUpdate(BaseModel):
    """Payload for PUT — all fields optional for partial updates."""

    Date: Optional[str] = None
    Time: Optional[str] = None
    Global_active_power: Optional[float] = None
    Global_reactive_power: Optional[float] = None
    Voltage: Optional[float] = None
    Global_intensity: Optional[float] = None
    Sub_metering_1: Optional[float] = None
    Sub_metering_2: Optional[float] = None
    Sub_metering_3: Optional[float] = None


class ConsumptionResponse(ConsumptionBase):
    """Full record representation including the primary key."""

    ID: int
    Date: str
    Time: str

    model_config = ConfigDict(from_attributes=True)


class LoadResponse(BaseModel):
    records_loaded: int
    status: str
