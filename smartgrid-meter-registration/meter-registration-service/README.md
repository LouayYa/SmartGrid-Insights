# SmartGrid Insights — Meter Registration Service

> **Service 2 of 5** | CMP404 Spring 2026 · Team 5 | Developed by **Ahmad Bilal** · AUS

## Overview

One of five independently deployed microservices behind SmartGrid Insights, a system that ingests, stores, and analyzes 260K+ smart meter readings end to end. This service owns meter identity: it registers meters and hands out the `meter_id` values that the Data Collection Service attaches to every reading.

Originally deployed on Azure App Service against Azure SQL via `pyodbc`; the database layer has since been migrated to **PostgreSQL**, and the service carries a **pytest** suite covering its API surface (CRUD on meters, duplicate-name conflicts, validation) against an isolated SQLite test database — no live infrastructure required to run tests locally or in CI.

**Stack:** Flask · Flask-SQLAlchemy · PostgreSQL (psycopg2) · Gunicorn · pytest · GitHub Actions · Azure App Service (deploy-on-demand)

---

## Data Flow

```
Client Interface
      │
      ├──► POST /meters          ──► registers a new meter
      ├──► GET  /meters          ──► lists registered meters
      └──► GET  /meters/{id}     ──► used by other services to resolve a meter_id
```

---

## API Endpoints

Base URL: `http://localhost:8000` (local dev — the Azure deployment has been decommissioned; see [CI/CD](#cicd))

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/meters` | Register a new meter (`name` required, must be unique) |
| `GET` | `/meters` | List all registered meters |
| `GET` | `/meters/{meter_id}` | Get a single meter by ID |
| `PUT` | `/meters/{meter_id}` | Rename a meter |
| `DELETE` | `/meters/{meter_id}` | Delete a meter |
| `GET` | `/health` | Health check |

**Example — register a meter:**
```http
POST /meters
{ "name": "Household 1" }
```
```json
{ "meter_id": 1, "name": "Household 1", "created_at": "2026-01-01T00:00:00" }
```

---

## Database Schema

**Table: `meters`** (PostgreSQL)

| Column | Type | Description |
|---|---|---|
| `meter_id` | SERIAL PK | Auto-increment |
| `name` | VARCHAR(100) UNIQUE | Meter label |
| `created_at` | TIMESTAMP | Set on registration |

Schema is created automatically on startup via `db.create_all()` — no manual migration step needed for this table.

---

## Testing

The service ships with a `pytest` suite in [`tests/`](tests/) covering:

- **CRUD on meters** — create, list, get, update, delete (`tests/test_meters.py`)
- **Validation and conflicts** — blank-name rejection (400), duplicate-name rejection (409), not-found handling (404) for get/update/delete
- **Health check**

Tests run against an isolated, disposable **SQLite** database (`tests/conftest.py` overrides `DATABASE_URL` before the app is imported), not the real PostgreSQL instance — so they're fast, deterministic, and require no external services or credentials to run.

```bash
pip install pytest
pytest tests/ -v
```

This suite runs automatically as part of CI (see below) on every push to `main`.

---

## Local Setup

```bash
git clone https://github.com/LouayYa/meter-registration-service.git
cd meter-registration-service
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file:
```env
DATABASE_URL=postgresql://<user>:<password>@<host>:5432/<db>
```

Run:
```bash
python app.py
# or, matching the production startup command:
gunicorn --bind=0.0.0.0:8000 app:app
```

---

## CI/CD

**Build & test** run automatically via **GitHub Actions** on every push to `main`: dependencies install into a virtual environment and the `pytest` suite runs against the isolated SQLite test database described above. A failing test blocks the pipeline before any deployment step runs.

**Deploy to Azure App Service** was originally wired through **Azure Deployment Center** (GitHub source → auto-generated workflow), with the `DATABASE_URL` app setting configured under App Service → Configuration rather than committed to the repo. The live Azure App Service has since been decommissioned to cut hosting costs, so the `deploy` job is kept in [`.github/workflows/`](.github/workflows/) as a reference implementation and only runs on a manual `workflow_dispatch` trigger — it no longer fires on every push.

---

## Related Services

| Service | Owner | Role |
|---|---|---|
| Data Ingestion Service | Saif | Historical CSV data source |
| **Meter Registration Service** | **Ahmad** | This repo — provides `meter_id` values |
| Data Collection Service | Louy | Persists readings tagged with `meter_id` |
| Data Analysis Service | Louy | Queries collected readings for analytics |
| Client Interface | Ahmad | Web UI |

> Part of **SmartGrid Insights** — CMP404 Spring 2026 · Team 5  
> Saifeldin Hassan · Louy Abbas · Ahmad Bilal · American University of Sharjah
