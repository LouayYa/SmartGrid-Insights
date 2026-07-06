# SmartGrid Insights — Data Ingestion Service

> **Service 1 of 5** | CMP404 Spring 2026 · Team 5 | Developed by **Saifeldin Hassan** · AUS

## Overview

One of five independently deployed microservices behind SmartGrid Insights, a system that ingests, stores, and analyzes 260K+ smart meter readings end to end. This service is the historical data source: it bulk-loads the household power consumption dataset (260,640 rows) into its own database and serves it out to the Data Collection Service's simulator, which replays it as live meter readings.

Originally deployed on Azure App Service against Azure SQL via `pyodbc`; the database layer has since been migrated to **PostgreSQL**, and the service carries a **pytest** suite covering its API surface (CRUD on consumption records, CSV loading, validation) against an isolated SQLite test database — no live infrastructure required to run tests locally or in CI.

**Stack:** FastAPI · SQLAlchemy · pandas · PostgreSQL (psycopg2) · Pydantic · pytest · GitHub Actions · Azure App Service (deploy-on-demand)

---

## Data Flow

```
household_power_consumption.csv
      │
      └──► POST /api/v1/load  ──► bulk-inserts into this service's DB
                                        │
Data Collection Service  ◄── GET /api/v1/consumption  (date-range filtered)
      │
      └──► replayed as simulated live readings
```

---

## API Endpoints

Base URL: `http://localhost:8003` (local dev — the Azure deployment has been decommissioned; see [CI/CD](#cicd))

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/load` | Bulk-load the household power consumption CSV into the database (idempotent — clears existing rows first) |
| `GET` | `/api/v1/consumption` | List consumption records — optional `start_date`/`end_date` (`d/m/yy` or `d/m/yyyy`), `limit`, `offset` |
| `POST` | `/api/v1/consumption` | Create a single consumption record |
| `PUT` | `/api/v1/consumption/{id}` | Partially update a consumption record |
| `DELETE` | `/api/v1/consumption/{id}` | Delete a consumption record |
| `GET` | `/health` | Health check |

**Example — load the dataset:**
```http
POST /api/v1/load
```
```json
{ "records_loaded": 260640, "status": "success" }
```

**Example — filtered consumption:**
```http
GET /api/v1/consumption?start_date=1/1/07&end_date=1/1/07
```
```json
[
  { "ID": 1, "Date": "1/1/07", "Time": "00:00:00", "Global_active_power": 4.216, "Sub_metering_1": 0.0, "Sub_metering_2": 1.0, "Sub_metering_3": 17.0 }
]
```

---

## Database Schema

**Table: `household_power_consumption`** (PostgreSQL)

| Column | Type | Description |
|---|---|---|
| `ID` | SERIAL PK | Auto-increment |
| `Date`, `Time` | VARCHAR | Stored verbatim (mixed `d/m/yy`/`d/m/yyyy` formats in the source dataset) |
| `Global_active_power`, `Global_reactive_power`, `Voltage`, `Global_intensity` | FLOAT, nullable | Nullable because ~3,771 source rows have missing (`?`) values |
| `Sub_metering_1/2/3` | FLOAT, nullable | Kitchen / Laundry / Water heater & AC (Wh) |

Schema is created automatically on startup via `Base.metadata.create_all()` — no manual migration step needed for this table.

---

## Testing

The service ships with a `pytest` suite in [`tests/`](tests/) covering:

- **CRUD on consumption records** — create, list, update, delete, date-range filtering, pagination (`tests/test_consumption.py`)
- **Validation** — required fields, inverted date ranges, malformed dates, missing date-bound pairing
- **CSV loading** — successful load with `?` → NULL coercion, idempotent re-load, missing file (404), missing required columns (400) (`tests/test_load.py`)

Tests run against an isolated, disposable **SQLite** database (`tests/conftest.py` overrides `DATABASE_URL` before the app is imported), not the real PostgreSQL instance — so they're fast, deterministic, and require no external services or credentials to run.

```bash
pip install pytest httpx
pytest tests/ -v
```

This suite runs automatically as part of CI (see below) on every push to `main`.

> Note: `GET /api/v1/consumption/{id}` is currently a stub — it returns a placeholder record rather than the real one — and is intentionally left untested pending implementation.

---

## Local Setup

```bash
git clone https://github.com/LouayYa/smartgrid-data-ingestion.git
cd smartgrid-data-ingestion
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file:
```env
DATABASE_URL=postgresql://<user>:<password>@<host>:5432/<db>
```

Run:
```bash
uvicorn main:app --reload --port 8003
# Docs: http://localhost:8003/docs
```

---

## CI/CD

**Build & test** run automatically via **GitHub Actions** on every push to `main`: dependencies install into a virtual environment and the `pytest` suite runs against the isolated SQLite test database described above. A failing test blocks the pipeline before any deployment step runs.

**Deploy to Azure App Service** was originally wired through **Azure Deployment Center** (GitHub source → auto-generated workflow), with the `DATABASE_URL` app setting configured under App Service → Configuration rather than committed to the repo. The live Azure App Service has since been decommissioned to cut hosting costs, so the `deploy` job is kept in [`.github/workflows/`](.github/workflows/) as a reference implementation and only runs on a manual `workflow_dispatch` trigger — it no longer fires on every push.

---

## Related Services

| Service | Owner | Role |
|---|---|---|
| **Data Ingestion Service** | **Saif** | This repo — historical CSV data source |
| Meter Registration Service | Ahmad | Provides `meter_id` values |
| Data Collection Service | Louy | Pulls from this service to simulate live readings |
| Data Analysis Service | Louy | Queries collected readings for analytics |
| Client Interface | Ahmad | Web UI |

> Part of **SmartGrid Insights** — CMP404 Spring 2026 · Team 5  
> Saifeldin Hassan · Louy Abbas · Ahmad Bilal · American University of Sharjah
