from sqlalchemy import Column, Float, Integer, String

from database import Base


class HouseholdPowerConsumption(Base):
    """ORM model for the household_power_consumption dataset.

    Numeric columns are nullable because ~3,771 rows in the source dataset
    have missing values (originally marked as "?").
    """

    __tablename__ = "household_power_consumption"

    ID = Column(Integer, primary_key=True, autoincrement=True, index=True)
    Date = Column(String(20), nullable=False)
    Time = Column(String(20), nullable=False)
    Global_active_power = Column(Float, nullable=True)
    Global_reactive_power = Column(Float, nullable=True)
    Voltage = Column(Float, nullable=True)
    Global_intensity = Column(Float, nullable=True)
    Sub_metering_1 = Column(Float, nullable=True)
    Sub_metering_2 = Column(Float, nullable=True)
    Sub_metering_3 = Column(Float, nullable=True)
