# SmartGrid Insights — Data Analysis Service

> **Service 4 of 5** | CMP404 Spring 2026 · Team 5 | Developed by **Louy Abbas** · AUS

## Overview

Provides analytical insights over collected smart meter consumption data. This service has no database of its own — it fetches readings from the Data Collection Service via REST and computes results on the fly. Deployed as an Azure App Service. Carries a **pytest** suite covering its API surface, with the outbound call to the Data Collection Service mocked — no live infrastructure required to run tests locally or in CI.

**Stack:** FastAPI · Pydantic · Requests · pytest · Azure App Service · GitHub Actions

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

Base URL: `https://<data-analysis-app>.azurewebsites.net`

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
DATA_COLLECTION_URL=https://<data-collection-app>.azurewebsites.net
```

Run:
```bash
uvicorn app.main:app --reload --port 8003
# Docs: http://localhost:8003/docs
```

---

## CI/CD — Deployment to Azure App Service

The service is deployed to Azure App Service via **GitHub Actions**, configured through **Azure Deployment Center** — no manual workflow setup required.

**How it was set up:**
1. In the Azure Portal, navigate to the App Service → **Deployment Center**
2. Under **Source**, select **GitHub** and authorize Azure to access your account
3. Select the repository (`smartgrid-data-analysis`) and branch (`main`)
4. Azure automatically generates and commits a GitHub Actions workflow file to `.github/workflows/`

From that point on, every push to `main` triggers the workflow — it builds the Python app and deploys it to the App Service automatically.

The `DATA_COLLECTION_URL` environment variable is configured under **App Service → Settings → Configuration** in the Azure Portal, not committed to the repo.

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
