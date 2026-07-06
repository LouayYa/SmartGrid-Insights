import os
from datetime import date
from typing import List, Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from models import HouseholdPowerConsumption
from schemas import (
    ConsumptionCreate,
    ConsumptionResponse,
    ConsumptionUpdate,
    LoadResponse,
    parse_date_string,
)

router = APIRouter(prefix="/api/v1", tags=["consumption"])

# Resolve the default CSV path relative to this file's directory so the
# server finds the dataset regardless of where uvicorn is launched from.
# Can be overridden via the CSV_PATH env var or the ?csv_path query param.
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CSV_PATH = os.environ.get(
    "CSV_PATH",
    os.path.join(_APP_DIR, "household_power_consumption.csv"),
)
BATCH_SIZE = 5000

NUMERIC_COLUMNS = [
    "Global_active_power",
    "Global_reactive_power",
    "Voltage",
    "Global_intensity",
    "Sub_metering_1",
    "Sub_metering_2",
    "Sub_metering_3",
]
EXPECTED_COLUMNS = ["Date", "Time", *NUMERIC_COLUMNS]

def parse_flexible_date(value: str) -> date:
    """Parse a date string in ISO, d/m/yyyy, or d/m/yy format.

    Raises ValueError if none of the formats match.
    """
    if value is None:
        raise ValueError("date value is None")
    return parse_date_string(value)


@router.post(
    "/load",
    response_model=LoadResponse,
    status_code=status.HTTP_201_CREATED,
)
def load_dataset(
    csv_path: str = DEFAULT_CSV_PATH,
    db: Session = Depends(get_db),
):
    """Bulk-load the household power consumption CSV into the database.

    Idempotent: clears existing rows before inserting. Missing values ("?")
    become NULL. The CSV's mixed d/m/yy and d/m/yyyy date strings are parsed
    into real DATE values so range queries can filter in SQL.
    """
    # Try the given path, then CWD-relative, then app-dir-relative as fallbacks.
    candidates = [csv_path]
    if not os.path.isabs(csv_path):
        candidates.append(os.path.abspath(csv_path))
        candidates.append(os.path.join(_APP_DIR, os.path.basename(csv_path)))

    resolved = next((p for p in candidates if os.path.isfile(p)), None)
    if resolved is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CSV file not found. Tried: {candidates}",
        )
    csv_path = resolved

    try:
        # Read CSV — treat "?" as NaN so numeric columns parse as float.
        df = pd.read_csv(csv_path, na_values=["?"])

        # Drop the "index" column if present (case-insensitive match).
        index_cols = [c for c in df.columns if c.lower() == "index"]
        if index_cols:
            df = df.drop(columns=index_cols)

        missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"CSV missing required columns: {missing}",
            )

        # Keep only expected columns, in order.
        df = df[EXPECTED_COLUMNS]

        # Ensure numeric columns are float (NaN for missing).
        for col in NUMERIC_COLUMNS:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # Parse mixed-format date strings into real dates; fail fast with a
        # clear error rather than storing junk.
        try:
            df["Date"] = df["Date"].astype(str).map(parse_flexible_date)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"CSV contains an unparseable date: {exc}",
            )
        df["Time"] = df["Time"].astype(str)

        # Replace NaN with None for SQLAlchemy (NULL in DB).
        df = df.replace({np.nan: None})

        # Idempotency: wipe existing rows.
        db.query(HouseholdPowerConsumption).delete()
        db.commit()

        total = 0
        records = df.to_dict(orient="records")
        for start in range(0, len(records), BATCH_SIZE):
            batch = records[start : start + BATCH_SIZE]
            db.bulk_insert_mappings(HouseholdPowerConsumption, batch)
            db.commit()
            total += len(batch)

        return LoadResponse(records_loaded=total, status="success")

    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load dataset: {exc}",
        )


@router.get("/consumption", response_model=List[ConsumptionResponse])
def list_consumption(
    start_date: Optional[str] = Query(
        None,
        description="Inclusive start date. Accepts d/m/yy or d/m/yyyy (e.g. 1/1/07 or 30/6/2007).",
    ),
    end_date: Optional[str] = Query(
        None,
        description="Inclusive end date. Accepts d/m/yy or d/m/yyyy.",
    ),
    limit: int = Query(1000, ge=1, le=100000, description="Max records to return."),
    offset: int = Query(0, ge=0, description="Number of records to skip."),
    db: Session = Depends(get_db),
):
    """List consumption records, optionally filtered by a date range.

    Filtering and pagination both run at the SQL level: Date is a real,
    indexed DATE column, so the range filter is a WHERE ... BETWEEN that
    uses the index instead of scanning all rows in Python.
    """
    if (start_date is None) != (end_date is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date and end_date must be provided together.",
        )

    query = db.query(HouseholdPowerConsumption)

    if start_date is not None and end_date is not None:
        try:
            start = parse_flexible_date(start_date)
            end = parse_flexible_date(end_date)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid date format: {exc}",
            )

        if start > end:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date must be on or before end_date.",
            )

        query = query.filter(
            HouseholdPowerConsumption.Date >= start,
            HouseholdPowerConsumption.Date <= end,
        )

    return (
        query.order_by(HouseholdPowerConsumption.ID)
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/consumption/{record_id}", response_model=ConsumptionResponse)
def get_consumption(record_id: int, db: Session = Depends(get_db)):
    """Retrieve a single consumption record by ID."""
    record = (
        db.query(HouseholdPowerConsumption)
        .filter(HouseholdPowerConsumption.ID == record_id)
        .first()
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Record not found",
        )
    return record


@router.post("/consumption", status_code=status.HTTP_201_CREATED)
def create_consumption(payload: ConsumptionCreate, db: Session = Depends(get_db)):
    """Create a new consumption record."""
    try:
        record = HouseholdPowerConsumption(**payload.model_dump())
        db.add(record)
        db.commit()
        db.refresh(record)
        return {"id": record.ID, "status": "created"}
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create record: {exc}",
        )


@router.put("/consumption/{record_id}")
def update_consumption(
    record_id: int,
    payload: ConsumptionUpdate,
    db: Session = Depends(get_db),
):
    """Update an existing consumption record (partial update)."""
    record = (
        db.query(HouseholdPowerConsumption)
        .filter(HouseholdPowerConsumption.ID == record_id)
        .first()
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Record not found",
        )

    updates = payload.model_dump(exclude_unset=True)
    try:
        for field, value in updates.items():
            setattr(record, field, value)
        db.commit()
        return {"id": record.ID, "status": "updated"}
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update record: {exc}",
        )


@router.delete("/consumption/{record_id}")
def delete_consumption(record_id: int, db: Session = Depends(get_db)):
    """Delete a consumption record by ID."""
    record = (
        db.query(HouseholdPowerConsumption)
        .filter(HouseholdPowerConsumption.ID == record_id)
        .first()
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Record not found",
        )

    try:
        db.delete(record)
        db.commit()
        return {"id": record_id, "status": "deleted"}
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete record: {exc}",
        )
