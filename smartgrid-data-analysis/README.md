# SmartGrid Insights — Data Analysis Service

> **Service 4 of 5** | CMP404 Spring 2026 · Team 5 | Developed by **Louy Abbas** · AUS

## Overview

Provides analytical insights over collected smart meter consumption data. This service has no database of its own — it fetches readings from the Data Collection Service via REST and computes results on the fly. Originally deployed on Azure App Service (since decommissioned — the stack now runs locally via Docker Compose). Carries a **pytest** suite covering its API surface, with the outbound call to the Data Collection Service mocked — no live infrastructure required to run tests locally or in CI.

**Stack:** FastAPI · Pydantic · Requests · pytest · Docker · GitHub Actions · Azure App Service (deploy-on-demand)

---

## Data Flow

```
Client Interface
      │
      └──► GET /analysis/averages/{meter_id}
           GET /analysis/peaks/{meter_id}
           GET /analysis/categories/{meter_id}
                          │
                          ▼
                Data Analysis Service (this repo)
                          │
                          ├── GET /readings  (Data Collection Service)
                          └── computes analytics in-memory
```

---

## API Endpoints

Base URL: `http://localhost:8003` (local dev — the Azure deployment has been decommissioned; see [CI/CD](#cicd))

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/analysis/averages/{meter_id}` | Daily average global active power per day |
| `GET` | `/analysis/peaks/{meter_id}` | Peak consumption hour (0–23) |
| `GET` | `/analysis/categories/{meter_id}` | Total energy per sub-metering category |

All endpoints require `start_date` and `end_date` as query parameters (format: `YYYY-MM-DD`).

**Example — daily averages:**
```http
GET /analysis/averages/1?start_date=2007-01-01&end_date=2007-01-31
```
```json
[
  { "date": "2007-01-01", "avg_power": 1.4523 },
  { "date": "2007-01-02", "avg_power": 1.6781 }
]
```

**Example — peak hour:**
```http
GET /analysis/peaks/1?start_date=2007-01-01&end_date=2007-01-31
```
```json
{ "peak_hour": 19, "avg_power": 2.1034 }
```

**Example — category breakdown:**
```http
GET /analysis/categories/1?start_date=2007-01-01&end_date=2007-01-31
```
```json
{ "kitchen": 12045.0, "laundry": 8932.0, "water_heater_ac": 15678.0 }
```

---

## Testing

The service ships with a `pytest` suite in [`tests/`](tests/) covering:

- **Daily averages, peak hour, and category breakdown** endpoints against canned reading data (`tests/test_analysis.py`)
- **Error handling** — empty result set from the Data Collection Service (404), upstream failure (502), and missing required query params (422)

Tests mock the outbound `requests.get` call to the Data Collection Service (`tests/conftest.py`), so they're fast, deterministic, and require no external services or credentials to run.

```bash
pip install pytest httpx
pytest tests/ -v
```

---

## Local Setup

```bash
git clone https://github.com/LouayYa/smartgrid-data-analysis.git
cd smartgrid-data-analysis
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file:
```env
DATA_COLLECTION_URL=http://localhost:8002
```

Run:
```bash
uvicorn app.main:app --reload --port 8003
# Docs: http://localhost:8003/docs
```

---

## Run with Docker

The repo ships a multi-stage [`Dockerfile`](Dockerfile) (Python 3.12-slim builder + slim runtime, non-root user, uvicorn):

```bash
docker build -t smartgrid-data-analysis .
docker run -p 8003:8003 --env-file .env smartgrid-data-analysis
```

To run the **entire five-service stack plus a shared PostgreSQL 16 instance** with one command, use the `docker-compose.yml` in the umbrella repo: [SmartGrid-Insights](https://github.com/LouayYa/SmartGrid-Insights).

---

## CI/CD

**Build & test** run automatically via **GitHub Actions** on every push to `main`: dependencies install into a virtual environment and the `pytest` suite runs with the Data Collection call mocked. A failing test blocks the pipeline before any deployment step runs.

**Deploy to Azure App Service** was originally wired through **Azure Deployment Center** (GitHub source → auto-generated workflow), with the `DATA_COLLECTION_URL` app setting configured under App Service → Configuration rather than committed to the repo. The live Azure App Service has since been decommissioned to cut hosting costs, so the `deploy` job is kept in [`.github/workflows/`](.github/workflows/) as a reference implementation and only runs on a manual `workflow_dispatch` trigger — it no longer fires on every push.

---

## Related Services

| Service | Owner | Role |
|---|---|---|
| Data Ingestion Service | Saif | Historical CSV data source |
| Meter Registration Service | Ahmad | Provides `meter_id` values |
| Data Collection Service | Louy | Provides readings via REST |
| **Data Analysis Service** | **Louy** | **This repo** |
| Client Interface | Ahmad | Web UI |

> Part of **SmartGrid Insights** — CMP404 Spring 2026 · Team 5  
> Saifeldin Hassan · Louy Abbas · Ahmad Bilal · American University of Sharjah
